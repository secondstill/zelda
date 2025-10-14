import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
import hashlib
import sqlite3
from assistant import get_ai_reply, get_ai_reply_with_context, get_motivation_message
import secrets
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any

# Simple password hashing functions as fallback
def generate_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_hash(hash, password):
    return hash == hashlib.sha256(password.encode()).hexdigest()

# Import voice assistant module
try:
    from voice_assistant import handle_voice_command
    VOICE_ENABLED = True
except ImportError:
    print("Voice assistant module could not be loaded. Please install required dependencies.")
    VOICE_ENABLED = False

# Import Whisper and new modules
try:
    from whisper_service import transcribe_audio_bytes
    from intent_parser import parse_user_intent
    from habit_automation import execute_habit_action
    WHISPER_ENABLED = True
    print("✅ Whisper-large and intelligent systems loaded successfully")
except ImportError as e:
    print(f"⚠️ Advanced voice features not available: {e}")
    WHISPER_ENABLED = False

app = Flask(__name__)
from dotenv import load_dotenv
load_dotenv()

# JWT Configuration - Production Ready
class JWTConfig:
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'bf3ef2c823a999def7fdb49721aeb5d98b00dffb73f714fca321e3aac0f5cc44')
    ALGORITHM = 'HS256'
    ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days
    
    @classmethod
    def validate_secret(cls):
        """Ensure JWT secret is secure"""
        if len(cls.SECRET_KEY) < 32:
            print("⚠️ WARNING: JWT secret key should be at least 32 characters for security")
        return cls.SECRET_KEY

# Initialize Flask app with secure JWT config
app.config['JWT_SECRET_KEY'] = JWTConfig.validate_secret()
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=JWTConfig.ACCESS_TOKEN_EXPIRE_HOURS)
app.config['JWT_ALGORITHM'] = JWTConfig.ALGORITHM

# Indian Standard Time timezone
IST = pytz.timezone('Asia/Kolkata')

def get_ist_time():
    """Get current time in IST"""
    return datetime.now(IST)

def format_ist_time(dt):
    """Format datetime to IST string"""
    if dt.tzinfo is None:
        # If naive datetime, assume it's IST
        dt = IST.localize(dt)
    elif dt.tzinfo != IST:
        # Convert to IST if it's in a different timezone
        dt = dt.astimezone(IST)
    return dt.isoformat()

# Initialize extensions
jwt = JWTManager(app)
# Improved CORS: allow Authorization header and all standard methods
CORS(
    app,
    resources={
        r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:5174"]},
        r"/login": {"origins": ["http://localhost:5173", "http://localhost:5174"]},
        r"/signup": {"origins": ["http://localhost:5173", "http://localhost:5174"]},
        r"/logout": {"origins": ["http://localhost:5173", "http://localhost:5174"]}
    },
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "Accept"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    max_age=600
)
@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:5173', 'http://localhost:5174']:
        resp.headers.setdefault('Access-Control-Allow-Origin', origin)
        resp.headers.setdefault('Vary', 'Origin')
    resp.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
    resp.headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
    resp.headers.setdefault('Access-Control-Allow-Credentials', 'true')
    return resp

# Generic OPTIONS handler (some browsers are strict if route not explicitly present)
@app.route('/login', methods=['OPTIONS'], provide_automatic_options=False)
@app.route('/signup', methods=['OPTIONS'], provide_automatic_options=False)
@app.route('/logout', methods=['OPTIONS'], provide_automatic_options=False)
def auth_options():
    resp = jsonify({'success': True})
    return resp, 200

