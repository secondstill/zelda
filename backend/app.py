import os
from flask import Flask, render_template, jsonify, request, abort, redirect, url_for, session, flash
from werkzeug.middleware.proxy_fix import ProxyFix
import hashlib
import json
import sqlite3
from assistant import get_ai_reply, get_motivation_message
from functools import wraps
import secrets
import datetime

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

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key
app.wsgi_app = ProxyFix(app.wsgi_app)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

DB_FILE = 'habits.db'

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
    
    # Create habit_dates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_dates (
            habit_id INTEGER,
            date TEXT,
            checked INTEGER DEFAULT 0,
            PRIMARY KEY (habit_id, date),
            FOREIGN KEY (habit_id) REFERENCES habits (id)
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
    
    # Migrate any existing tasks table to include user_id if needed
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE tasks ADD COLUMN user_id INTEGER REFERENCES users(id)')
    
    conn.commit()
    conn.close()

init_db()

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash, full_name FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            session['full_name'] = user[2] or username
            flash('Welcome back!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form.get('full_name', '')
        
        # Validate input
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if username or email already exists
        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            flash('Username or email already exists', 'error')
            conn.close()
            return render_template('signup.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name)
            VALUES (?, ?, ?, ?)
        ''', (username, email, password_hash, full_name))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Log them in
        session['user_id'] = user_id
        session['username'] = username
        session['full_name'] = full_name or username
        flash('Account created successfully! Welcome to Zelda!', 'success')
        return redirect(url_for('home'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/habits')
@login_required
def habits():
    return render_template('habits.html')

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/chat-simple')
def chat_simple():
    """Educational version of the chat interface"""
    return render_template('chat_simple.html')

@app.route('/account')
@login_required
def account():
    return render_template('account.html')

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        user_id = session['user_id']
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
        
        # Update session
        session['full_name'] = full_name
        session['email'] = email
        session['username'] = username
        
        return jsonify({
            'success': True, 
            'message': 'Profile updated successfully',
            'created_at': created_at
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Task Management - DISABLED
# @app.route('/tasks')
# @login_required
# def tasks():
#     """Modern task management interface"""
#     return render_template('tasks.html')

# Task Management API Endpoints - DISABLED
# @app.route('/api/tasks', methods=['GET'])
# @login_required
# def get_tasks():
#     """Get all tasks from database for the current user"""
#     try:
#         user_id = session['user_id']
#         conn = sqlite3.connect(DB_FILE)
#         conn.row_factory = sqlite3.Row
#         cursor = conn.cursor()
#         
#         cursor.execute('''
#             SELECT * FROM tasks WHERE user_id = ? ORDER BY 
#             CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
#             created_at DESC
#         ''', (user_id,))
#         
#         tasks = []
#         for row in cursor.fetchall():
#             tasks.append({
#                 'id': row['id'],
#                 'title': row['title'],
#                 'description': row['description'],
#                 'priority': row['priority'],
#                 'category': row['category'],
#                 'dueDate': row['due_date'],
#                 'completed': bool(row['completed']),
#                 'createdAt': row['created_at']
#             })
#         
#         conn.close()
#         return jsonify({'success': True, 'tasks': tasks})
#         
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500

# @app.route('/api/tasks', methods=['POST'])
# @login_required
# def create_task():
#     """Create a new task for the current user"""
#     try:
#         user_id = session['user_id']
#         data = request.get_json()
#         
#         conn = sqlite3.connect(DB_FILE)
#         cursor = conn.cursor()
#         
#         cursor.execute('''
#             INSERT INTO tasks (user_id, title, description, priority, category, due_date, completed, created_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         ''', (
#             user_id,
#             data['title'],
#             data.get('description', ''),
#             data.get('priority', 'medium'),
#             data.get('category', 'other'),
#             data.get('dueDate'),
#             False,
#             data['createdAt']
#         ))
#         
#         conn.commit()
#         task_id = cursor.lastrowid
#         conn.close()
#         
#         return jsonify({'success': True, 'task_id': task_id})
#         
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500

# @app.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
# @login_required
# def complete_task(task_id):
#     """Mark a task as completed (only user's own task)"""
#     try:
#         user_id = session['user_id']
#         conn = sqlite3.connect(DB_FILE)
#         cursor = conn.cursor()
#         
#         # Verify the task belongs to the user
#         cursor.execute('SELECT id FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
#         if not cursor.fetchone():
#             return jsonify({'success': False, 'error': 'Task not found'}), 404
#         
#         cursor.execute('UPDATE tasks SET completed = 1 WHERE id = ? AND user_id = ?', (task_id, user_id))
#         conn.commit()
#         conn.close()
#         
#         return jsonify({'success': True})
#         
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500

# @app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
# @login_required
# def delete_task(task_id):
#     """Delete a task (only user's own task)"""
#     try:
#         user_id = session['user_id']
#         conn = sqlite3.connect(DB_FILE)
#         cursor = conn.cursor()
#         
#         # Verify the task belongs to the user
#         cursor.execute('SELECT id FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
#         if not cursor.fetchone():
#             return jsonify({'success': False, 'error': 'Task not found'}), 404
#         
#         cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
#         conn.commit()
#         conn.close()
#         
#         return jsonify({'success': True})
#         
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user-stats')
@login_required
def get_user_stats():
    """Get comprehensive user statistics"""
    try:
        user_id = session['user_id']
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get habits count
        cursor.execute('SELECT COUNT(*) as count FROM habits WHERE user_id = ?', (user_id,))
        habits_count = cursor.fetchone()['count']
        
        # Get habit entries for completion rate calculation
        cursor.execute('''
            SELECT COUNT(*) as total_entries, 
                   SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_entries 
            FROM habit_entries he
            JOIN habits h ON he.habit_id = h.id
            WHERE h.user_id = ? AND he.date >= date('now', '-7 days')
        ''', (user_id,))
        habit_stats = cursor.fetchone()
        total_entries = habit_stats['total_entries'] or 0
        completed_entries = habit_stats['completed_entries'] or 0
        completion_rate = int((completed_entries / total_entries * 100)) if total_entries > 0 else 0
        
        # Get habit streak (days with any habit completed)
        cursor.execute('''
            SELECT COUNT(DISTINCT date) as streak_days
            FROM habit_entries he
            JOIN habits h ON he.habit_id = h.id
            WHERE h.user_id = ? AND he.completed = 1
            AND he.date >= date('now', '-30 days')
        ''', (user_id,))
        streak_result = cursor.fetchone()
        current_streak = streak_result['streak_days'] if streak_result else 0
        
        # Get habit completion entries for this month
        cursor.execute('''
            SELECT COUNT(*) as completions
            FROM habit_entries he
            JOIN habits h ON he.habit_id = h.id
            WHERE h.user_id = ? AND he.completed = 1
            AND strftime('%Y-%m', he.date) = strftime('%Y-%m', 'now')
        ''', (user_id,))
        monthly_completions = cursor.fetchone()['completions']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'habits_count': habits_count,
                'completion_rate': completion_rate,
                'current_streak': current_streak,
                'monthly_completions': monthly_completions
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/motivation')
@login_required
def get_motivation():
    message = get_motivation_message()
    return jsonify({'motivation': message})

# --- HABIT TRACKER MULTI-HABIT SUPPORT ---
# habits.json structure:
# {
#   "Habit Name": {"dates": {"YYYY-MM-DD": true, ...}, "color": "#hex"},
#   ...
# }

def create_task_via_voice(task_title, date_time, user_id):
    """Helper function to create a task via voice command"""
    try:
        import datetime
        task_data = {
            'title': task_title,
            'description': f'Created via voice command',
            'priority': 'medium',
            'category': 'voice',
            'dueDate': date_time,
            'createdAt': datetime.datetime.now().isoformat()
        }
        return create_task_in_db(task_data, user_id)
    except Exception as e:
        print(f"Error creating task via voice: {e}")
        return False

def create_task_in_db(task_data, user_id):
    """Helper function to create a task in the database (used by voice assistant)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (title, description, priority, category, due_date, completed, created_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_data['title'],
            task_data.get('description', ''),
            task_data.get('priority', 'medium'),
            task_data.get('category', 'other'),
            task_data.get('dueDate'),
            False,
            task_data['createdAt'],
            user_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error creating task: {e}")
        return False

def get_habits_from_db(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Get user-specific habits
        c.execute('SELECT id, name, color FROM habits WHERE user_id = ?', (user_id,))
        rows = c.fetchall()
        
        habits = {}
        for habit_id, name, color in rows:
            # Get habit entries for this user and habit
            c.execute('SELECT date, completed FROM habit_entries WHERE user_id = ? AND habit_id = ?', (user_id, habit_id))
            dates = {row[0]: bool(row[1]) for row in c.fetchall()}
            habits[name] = {'dates': dates, 'color': color or '#2ecc40'}
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        habits = {}
    
    conn.close()
    return habits

def save_habit_date(habit_name, date, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get or create habit for this user
    c.execute('SELECT id FROM habits WHERE name = ? AND user_id = ?', (habit_name, user_id))
    row = c.fetchone()
    if not row:
        c.execute('INSERT INTO habits (name, user_id) VALUES (?, ?)', (habit_name, user_id))
        habit_id = c.lastrowid
    else:
        habit_id = row[0]
    
    # Toggle habit entry for this date
    c.execute('SELECT completed FROM habit_entries WHERE habit_id = ? AND date = ? AND user_id = ?', (habit_id, date, user_id))
    row = c.fetchone()
    if row:
        new_completed = 0 if row[0] else 1
        c.execute('UPDATE habit_entries SET completed = ? WHERE habit_id = ? AND date = ? AND user_id = ?', 
                 (new_completed, habit_id, date, user_id))
    else:
        new_completed = 1
        c.execute('INSERT INTO habit_entries (user_id, habit_id, date, completed) VALUES (?, ?, ?, ?)', 
                 (user_id, habit_id, date, new_completed))
    
    conn.commit()
    conn.close()

def add_habit_to_db(habit_name, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO habits (name, user_id) VALUES (?, ?)', (habit_name, user_id))
        conn.commit()
    except sqlite3.IntegrityError:
        # Habit already exists for this user, ignore
        pass
    conn.close()

def update_habit_color_in_db(habit_name, color, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE habits SET color=? WHERE name=? AND user_id=?', (color, habit_name, user_id))
    conn.commit()
    conn.close()

def rename_habit_in_db(old_name, new_name, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE habits SET name=? WHERE name=? AND user_id=?', (new_name, old_name, user_id))
    conn.commit()
    conn.close()

def delete_habit_from_db(habit_name, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM habits WHERE name=? AND user_id=?', (habit_name, user_id))
    conn.commit()
    conn.close()

# --- HABIT TRACKING API ENDPOINTS ---

@app.route('/api/habits', methods=['GET', 'POST'])
@login_required
def habits_api():
    user_id = session['user_id']
    if request.method == 'POST':
        habit_name = request.json.get('habit')
        date = request.json.get('date')
        if habit_name and date:
            save_habit_date(habit_name, date, user_id)
    habits = get_habits_from_db(user_id)
    return jsonify({'habits': habits})

@app.route('/api/habits/new', methods=['POST'])
@login_required
def add_habit():
    user_id = session['user_id']
    habit_name = request.json.get('habit')
    if habit_name:
        add_habit_to_db(habit_name, user_id)
    habits = get_habits_from_db(user_id)
    return jsonify({'habits': habits})

@app.route('/api/habits/color', methods=['POST'])
@login_required
def update_habit_color():
    user_id = session['user_id']
    habit_name = request.json.get('habit')
    color = request.json.get('color')
    if habit_name and color:
        update_habit_color_in_db(habit_name, color, user_id)
    habits = get_habits_from_db(user_id)
    return jsonify({'habits': habits})

@app.route('/api/habits/rename', methods=['POST'])
@login_required
def rename_habit():
    user_id = session['user_id']
    old = request.json.get('old')
    new = request.json.get('new')
    if old and new:
        rename_habit_in_db(old, new, user_id)
    habits = get_habits_from_db(user_id)
    return jsonify({'habits': habits})

@app.route('/api/habits/delete', methods=['POST'])
@login_required
def delete_habit():
    user_id = session['user_id']
    habit = request.json.get('habit')
    if habit:
        delete_habit_from_db(habit, user_id)
    habits = get_habits_from_db(user_id)
    return jsonify({'habits': habits})

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    user_id = session['user_id']
    user_message = request.json.get('message', '')
    
    # Proactively detect and create habits/tasks from user messages
    detected_actions = detect_and_create_items(user_message, user_id)
    
    reply = get_ai_reply(user_message)
    
    # If we detected and created something, modify the reply to acknowledge it
    if detected_actions:
        if detected_actions.get('habits'):
            habit_names = ", ".join(detected_actions['habits'])
            reply = f"Perfect! I've added '{habit_names}' to your habits tracker. {reply}"
        if detected_actions.get('tasks'):
            task_names = ", ".join(detected_actions['tasks'])
            reply = f"Great! I've created the task '{task_names}' for you. {reply}"
    
    # Store the conversation in user-specific chat history
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (user_id, message, response)
            VALUES (?, ?, ?)
        ''', (user_id, user_message, reply))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error storing chat history: {e}")  # Log but don't fail the chat
    
    return jsonify({'reply': reply, 'success': True})

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
    
    # Task detection patterns  
    task_patterns = [
        r"i need to (?:do|complete|finish|work on) ([^.,!?]+)",
        r"(?:create|add|make) (?:a |the )?task[:\s]+['\"]?([^'\".,!?]+)['\"]?",
        r"remind me to ([^.,!?]+)",
        r"i have to ([^.,!?]+)",
        r"(?:schedule|plan) ([^.,!?]+)",
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
    
    # Check for tasks
    for pattern in task_patterns:
        matches = re.findall(pattern, message_lower, re.IGNORECASE)
        for match in matches:
            task_title = match.strip().title()
            if task_title and len(task_title) > 2:
                task_data = {
                    'title': task_title,
                    'description': '',
                    'priority': 'medium',
                    'category': 'other',
                    'dueDate': None,
                    'createdAt': datetime.now().isoformat()
                }
                if create_task_in_db(task_data, user_id):
                    created_items['tasks'].append(task_title)
    
    return created_items if (created_items['habits'] or created_items['tasks']) else None

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

@app.route('/api/voice', methods=['POST'])
@login_required
def handle_voice():
    """Handle voice command requests"""
    try:
        print("🎤 Voice request received")
        
        if 'audio' not in request.files:
            print("❌ No audio file in request")
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        print(f"📁 Audio file: {audio_file.filename}, size: {audio_file.content_length}")
        
        # Get user_id from session
        user_id = session['user_id']
        
        # Process the voice command
        result = handle_voice_command(audio_file, user_id)
        print(f"✅ Voice processing result: {result}")
        
        # Add success field to the response
        if result and 'reply' in result:
            result['success'] = True
            if 'transcript' not in result:
                result['transcript'] = result.get('transcript', 'Voice command processed')
        else:
            result = {
                'success': False,
                'transcript': '',
                'reply': 'Sorry, I couldn\'t process that command.',
                'action': 'error'
            }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Voice processing error: {str(e)}")
        return jsonify({
            'success': False,
            'transcript': '',
            'reply': 'Sorry, there was an error processing your voice command.',
            'action': 'error'
        }), 500

if __name__ == '__main__':
    # For local development with HTTPS (required for microphone access)
    import ssl
    
    try:
        # Create a simple SSL context for development
        # This allows microphone access in browsers
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Try to use adhoc certificates (Flask will generate them)
        print("🔐 Starting HTTPS server for voice functionality...")
        print("📱 Accept the security warning in your browser for localhost")
        print("🌐 Open: https://127.0.0.1:8080")
        app.run(debug=False, port=8080, host='127.0.0.1', ssl_context='adhoc')

    except Exception as e:
        print(f"⚠️  Could not start HTTPS server: {e}")
        print("🎙️  Falling back to HTTP - voice functionality will be limited")
        print("🌐 Open: http://127.0.0.1:8080")
        app.run(debug=False, port=8080, host='127.0.0.1')