# Enhanced JWT error handlers with detailed logging
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    user_id = jwt_payload.get('sub', 'unknown')
    exp_timestamp = jwt_payload.get('exp', 0)
    exp_time = datetime.fromtimestamp(exp_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    print(f"❌ JWT EXPIRED - User: {user_id}, Expired at: {exp_time}")
    return jsonify({
        'success': False, 
        'error': 'Token has expired',
        'error_code': 'TOKEN_EXPIRED',
        'expired_at': exp_time
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    print(f"❌ JWT INVALID - Error: {error}")
    # Log the actual token for debugging (first 20 chars only for security)
    auth_header = request.headers.get('Authorization', '')
    token_preview = auth_header.replace('Bearer ', '')[:20] + '...' if len(auth_header) > 20 else auth_header
    print(f"❌ Invalid token preview: {token_preview}")
    return jsonify({
        'success': False, 
        'error': 'Invalid token format or signature',
        'error_code': 'TOKEN_INVALID'
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    print(f"❌ JWT MISSING - Error: {error}")
    print(f"❌ Request headers: {dict(request.headers)}")
    return jsonify({
        'success': False, 
        'error': 'Authorization token required',
        'error_code': 'TOKEN_MISSING'
    }), 401

@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    user_id = jwt_payload.get('sub', 'unknown')
    print(f"❌ JWT NOT FRESH - User: {user_id}")
    return jsonify({
        'success': False, 
        'error': 'Fresh token required',
        'error_code': 'TOKEN_NOT_FRESH'
    }), 401

# Helper functions for JWT (simplified approach)
def get_current_user_id():
    """Get current user ID from JWT token"""
    try:
        return int(get_jwt_identity())
    except:
        return None

def get_current_user_data():
    """Get current user data from JWT token"""
    try:
        return get_jwt()
    except:
        return {}

# Enhanced token creation with validation
def create_secure_token(user_id: int, user_data: dict = None) -> dict:
    """Create a secure JWT token with proper payload and validation"""
    try:
        # Ensure user_id is valid
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id for token creation")
        
        # Create token with enhanced payload
        additional_claims = {
            'user_id': user_id,  # Custom claim for easier access
            'iat': datetime.utcnow(),  # Issued at
            'type': 'access_token'
        }
        
        # Add user data if provided
        if user_data:
            additional_claims.update({
                'username': user_data.get('username', ''),
                'email': user_data.get('email', '')
            })
        
        # Create token using Flask-JWT-Extended (handles expiry automatically)
        access_token = create_access_token(
            identity=str(user_id),  # Must be string for Flask-JWT-Extended
            additional_claims=additional_claims
        )
        
        print(f"✅ Token created successfully for user {user_id}")
        
        return {
            'success': True,
            'token': access_token,
            'expires_at': (datetime.utcnow() + timedelta(hours=JWTConfig.ACCESS_TOKEN_EXPIRE_HOURS)).isoformat(),
            'user_id': user_id
        }
        
    except Exception as e:
        print(f"❌ Token creation failed: {str(e)}")
        return {
            'success': False,
            'error': f'Token creation failed: {str(e)}'
        }

DB_FILE = 'habits.db'

# Database helper functions
def get_habits_from_db(user_id):
    """Get all habits for a user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, color FROM habits WHERE user_id = ?', (user_id,))
        habits = []
        for row in cursor.fetchall():
            habits.append({
                'id': row[0],
                'name': row[1],
                'color': row[2]
            })
        conn.close()
        return habits
    except Exception as e:
        print(f"Error getting habits: {e}")
        return []

def add_habit_to_db(habit_name, user_id):
    """Add a new habit to the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO habits (name, user_id) VALUES (?, ?)', (habit_name, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding habit: {e}")

def save_habit_date(habit_name, date, user_id):
    """Save habit completion for a specific date"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # First get the habit_id
        cursor.execute('SELECT id FROM habits WHERE name = ? AND user_id = ?', (habit_name, user_id))
        habit_row = cursor.fetchone()
        if habit_row:
            habit_id = habit_row[0]
            cursor.execute('INSERT OR REPLACE INTO habit_entries (user_id, habit_id, date, completed) VALUES (?, ?, ?, 1)', 
                         (user_id, habit_id, date))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving habit date: {e}")

def update_habit_color_in_db(habit_name, color, user_id):
    """Update habit color"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE habits SET color = ? WHERE name = ? AND user_id = ?', (color, habit_name, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating habit color: {e}")

def rename_habit_in_db(old_name, new_name, user_id):
    """Rename a habit"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE habits SET name = ? WHERE name = ? AND user_id = ?', (new_name, old_name, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error renaming habit: {e}")

def delete_habit_from_db(habit_name, user_id):
    """Delete a habit"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # First get the habit_id
        cursor.execute('SELECT id FROM habits WHERE name = ? AND user_id = ?', (habit_name, user_id))
        habit_row = cursor.fetchone()
        if habit_row:
            habit_id = habit_row[0]
            # Delete habit entries first, then the habit
            cursor.execute('DELETE FROM habit_entries WHERE habit_id = ? AND user_id = ?', (habit_id, user_id))
            cursor.execute('DELETE FROM habits WHERE id = ? AND user_id = ?', (habit_id, user_id))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error deleting habit: {e}")

# Database initialization
def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create habits table (updated with user_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#2ecc40',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, name)
        )
    ''')
    
    # Create habit_entries table (updated with user_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            habit_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (habit_id) REFERENCES habits (id),
            UNIQUE(user_id, habit_id, date)
        )
    ''')
    
    # Create tasks table (updated with user_id)  
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create chat history table for user-specific conversations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Authentication Routes
@app.route('/login', methods=['POST'])
def login():
    """Enhanced login with secure token generation"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"🔐 Login attempt for: {username}")
        
        # Validate input
        if not username or not password:
            print("❌ Login failed: Missing credentials")
            return jsonify({
                'success': False, 
                'error': 'Username and password required'
            }), 400
        
        # Get user from database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, password_hash, full_name, email, username, created_at
            FROM users WHERE username = ? OR email = ?
        ''', (username, username))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            print(f"❌ Login failed: User '{username}' not found")
            return jsonify({
                'success': False, 
                'error': 'Invalid username or password'
            }), 401
        
        # Verify password
        if not check_password_hash(user[1], password):
            print(f"❌ Login failed: Invalid password for '{username}'")
            return jsonify({
                'success': False, 
                'error': 'Invalid username or password'
            }), 401
        
        # Create secure token
        user_data = {
            'username': user[4],
            'full_name': user[2],
            'email': user[3]
        }
        
        print(f"🔧 DEBUG: About to create token for user {user[0]} with data: {user_data}")
        token_result = create_secure_token(user[0], user_data)
        print(f"🔧 DEBUG: Token creation result: {token_result}")
        
        if not token_result.get('success'):
            print(f"❌ Login failed: Token creation error for '{username}': {token_result.get('error', 'Unknown error')}")
            return jsonify({
                'success': False,
                'error': 'Failed to generate authentication token'
            }), 500
        
        print(f"✅ Login successful for user ID: {user[0]} ({username})")
        
        response_data = {
            'success': True,
            'token': token_result['token'],
            'expires_at': token_result['expires_at'],
            'user': {
                'id': user[0],
                'username': user[4],
                'full_name': user[2],
                'email': user[3],
                'created_at': user[5]
            }
        }
        print(f"🔧 DEBUG: Sending response: {response_data}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Login failed due to server error'
        }), 500

@app.route('/signup', methods=['POST'])
def signup():
    """Enhanced signup with secure token generation"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        full_name = data.get('full_name', '').strip()
        
        print(f"📝 Signup attempt for: {username} ({email})")
        
        # Enhanced validation
        if not username or len(username) < 3:
            return jsonify({
                'success': False, 
                'error': 'Username must be at least 3 characters long'
            }), 400
        
        if not password or len(password) < 6:
            return jsonify({
                'success': False, 
                'error': 'Password must be at least 6 characters long'
            }), 400
        
        if not email or '@' not in email:
            return jsonify({
                'success': False, 
                'error': 'Valid email is required'
            }), 400
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if username or email already exists
        cursor.execute('SELECT id, username, email FROM users WHERE username = ? OR email = ?', (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            print(f"❌ Signup failed: User already exists - {username}/{email}")
            return jsonify({
                'success': False, 
                'error': 'Username or email already exists'
            }), 400
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, datetime.utcnow().isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create secure token
        user_data = {
            'username': username,
            'full_name': full_name,
            'email': email
        }
        
        token_result = create_secure_token(user_id, user_data)
        
        if not token_result.get('success'):
            print(f"❌ Signup failed: Token creation error for '{username}'")
            return jsonify({
                'success': False,
                'error': 'Failed to generate authentication token'
            }), 500
        
        print(f"✅ Signup successful for user ID: {user_id} ({username})")
        
        return jsonify({
            'success': True,
            'token': token_result['token'],
            'expires_at': token_result['expires_at'],
            'user': {
                'id': user_id,
                'username': username,
                'full_name': full_name,
                'email': email
            }
        })
        
    except Exception as e:
        print(f"❌ Signup error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Signup failed due to server error'
        }), 500

@app.route('/api/update-profile', methods=['POST'])
@jwt_required()
def update_profile():
    """Update user profile information"""
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        data = request.get_json()
        
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        username = data.get('username', '').strip()
        
        if not full_name or not email or not username:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if email or username already exists for other users
        cursor.execute('''
            SELECT id FROM users 
            WHERE (email = ? OR username = ?) AND id != ?
        ''', (email, username, user_id))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Email or username already taken'}), 400
        
        # Update user information
        cursor.execute('''
            UPDATE users 
            SET full_name = ?, email = ?, username = ?
            WHERE id = ?
        ''', (full_name, email, username, user_id))
        
        # Get created_at date for response
        cursor.execute('SELECT created_at FROM users WHERE id = ?', (user_id,))
        created_at = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Profile updated successfully',
            'user': {
                'id': user_id,
                'username': username,
                'full_name': full_name,
                'email': email
            },
            'created_at': created_at
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        data = request.get_json()
        
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'error': 'Current password and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'New password must be at least 6 characters long'}), 400
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get current password hash
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        current_hash = result[0]
        
        # Verify current password
        if not check_password_hash(current_hash, current_password):
            conn.close()
            return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
        
        # Hash new password and update
        new_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Password updated successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-auth')
@jwt_required()
def test_auth():
    """Test endpoint to verify JWT authentication works"""
    try:
        user_id = get_current_user_id()
        user_data = get_current_user_data()
        
        print(f"✅ AUTH TEST: User {user_id} authenticated successfully")
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'user_id': user_id,
            'token_data': {
                'exp': datetime.fromtimestamp(user_data.get('exp', 0)).isoformat(),
                'iat': datetime.fromtimestamp(user_data.get('iat', 0)).isoformat(),
                'username': user_data.get('username', ''),
                'email': user_data.get('email', '')
            }
        })
        
    except Exception as e:
        print(f"❌ AUTH TEST ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/audio', methods=['POST'])
@jwt_required()
def process_voice_audio():
    """Fixed voice audio processing with proper authentication"""
    try:
        user_id = get_current_user_id()
        
        if not WHISPER_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Voice processing not available. Please install required dependencies.',
                'error_code': 'WHISPER_DISABLED'
            }), 503
        
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        audio_file = request.files['audio']
        if not audio_file:
            return jsonify({
                'success': False,
                'error': 'Empty audio file'
            }), 400
        
        print(f"🎤 Processing audio from user {user_id}, file: {audio_file.filename}")
        
        # Read audio bytes
        audio_bytes = audio_file.read()
        
        # Attempt transcription (lazy load inside service)
        try:
            transcription_result = transcribe_audio_bytes(audio_bytes, audio_file.filename or "audio.webm")
        except RuntimeError as re:
            # Likely model load failure
            return jsonify({
                'success': False,
                'error': 'Whisper model initialization failed',
                'error_code': 'MODEL_LOAD_FAILED',
                'details': str(re)
            }), 500
        except Exception as te:
            return jsonify({
                'success': False,
                'error': 'Unexpected transcription error',
                'error_code': 'TRANSCRIPTION_ERROR',
                'details': str(te)
            }), 500
        
        if not transcription_result.get('success'):
            # Map internal hints to user-facing guidance
            internal_error = transcription_result.get('error', 'Unknown error')
            hint = None
            if 'cpu_retry_failed' == transcription_result.get('retry_hint'):
                hint = 'Model failed on GPU/MPS and CPU retry also failed. Consider reducing background load or verifying torch installation.'
            elif 'cpu_retry_success' == transcription_result.get('retry_hint'):
                hint = 'Primary device failed; succeeded on CPU fallback (slower performance).'
            elif 'aten::_sparse' in internal_error or 'PythonFallbackKernel' in internal_error:
                hint = 'Torch backend issue. Try reinstalling pytorch/torchaudio or forcing CPU.'
            return jsonify({
                'success': False,
                'error': 'Audio transcription failed',
                'error_code': 'TRANSCRIBE_FAIL',
                'details': internal_error,
                'hint': hint,
                'error_class': transcription_result.get('error_class'),
                'retry_hint': transcription_result.get('retry_hint')
            }), 500
        
        transcript = transcription_result.get('text', '').strip()
        confidence = transcription_result.get('confidence', 0.0)
        
        print(f"🎯 Transcription: '{transcript}' (confidence: {confidence:.2f})")
        
        if not transcript:
            return jsonify({
                'success': False,
                'error': 'No speech detected in audio',
                'transcript': '',
                'confidence': confidence
            }), 400
        
        # Process through unified chat pipeline
        chat_response = process_unified_message(transcript, user_id, is_voice=True)
        
        return jsonify({
            'success': True,
            'transcript': transcript,
            'confidence': confidence,
            'language': transcription_result.get('language', 'unknown'),
            'reply': chat_response.get('reply', ''),
            'action_taken': chat_response.get('action_taken', False),
            'habit_action': chat_response.get('habit_action', {}),
            'processing_type': chat_response.get('processing_type', 'conversation')
        })
        
    except Exception as e:
        print(f"❌ Voice audio processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process voice audio',
            'error_code': 'VOICE_AUDIO_ERROR',
            'details': str(e)
        }), 500

@app.route('/api/voice/status', methods=['GET'])
def voice_status():
    """Report Whisper service readiness & configuration for frontend polling.

    Does not require auth so the UI can decide to show / hide voice controls pre-login.
    Safe info only.
    """
    try:
        status = {
            'whisper_enabled': WHISPER_ENABLED,
        }
        if WHISPER_ENABLED:
            try:
                from whisper_service import get_whisper_service
                svc = get_whisper_service()
                svc_status = svc.get_status()
                status.update({
                    'ready': svc_status['ready'],
                    'model': svc_status['model'],
                    'device': svc_status['device'],
                    'attempted': svc_status['attempted'],
                    'error': svc_status['error']
                })
            except Exception as e:
                status.update({'ready': False, 'error': str(e)})
        else:
            status.update({'ready': False, 'error': 'Whisper features disabled'})
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/habits', methods=['GET', 'POST'])
@jwt_required()
def habits_api():
    """Habits endpoint returning object keyed by habit name with dates map"""
    try:
        user_id = int(get_jwt_identity())
        print(f"🔍 Habits request from user {user_id}")

        # Handle toggle/add date POST
        if request.method == 'POST':
            data = request.get_json() or {}
            habit_name = (data.get('habit') or '').strip()
            date = (data.get('date') or '').strip()
            if habit_name and date:
                save_habit_date(habit_name, date, user_id)
                print(f"📝 Marked {habit_name} on {date}")

        # Build response shape expected by frontend
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, color FROM habits WHERE user_id = ? ORDER BY name ASC', (user_id,))
        habit_rows = cursor.fetchall()

        # Preload completion entries for recent and month range
        cursor.execute('''
            SELECT h.name, e.date, e.completed
            FROM habit_entries e
            JOIN habits h ON e.habit_id = h.id
            WHERE e.user_id = ?
        ''', (user_id,))
        entries = cursor.fetchall()
        conn.close()

        habits_obj = {}
        for hid, name, color in habit_rows:
            habits_obj[name] = {
                'color': color or '#3b82f6',
                'dates': {}
            }
        for habit_name, date, completed in entries:
            if habit_name in habits_obj:
                habits_obj[habit_name]['dates'][date] = bool(completed)

        print(f"📊 Returning habits keys: {list(habits_obj.keys())}")
        return jsonify({'success': True, 'habits': habits_obj})
    except Exception as e:
        print(f"❌ Error in habits_api: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/habits/new', methods=['POST'])
@jwt_required()
def add_habit():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        habit_name = (data.get('habit') or '').strip()
        if not habit_name:
            return jsonify({'success': False, 'error': 'Habit name required'}), 400
        add_habit_to_db(habit_name, user_id)
        print(f"✅ Added habit {habit_name}")
        # Reuse habits_api logic by calling it directly
        return habits_api()
    except Exception as e:
        print(f"❌ Error in add_habit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/habits/color', methods=['POST'])
@jwt_required()
def update_habit_color():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        habit_name = (data.get('habit') or '').strip()
        color = (data.get('color') or '').strip()
        if habit_name and color:
            update_habit_color_in_db(habit_name, color, user_id)
        return habits_api()
    except Exception as e:
        print(f"❌ Error in update_habit_color: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/habits/rename', methods=['POST'])
@jwt_required()
def rename_habit():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        old = (data.get('old') or '').strip()
        new = (data.get('new') or '').strip()
        if old and new:
            rename_habit_in_db(old, new, user_id)
        return habits_api()
    except Exception as e:
        print(f"❌ Error in rename_habit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/habits/delete', methods=['POST'])
@jwt_required()
def delete_habit():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        habit = (data.get('habit') or '').strip()
        if habit:
            delete_habit_from_db(habit, user_id)
        return habits_api()
    except Exception as e:
        print(f"❌ Error in delete_habit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user-stats', methods=['GET'])
@jwt_required()
def user_stats():
    """Return simple aggregated stats for dashboard"""
    try:
        user_id = int(get_jwt_identity())
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Total habits
        cursor.execute('SELECT COUNT(*) FROM habits WHERE user_id = ?', (user_id,))
        total_habits = cursor.fetchone()[0]
        # Completed today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM habit_entries e
            JOIN habits h ON e.habit_id = h.id
            WHERE e.user_id = ? AND e.date = ? AND e.completed = 1
        ''', (user_id, today))
        completed_today = cursor.fetchone()[0]
        # Total entries for rate
        cursor.execute('SELECT COUNT(*) FROM habit_entries WHERE user_id = ? AND completed = 1', (user_id,))
        total_completions = cursor.fetchone()[0]
        conn.close()
        completion_rate = 0.0
        if total_habits > 0:
            # crude estimate: completions / (habits * 30) for last 30 days placeholder
            completion_rate = round(min(100.0, (total_completions / (total_habits * 30)) * 100), 2)
        return jsonify({
            'success': True,
            'stats': {
                'total_habits': total_habits,
                'completed_today': completed_today,
                'completion_rate': completion_rate,
                'best_streak': 0
            }
        })
    except Exception as e:
        print(f"❌ Error in user_stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat-history', methods=['GET'])
@jwt_required()
def get_chat_history():
    """Get chat history for the current user"""
    try:
        user_id = int(get_jwt_identity())
        print(f"📖 Getting chat history for user {user_id}")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get recent chat history (last 50 messages)
        cursor.execute('''
            SELECT message, response, timestamp 
            FROM chat_history 
            WHERE user_id = ? 
            ORDER BY timestamp ASC 
            LIMIT 50
        ''', (user_id,))
        
        history = cursor.fetchall()
        conn.close()
        
        # Format the history for frontend
        formatted_history = []
        for msg, resp, timestamp in history:
            # Parse the stored timestamp and ensure it's in IST
            try:
                if isinstance(timestamp, str):
                    # Try to parse the timestamp
                    if 'T' in timestamp:
                        # ISO format with timezone
                        dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = IST.localize(dt)
                        else:
                            dt = dt.astimezone(IST)
                    else:
                        # SQLite default format
                        dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                        dt = IST.localize(dt)
                else:
                    # Fallback to current time
                    dt = get_ist_time()
            except Exception as e:
                print(f"❌ Error parsing timestamp {timestamp}: {e}")
                dt = get_ist_time()
            
            # Create slightly different timestamps for user and assistant
            user_time = dt
            assistant_time = dt + datetime.timedelta(seconds=2)
            
            # Add user message
            formatted_history.append({
                'id': len(formatted_history) + 1,
                'content': msg,
                'isUser': True,
                'timestamp': format_ist_time(user_time)
            })
            # Add assistant response
            formatted_history.append({
                'id': len(formatted_history) + 1,
                'content': resp,
                'isUser': False,
                'timestamp': format_ist_time(assistant_time)
            })
        
        print(f"✅ Retrieved {len(formatted_history)} chat messages")
        return jsonify({
            'success': True,
            'messages': formatted_history
        })
        
    except Exception as e:
        print(f"❌ Error getting chat history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve chat history',
            'messages': []
        }), 500

@app.route('/api/chat-history', methods=['DELETE'])
@jwt_required()
def clear_chat_history():
    """Clear chat history for the current user"""
    try:
        user_id = int(get_jwt_identity())
        print(f"🗑️ Clearing chat history for user {user_id}")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ Cleared {deleted_count} chat messages")
        return jsonify({
            'success': True,
            'message': f'Cleared {deleted_count} chat messages'
        })
        
    except Exception as e:
        print(f"❌ Error clearing chat history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear chat history'
        }), 500

@app.route('/api/chat', methods=['POST'])
@jwt_required()
def chat_api():
    """Unified chat endpoint that handles text messages through the same pipeline as voice"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400
        
        print(f"💬 Text chat request from user {user_id}: {user_message}")
        
        # Process through unified pipeline
        response = process_unified_message(user_message, user_id, is_voice=False)
        
        return jsonify({
            'reply': response.get('reply', ''),
            'success': True,
            'action_taken': response.get('action_taken', False),
            'habit_action': response.get('habit_action', {}),
            'frontend_action': response.get('frontend_action'),
            'processing_type': response.get('processing_type', 'conversation')
        })
        
    except Exception as e:
        print(f"❌ Chat API error: {str(e)}")
        return jsonify({
            'reply': "Sorry, I encountered an error. Please try again.",
            'success': False,
            'error': str(e)
        }), 500

def detect_and_create_items(message, user_id):
    """Detect habit and task creation from user messages and create them automatically"""
    import re
    from datetime import datetime
    
    message_lower = message.lower()
    created_items = {'habits': [], 'tasks': []}
    
    # Habit detection patterns
    habit_patterns = [
        r"i want to (?:start|begin|create|add|track) (?:a )?habit (?:called |named |of )?['\"]?([^'\".,!?]+)['\"]?",
        r"(?:create|add|start|track) (?:a |the )?habit[:\s]+['\"]?([^'\".,!?]+)['\"]?",
        r"i (?:want to|need to|should) (?:start|begin) ([^.,!?]+daily|[^.,!?]+every day|drinking water|exercising|reading|meditation|yoga)",
        r"help me (?:track|start|create) (?:a )?habit (?:of |for )?['\"]?([^'\".,!?]+)['\"]?",
        r"i'm (?:starting|beginning) (?:a |the )?habit (?:of |for )?['\"]?([^'\".,!?]+)['\"]?",
    ]
    
    # Check for habits
    for pattern in habit_patterns:
        matches = re.findall(pattern, message_lower, re.IGNORECASE)
        for match in matches:
            habit_name = match.strip().title()
            if habit_name and len(habit_name) > 2:
                # Clean up the habit name
                habit_name = re.sub(r'(daily|every day|everyday)$', '', habit_name).strip()
                add_habit_to_db(habit_name, user_id)
                created_items['habits'].append(habit_name)
    
    return created_items if (created_items['habits'] or created_items['tasks']) else None

@app.route('/api/motivation', methods=['GET'])
@jwt_required()
def api_get_motivation():
    """Get a motivational message"""
    try:
        print("🌟 Motivation request received")
        
        motivation = get_motivation_message()
        
        print(f"💫 Motivation: {motivation}")
        
        return jsonify({
            'success': True,
            'message': motivation
        })
        
    except Exception as e:
        print(f"❌ Motivation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Stay motivated! You\'re doing great! 🌟'
        }), 500

def process_unified_message(message: str, user_id: int, is_voice: bool = False) -> Dict[str, Any]:
    """
    Unified message processing that handles both voice and text through same pipeline
    with intelligent intent detection and habit automation
    """
    try:
        print(f"🧠 Processing message: '{message}' (voice: {is_voice}) for user {user_id}")
        
        # Parse intent to determine if this is a habit action or conversation
        intent_result = parse_user_intent(message)
        action = intent_result.get('action')
        confidence = intent_result.get('confidence', 0.0)
        
        print(f"🎯 Intent: {action} (confidence: {confidence:.2f})")
        print(f"📋 Full intent result: {intent_result}")
        
        # Debug: Show what data was extracted
        if 'data' in intent_result:
            data = intent_result['data']
            if 'habit_name' in data:
                print(f"💡 Extracted habit name: '{data['habit_name']}'")
            if 'date' in data:
                print(f"📅 Extracted date: '{data['date']}'")
            if 'action' in data:
                print(f"🎬 Extracted action: '{data['action']}'")
        
        # Validate minimum confidence for habit actions
        if action in ['add_habit', 'complete_habit', 'edit_habit', 'delete_habit'] and confidence < 0.7:
            print(f"⚠️ Low confidence for habit action ({confidence:.2f} < 0.7), treating as conversation")
        
        # Initialize response
        response = {
            'reply': '',
            'action_taken': False,
            'habit_action': {},
            'processing_type': action
        }
        
        # Handle all voice commands (habits, navigation, app controls, etc.) with high confidence
        if action in ['add_habit', 'complete_habit', 'edit_habit', 'delete_habit', 'show_habits', 'habit_status',
                      'navigate_home', 'navigate_habits', 'navigate_analytics', 'navigate_chat', 'navigate_settings',
                      'logout', 'view_account', 'refresh_page', 'clear_data', 'show_help', 'app_info', 
                      'show_today', 'show_calendar'] and confidence > 0.6:
            
            # Import and use the comprehensive voice command handler
            from voice_command_handler import execute_voice_command
            
            # Execute the voice command
            voice_result = execute_voice_command(intent_result, user_id)
            
            response['action_taken'] = True
            response['habit_action'] = voice_result  # This now contains all command results
            response['reply'] = voice_result.get('message', 'Command executed successfully.')
            response['frontend_action'] = voice_result.get('frontend_action')  # New: Frontend actions
            
            # If command was successful, store in chat history
            if voice_result.get('success'):
                store_chat_message(user_id, message, response['reply'])
            
        else:
            # Handle as regular conversation - route through existing chat system
            
            # Get conversation context
            conversation_context = get_conversation_context(user_id)
            
            # Get AI reply with context
            try:
                ai_reply = get_ai_reply_with_context(message, conversation_context)
            except Exception as e:
                print(f"⚠️ Error getting AI reply with context: {e}")
                ai_reply = get_ai_reply(message)
            
            # Check for any implicit habit/task creation in conversation
            detected_actions = detect_and_create_items(message, user_id)
            
            # Modify reply if we detected and created items
            if detected_actions:
                if detected_actions.get('habits'):
                    habit_names = ", ".join(detected_actions['habits'])
                    ai_reply = f"Perfect! I've added '{habit_names}' to your habits tracker. {ai_reply}"
                    response['action_taken'] = True
                    response['habit_action'] = {'implicit_creation': detected_actions}
                
                if detected_actions.get('tasks'):
                    task_names = ", ".join(detected_actions['tasks'])
                    ai_reply = f"Great! I've created the task '{task_names}' for you. {ai_reply}"
                    response['action_taken'] = True
            
            response['reply'] = ai_reply
            
            # Store in chat history
            store_chat_message(user_id, message, ai_reply)
        
        return response
        
    except Exception as e:
        print(f"❌ Error in unified message processing: {str(e)}")
        return {
            'reply': "Sorry, I encountered an error processing your message. Please try again.",
            'action_taken': False,
            'habit_action': {},
            'processing_type': 'error'
        }

def get_conversation_context(user_id: int) -> str:
    """Get recent conversation context for AI"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message, response 
            FROM chat_history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (user_id,))
        
        recent_history = cursor.fetchall()
        recent_history.reverse()  # Reverse to get chronological order
        conn.close()
        
        if recent_history:
            context = "\n\nRecent conversation context:\n"
            for msg, resp in recent_history:
                context += f"User: {msg}\nZelda: {resp}\n\n"
            return context
        
        return ""
        
    except Exception as e:
        print(f"❌ Error getting conversation context: {e}")
        return ""

def store_chat_message(user_id: int, message: str, reply: str):
    """Store chat message in history"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        current_time = get_ist_time()
        timestamp_str = format_ist_time(current_time)
        
        cursor.execute('''
            INSERT INTO chat_history (user_id, message, response, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message, reply, timestamp_str))
        
        conn.commit()
        conn.close()
        print(f"💾 Stored chat message at IST: {timestamp_str}")
        
    except Exception as e:
        print(f"❌ Error storing chat message: {e}")

@app.route('/api/voice/process', methods=['POST'])
@jwt_required()
def process_voice_command():
    """Process voice commands sent as text from the frontend"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        command = data.get('command', '').strip()
        
        print(f"🎤 Voice command from user {user_id}: {command}")
        
        if not command:
            return jsonify({
                'success': False,
                'error': 'No command provided'
            }), 400
        
        # Use the new unified processing system
        try:
            print("🧠 Processing voice command through unified system...")
            chat_response = process_unified_message(command, user_id, is_voice=True)
            
            return jsonify({
                'success': True,
                'transcript': command,
                'reply': chat_response.get('reply', ''),
                'action': chat_response.get('processing_type', 'conversation'),
                'action_taken': chat_response.get('action_taken', False),
                'habit_action': chat_response.get('habit_action', {}),
                'data': chat_response.get('habit_action', {})
            })
            
        except Exception as e:
            print(f"⚠️ Unified processing failed, using fallback: {e}")
            
            # Simple pattern matching for basic commands
            response = process_basic_voice_command(command, user_id)
            return jsonify({
                'success': True,
                'transcript': command,
                'reply': response,
                'action': 'processed',
                'data': {}
            })
        
    except Exception as e:
        print(f"❌ Voice command processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process voice command'
        }), 500

@app.route('/api/voice/test', methods=['POST'])
@jwt_required()
def test_voice_command():
    """Test voice commands with text input for debugging"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        command = data.get('command', '').strip()
        
        print(f"🧪 Testing voice command from user {user_id}: {command}")
        
        if not command:
            return jsonify({
                'success': False,
                'error': 'No command provided'
            }), 400
        
        # Process through unified system
        chat_response = process_unified_message(command, user_id, is_voice=True)
        
        return jsonify({
            'success': True,
            'transcript': command,
            'reply': chat_response.get('reply', ''),
            'action': chat_response.get('processing_type', 'conversation'),
            'action_taken': chat_response.get('action_taken', False),
            'habit_action': chat_response.get('habit_action', {}),
            'processing_details': {
                'user_id': user_id,
                'original_command': command,
                'is_voice': True
            }
        })
        
    except Exception as e:
        print(f"❌ Voice test error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'transcript': command if 'command' in locals() else '',
            'reply': 'Sorry, there was an error processing your command.'
        }), 500

def process_basic_voice_command(command, user_id):
    """Basic fallback voice command processing without AI"""
    import re
    
    command_lower = command.lower()
    
    # Add habit patterns
    add_patterns = [
        r'add (?:a )?habit (?:called |named |to )?(.+)',
        r'create (?:a )?habit (?:called |named |to )?(.+)',
        r'start tracking (.+)',
        r'i want to track (.+)',
    ]
    
    # Complete habit patterns
    complete_patterns = [
        r'mark (.+) (?:as )?(?:complete|completed|done)',
        r'complete (.+)',
        r'i (?:did|completed|finished) (.+)',
    ]
    
    # Delete habit patterns
    delete_patterns = [
        r'delete (?:the )?habit (.+)',
        r'remove (?:the )?habit (.+)',
        r'stop tracking (.+)',
    ]
    
    # Show habits patterns
    show_patterns = [
        r'show (?:me )?(?:my )?habits',
        r'list (?:my )?habits',
        r'what are my habits',
    ]
    
    # Try to match patterns
    for pattern in add_patterns:
        match = re.search(pattern, command_lower)
        if match:
            habit_name = match.group(1).strip().title()
            add_habit_to_db(habit_name, user_id)
            return f"Great! I've added '{habit_name}' to your habits. You can start tracking it now!"
    
    for pattern in complete_patterns:
        match = re.search(pattern, command_lower)
        if match:
            habit_name = match.group(1).strip()
            # Try to mark today's date for this habit
            from datetime import date
            today = date.today().isoformat()
            save_habit_date(habit_name, today, user_id)
            return f"Awesome! I've marked '{habit_name}' as completed for today. Keep up the great work!"
    
    for pattern in delete_patterns:
        match = re.search(pattern, command_lower)
        if match:
            habit_name = match.group(1).strip()
            delete_habit_from_db(habit_name, user_id)
            return f"I've removed '{habit_name}' from your habits tracker."
    
    for pattern in show_patterns:
        if re.search(pattern, command_lower):
            habits = get_habits_from_db(user_id)
            if habits:
                habit_list = list(habits.keys())
                return f"Your current habits are: {', '.join(habit_list)}. Great job staying consistent!"
            else:
                return "You don't have any habits yet. Try saying 'Add a habit to drink water' to get started!"
    
    # Default response
    return "I heard you, but I'm not sure how to help with that. Try saying things like 'Add a habit to exercise' or 'Mark reading as complete'."

@app.route('/api/voice', methods=['POST'])
@jwt_required()
def handle_voice():
    """Handle voice command requests with intelligent processing"""
    try:
        print("🎤 Voice request received")
        if 'audio' not in request.files:
            print("❌ No audio file in request")
            return jsonify({'success': False, 'error': 'No audio file provided', 'details': 'Missing audio file in request.'}), 400

        audio_file = request.files['audio']
        audio_size = len(audio_file.read())
        audio_file.seek(0)  # Reset file pointer after reading size
        print(f"📁 Audio file: {getattr(audio_file, 'filename', 'unknown')}, size: {audio_size}")

        # Get user_id from JWT
        user_id = int(get_jwt_identity())

        # Check if audio file has content
        if audio_size == 0:
            print("❌ Empty audio file received")
            return jsonify({
                'success': False, 
                'error': 'Empty audio file', 
                'transcript': '',
                'reply': 'I didn\'t receive any audio. Please try recording again and make sure your microphone is working.',
                'action': 'error'
            }), 400

        # Try the new Whisper-based processing first
        if WHISPER_ENABLED:
            try:
                print("🎤 Using Whisper-based voice processing...")
                
                # Read audio bytes
                audio_bytes = audio_file.read()
                audio_file.seek(0)  # Reset for potential fallback
                
                from whisper_service import transcribe_audio_bytes
                
                # Attempt transcription
                print(f"🔊 Audio details: {len(audio_bytes)} bytes, format: {audio_file.filename}")
                transcription_result = transcribe_audio_bytes(audio_bytes, audio_file.filename or "audio.webm")
                
                print(f"📊 Transcription result: success={transcription_result.get('success')}, confidence={transcription_result.get('confidence', 0):.2f}")
                print(f"📄 Raw transcription result: {transcription_result}")
                
                if transcription_result.get('success'):
                    transcript = transcription_result.get('text', '').strip()
                    confidence = transcription_result.get('confidence', 0.0)
                    print(f"🎯 Whisper transcription: '{transcript}' (confidence: {confidence:.2f})")
                    
                    # Additional validation
                    if len(transcript) < 3:
                        print(f"⚠️ Transcript too short: '{transcript}' - likely noise or unclear speech")
                        return jsonify({
                            'success': False,
                            'transcript': transcript,
                            'reply': 'I heard something but it was too short to understand. Please try speaking more clearly.',
                            'action': 'error',
                            'debug_info': transcription_result
                        }), 400
                    
                    if transcript:
                        # Process through unified pipeline
                        chat_response = process_unified_message(transcript, user_id, is_voice=True)
                        
                        return jsonify({
                            'success': True,
                            'transcript': transcript,
                            'reply': chat_response.get('reply', ''),
                            'action': chat_response.get('processing_type', 'conversation'),
                            'action_taken': chat_response.get('action_taken', False),
                            'habit_action': chat_response.get('habit_action', {}),
                            'frontend_action': chat_response.get('frontend_action')  # New: Frontend actions
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'transcript': '',
                            'reply': 'I couldn\'t understand what you said. Please try speaking more clearly.',
                            'action': 'error'
                        }), 400
                else:
                    print(f"⚠️ Whisper transcription failed: {transcription_result.get('error')}")
                    # Fall through to old system
            except Exception as e:
                print(f"⚠️ Whisper processing failed: {e}")
                # Fall through to old system

        # Fallback to old voice system if Whisper fails or not available
        if VOICE_ENABLED and 'handle_voice_command' in globals():
            try:
                print("🎤 Falling back to legacy voice processing...")
                result = handle_voice_command(audio_file, user_id)
                print(f"✅ Legacy voice processing result: {result}")
                
                # Check if we got a valid transcript (not an error message)
                transcript = result.get('transcript', '')
                is_valid_transcript = (
                    transcript and 
                    len(transcript.strip()) > 0 and
                    'error' not in transcript.lower() and
                    'couldn\'t understand' not in transcript.lower() and
                    'please speak clearly' not in transcript.lower() and
                    'try again' not in transcript.lower() and
                    'speech recognition not fully installed' not in transcript.lower() and
                    'sorry, i couldn\'t process' not in transcript.lower() and
                    'service is temporarily unavailable' not in transcript.lower()
                )
                
                if is_valid_transcript:
                    try:
                        print(f"🧠 Processing valid transcript: '{transcript}'")
                        # Process through unified pipeline
                        chat_response = process_unified_message(transcript, user_id, is_voice=True)
                        
                        # Merge results
                        result['reply'] = chat_response.get('reply', result.get('reply', ''))
                        result['action_taken'] = chat_response.get('action_taken', False)
                        result['habit_action'] = chat_response.get('habit_action', {})
                        result['processing_type'] = chat_response.get('processing_type', 'conversation')
                        result['success'] = True
                        
                        print(f"✅ Enhanced voice processing result: {result}")
                        return jsonify(result)
                    except Exception as e:
                        print(f"⚠️ Enhanced processing failed: {e}")
                else:
                    print(f"⚠️ Invalid transcript detected, treating as speech recognition failure: '{transcript}'")
                    # Return speech recognition error without processing through intent system
                    return jsonify({
                        'success': False,
                        'transcript': '',
                        'reply': 'I had trouble understanding your voice command. Please try speaking more clearly or use the text chat instead.',
                        'action': 'speech_recognition_error',
                        'error': 'Speech recognition failed'
                    }), 400
                
                # Add success field to the response for other cases
                if result and isinstance(result, dict) and 'reply' in result:
                    result['success'] = True
                    if 'transcript' not in result:
                        result['transcript'] = result.get('transcript', 'Voice command processed')
                    return jsonify(result)
                
            except Exception as ve:
                print(f"❌ Exception in legacy voice processing: {ve}")
        
        # Final fallback
        return jsonify({
            'success': False,
            'transcript': '',
            'reply': 'Sorry, I couldn\'t process your voice command. Please try typing your message instead.',
            'action': 'error'
        }), 503

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"❌ Voice processing error: {str(e)}\n{tb}")
        # Always return valid JSON
        return jsonify({
            'success': False,
            'transcript': '',
            'reply': 'Sorry, there was an error processing your voice command.',
            'action': 'error',
            'details': str(e),
            'traceback': tb
        }), 500

# JWT authentication now handled by Flask-JWT-Extended decorators

# JWT authentication now handled by Flask-JWT-Extended decorators

if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print(f"📍 Server will be available at: http://localhost:8091")
    print("🔧 Debug mode: ON")
    print("=" * 50)
    
    # Start the Flask development server
    app.run(
        host='0.0.0.0',  # Allow connections from all interfaces
        port=8091,       # Using port 8091 to avoid conflicts
        debug=True,      # Enable debug mode for development
        threaded=True    # Enable threading for concurrent requests
    )
