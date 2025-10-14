import os
import tempfile
import subprocess
import re
import datetime
from flask import request, jsonify
import json

# Try to import speech recognition - fallback to simpler approach if not available
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

def handle_voice_command(audio_file, user_id):
    """Process voice commands using speech recognition and respond appropriately"""
    try:
        # Save the audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
            tmp_file.write(audio_file.read())
            tmp_file_path = tmp_file.name
        
        transcript = ""
        
        if SPEECH_RECOGNITION_AVAILABLE:
            # Convert webm to wav for speech recognition
            try:
                r = sr.Recognizer()
                r.energy_threshold = 300  # Adjust for background noise
                r.dynamic_energy_threshold = True
                
                # Convert webm to wav using ffmpeg
                wav_path = tmp_file_path.replace('.webm', '.wav')
                
                print(f"Converting audio from {tmp_file_path} to {wav_path}")
                
                # Convert using ffmpeg with better settings
                result = subprocess.run([
                    'ffmpeg', '-i', tmp_file_path, 
                    '-acodec', 'pcm_s16le',  # 16-bit PCM
                    '-ar', '16000',          # Sample rate 16kHz
                    '-ac', '1',              # Mono channel
                    '-y',                    # Overwrite output
                    wav_path
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"FFmpeg error: {result.stderr}")
                    raise subprocess.CalledProcessError(result.returncode, "ffmpeg")
                
                print(f"Audio converted successfully to {wav_path}")
                
                # Now try to recognize the WAV file
                with sr.AudioFile(wav_path) as source:
                    # Adjust for ambient noise
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = r.record(source)
                    
                    print("Attempting speech recognition...")
                    transcript = r.recognize_google(audio_data)
                    print(f"Recognized: {transcript}")
                
                # Clean up WAV file
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
                    
            except subprocess.CalledProcessError as e:
                print(f"FFmpeg conversion failed: {e}")
                transcript = "Sorry, I couldn't process the audio format. Please try again."
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
                transcript = "I couldn't understand what you said. Please speak clearly and try again."
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service: {e}")
                transcript = "Speech recognition service is temporarily unavailable."
            except Exception as e:
                print(f"Speech recognition error: {e}")
                transcript = "There was an error processing your voice. Please try again."
        else:
            # Fallback - simulate speech recognition for demo
            transcript = "Voice command received (speech recognition not fully installed)"
        
        # Clean up original temp file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        
        # Process the command
        if transcript and len(transcript.strip()) > 0 and "couldn't" not in transcript and "error" not in transcript:
            command_result = process_command(transcript, user_id)
            return {
                'transcript': transcript,
                **command_result
            }
        else:
            return {
                'transcript': transcript,
                'reply': transcript if "couldn't" in transcript or "error" in transcript else "I didn't catch that. Could you please try speaking again?",
                'action': 'error'
            }
        
    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        return {
            'transcript': '',
            'reply': "Sorry, there was an error processing your voice command. Please try again.",
            'action': 'error'
        }

def process_command(text, user_id):
    """Parse and process the transcribed command"""
    text_lower = text.lower()
    
    # Check for task commands first
    task_result = check_task_commands(text_lower, text, user_id)
    if task_result:
        return task_result
    
    # Check for habit tracking commands
    habit_result = check_habit_commands(text_lower, user_id)
    if habit_result:
        return habit_result
    
    # Check for general assistant commands
    general_result = check_general_commands(text_lower, text)
    if general_result:
        return general_result
    
    # If no specific command is detected, treat as a chat message
    from assistant import get_ai_reply
    reply = get_ai_reply(text)
    
    return {
        'reply': reply,
        'action': 'chat'
    }

def check_task_commands(text_lower, original_text, user_id):
    """Check for task-related commands"""
    
    # Add task/event patterns
    add_task_patterns = [
        r"(add|create|schedule|plan|set up|make|new)\s+(task|event|appointment|meeting|reminder|todo|item)",
        r"(remind me to|schedule|plan to|need to|have to|should)\s+(.+)",
        r"(tomorrow|today|next week|this week|monday|tuesday|wednesday|thursday|friday|saturday|sunday).+(meeting|appointment|call|task|event)"
    ]
    
    # Check for add task commands
    for pattern in add_task_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # Extract task details
            task_text = extract_task_from_text(original_text)
            date_time = extract_datetime_from_text(original_text)
            
            if task_text:
                from app import create_task_via_voice
                result = create_task_via_voice(task_text, date_time, user_id)
                
                return {
                    'reply': f"I've added '{task_text}' to your tasks{' for ' + date_time if date_time else ''}.",
                    'action': 'task_updated',
                    'task_added': task_text
                }
    
    # Complete task patterns
    complete_patterns = [
        r"(complete|done|finished|mark as done|check off)\s+(.+)",
        r"(completed|did|finished)\s+(.+)"
    ]
    
    for pattern in complete_patterns:
        match = re.search(pattern, text_lower)
        if match:
            task_name = match.group(2).strip()
            
            return {
                'reply': f"Task completion will be available in the tasks page. You can mark '{task_name}' as complete there.",
                'action': 'task_info'
            }
    
    # List tasks patterns
    list_patterns = [
        r"(what|show|list|tell me).+(tasks|schedule|todo|events|appointments)",
        r"(what's|whats).+(on my|my).+(schedule|calendar|todo)",
        r"(show me|list).+(today|tomorrow|this week|next week)"
    ]
    
    for pattern in list_patterns:
        if re.search(pattern, text_lower):
            return {
                'reply': "You can view all your tasks on the Tasks page. I can help you add new tasks through voice commands!",
                'action': 'task_info'
            }
    
    return None

def extract_task_from_text(text):
    """Extract task description from natural language"""
    # Common patterns to extract the actual task
    patterns = [
        r"remind me to (.+)",
        r"schedule (.+)",
        r"add (.+) to",
        r"need to (.+)",
        r"have to (.+)",
        r"should (.+)",
        r"plan to (.+)",
        r"create (.+) task",
        r"new (.+) task",
        r"make (.+) appointment"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1).strip()
    
    # If no pattern matches, try to extract the main content
    # Remove common command words
    words_to_remove = ['add', 'create', 'schedule', 'plan', 'set up', 'make', 'new', 'task', 'event', 'appointment', 'meeting', 'reminder', 'todo', 'agenda', 'item']
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in words_to_remove]
    
    if len(filtered_words) > 2:
        return ' '.join(filtered_words)
    
    return text.strip()

def extract_datetime_from_text(text):
    """Extract date/time information from text"""
    text_lower = text.lower()
    
    # Simple date/time extraction
    if 'tomorrow' in text_lower:
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        return tomorrow.strftime('%Y-%m-%d')
    elif 'today' in text_lower:
        return datetime.date.today().strftime('%Y-%m-%d')
    elif 'next week' in text_lower:
        next_week = datetime.date.today() + datetime.timedelta(weeks=1)
        return next_week.strftime('%Y-%m-%d')
    elif 'this week' in text_lower:
        return datetime.date.today().strftime('%Y-%m-%d')
    
    # Days of the week
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(days):
        if day in text_lower:
            # Find the next occurrence of this day
            today = datetime.date.today()
            days_ahead = i - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            target_date = today + datetime.timedelta(days_ahead)
            return target_date.strftime('%Y-%m-%d')
    
    return None

def check_general_commands(text_lower, original_text):
    """Check for general assistant commands"""
    
    # Time/date queries
    if any(phrase in text_lower for phrase in ['what time', 'current time', 'what day', 'what date']):
        now = datetime.datetime.now()
        return {
            'reply': f"It's currently {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}.",
            'action': 'time_query'
        }
    
    # Weather (placeholder)
    if any(phrase in text_lower for phrase in ['weather', 'temperature', 'forecast']):
        return {
            'reply': "I don't have access to weather data yet, but you can check your local weather app or ask me to add weather integration!",
            'action': 'weather_query'
        }
    
    # System commands
    if any(phrase in text_lower for phrase in ['open', 'launch', 'start']):
        # Extract app name
        apps = ['safari', 'chrome', 'firefox', 'mail', 'calendar', 'notes', 'messages', 'facetime', 'music', 'spotify']
        for app in apps:
            if app in text_lower:
                return {
                    'reply': f"I would open {app} for you, but I need permission to control your system. You can manually open {app} for now.",
                    'action': 'system_command',
                    'app': app
                }
    
    return None

def check_habit_commands(text, user_id):
    """Enhanced habit command processing with better pattern recognition"""
    text_lower = text.lower()
    
    # Enhanced patterns for habit creation
    add_habit_patterns = [
        r"(?:add|create|start|begin|track|make).*?(?:habit|routine).*?(?:called|named|for|to)?[\s\"]*([^\".,!?]+)[\s\"]*",
        r"(?:i (?:want to|need to|should)).*?(?:start|begin|track).*?([^.,!?]+)(?:daily|every day|regularly)",
        r"(?:help me|remind me to).*?(?:track|build|start).*?(?:habit|routine).*?(?:of|for)?[\s\"]*([^\".,!?]+)[\s\"]*",
        r"(?:new|a).*?habit.*?(?:called|named|for|to)?[\s\"]*([^\".,!?]+)[\s\"]*",
        r"track.*?([^.,!?]+)(?:daily|every day|regularly|as a habit)"
    ]
    
    # NEW: Enhanced patterns for habit deletion/removal
    delete_habit_patterns = [
        r"(?:remove|delete|stop|quit|cancel).*?(?:habit|routine).*?(?:called|named)?[\s\"]*([^\".,!?]+)[\s\"]*",
        r"(?:remove|delete|stop|quit|cancel).*?(?:the)?[\s\"]*([^\".,!?]+)[\s\"]*(?:habit|routine)?",
        r"(?:don't want to|no longer want to|stop).*?(?:track|do).*?([^.,!?]+)(?:anymore|any more)?",
        r"(?:get rid of|eliminate).*?(?:habit|routine)?.*?(?:called|named)?[\s\"]*([^\".,!?]+)[\s\"]*",
        r"(?:i want to|need to|should).*?(?:remove|delete|stop|quit).*?([^.,!?]+)(?:habit|routine)?"
    ]
    
    # Enhanced patterns for habit completion
    complete_habit_patterns = [
        r"(?:mark|complete|did|finished|done|check off|completed).*?([^.,!?]+)(?:today|for today|now)?",
        r"(?:i|just).*?(?:did|finished|completed).*?([^.,!?]+)(?:today|now)?",
        r"(?:completed|done with|finished).*?([^.,!?]+)",
        r"([^.,!?]+).*?(?:is|was).*?(?:done|completed|finished)(?:today|now)?"
    ]
    
    # Enhanced patterns for habit tracking/status
    track_habit_patterns = [
        r"(?:how am i doing|progress|status).*?(?:with|on).*?([^.,!?]+)",
        r"(?:show|tell me).*?(?:progress|status).*?(?:for|on|with).*?([^.,!?]+)",
        r"(?:what's my|whats my).*?(?:progress|streak).*?(?:for|on|with).*?([^.,!?]+)"
    ]
    
    # Check for habit deletion FIRST (before creation patterns)
    for pattern in delete_habit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            habit_name = clean_habit_name(match.group(1))
            if habit_name and len(habit_name) > 2:
                try:
                    from app import delete_habit_from_db, get_habits_from_db
                    
                    # Find the habit by name (case-insensitive partial matching)
                    habits = get_habits_from_db(user_id)
                    matching_habit = None
                    
                    # habits is returned as {habit_name: {dates: {}, color: ''}}
                    for habit_name_from_db, habit_data in habits.items():
                        # Check if the spoken name matches the database name
                        if (habit_name.lower() in habit_name_from_db.lower() or 
                            habit_name_from_db.lower() in habit_name.lower() or
                            habit_name.lower() == habit_name_from_db.lower()):
                            matching_habit = habit_name_from_db
                            break
                    
                    if matching_habit:
                        delete_habit_from_db(matching_habit, user_id)
                        return {
                            'reply': f"✅ I've successfully removed '{matching_habit}' from your habits. Great job on recognizing when it's time to adjust your routine! 💪",
                            'action': 'habit_deleted'
                        }
                    else:
                        # Show available habits for debugging
                        available_habits = list(habits.keys())
                        return {
                            'reply': f"I couldn't find a habit matching '{habit_name}' in your current habits. Your current habits are: {', '.join(available_habits)}. Could you try again with the exact name?",
                            'action': 'habit_not_found'
                        }
                except Exception as e:
                    return {
                        'reply': f"I'd love to remove '{habit_name}' for you, but the habit system isn't responding right now. You can remove it manually on the habits page.",
                        'action': 'habit_error'
                    }
    
    # Check for adding new habits
    for pattern in add_habit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            habit_name = clean_habit_name(match.group(1))
            if habit_name and len(habit_name) > 2:
                try:
                    from app import add_habit_to_db
                    add_habit_to_db(habit_name, user_id)
                    
                    return {
                        'reply': f"Perfect! I've added '{habit_name}' to your habit tracker. 🌟 Building consistent habits is the key to success! You can find it on your habits page and I can help you track it daily through voice commands.",
                        'action': 'habit_created'
                    }
                except Exception as e:
                    return {
                        'reply': f"I'd love to add '{habit_name}' as a habit for you, but the habit system isn't responding right now. You can add it manually on the habits page.",
                        'action': 'habit_error'
                    }
    
    # Check for completing habits
    for pattern in complete_habit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            habit_name = clean_habit_name(match.group(1))
            if habit_name and len(habit_name) > 2:
                try:
                    from app import get_habits_from_db, save_habit_date
                    import datetime
                    
                    habits = get_habits_from_db(user_id)
                    best_match = find_best_habit_match(habit_name, habits.keys())
                    
                    if best_match:
                        today = datetime.date.today().isoformat()
                        save_habit_date(best_match, today, user_id)
                        
                        return {
                            'reply': f"Excellent! 🎉 I've marked '{best_match}' as completed for today. You're building great momentum - keep it up!",
                            'action': 'habit_updated'
                        }
                    else:
                        # Suggest creating new habit if not found
                        return {
                            'reply': f"I couldn't find a habit called '{habit_name}' in your tracker. Would you like me to create it as a new habit? Just say 'add habit {habit_name}' and I'll set it up for you!",
                            'action': 'habit_not_found'
                        }
                except Exception as e:
                    return {
                        'reply': f"I understand you completed '{habit_name}', but I'm having trouble updating your habit tracker right now. Please mark it manually on the habits page.",
                        'action': 'habit_error'
                    }
    
    # Check for habit progress/status queries
    for pattern in track_habit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            habit_name = clean_habit_name(match.group(1))
            if habit_name and len(habit_name) > 2:
                try:
                    from app import get_habits_from_db
                    habits = get_habits_from_db(user_id)
                    best_match = find_best_habit_match(habit_name, habits.keys())
                    
                    if best_match:
                        habit_data = habits[best_match]
                        dates = habit_data.get('dates', {})
                        
                        # Calculate some basic stats
                        total_days = len([date for date, completed in dates.items() if completed])
                        this_month = len([date for date, completed in dates.items() 
                                        if completed and date.startswith(datetime.date.today().strftime('%Y-%m'))])
                        
                        return {
                            'reply': f"Great question! For your '{best_match}' habit: You've completed it {total_days} times total, and {this_month} times this month. Check your habits page for the full visual progress and streak information!",
                            'action': 'habit_status'
                        }
                    else:
                        return {
                            'reply': f"I couldn't find a habit called '{habit_name}' to show progress for. You can see all your habits and their progress on the habits page.",
                            'action': 'habit_not_found'
                        }
                except Exception as e:
                    return {
                        'reply': f"I'd love to show you progress for '{habit_name}', but I'm having trouble accessing your habit data right now. Please check the habits page for visual progress.",
                        'action': 'habit_error'
                    }
    
    # Enhanced task creation (separate from habits)
    task_patterns = [
        r"(?:add|create|make|schedule).*?(?:task|todo|reminder|appointment).*?(?:called|named|for|to)?[\s\"]*([^\".,!?]+)[\s\"]*",
        r"(?:remind me to|i need to|i have to|i should)[\s]*([^.,!?]+)",
        r"(?:create|add|make).*?(?:a |an )?(?:task|todo|reminder).*?([^.,!?]+)"
    ]
    
    for pattern in task_patterns:
        match = re.search(pattern, text_lower)
        if match:
            task_title = clean_habit_name(match.group(1))
            if task_title and len(task_title) > 2:
                try:
                    import datetime
                    from app import create_task_in_db
                    
                    # Smart priority and category detection
                    priority = 'medium'
                    category = 'other'
                    
                    task_lower = task_title.lower()
                    if any(word in task_lower for word in ['urgent', 'asap', 'important', 'critical']):
                        priority = 'high'
                    elif any(word in task_lower for word in ['someday', 'maybe', 'eventually']):
                        priority = 'low'
                    
                    if any(word in task_lower for word in ['meeting', 'call', 'work', 'project']):
                        category = 'work'
                    elif any(word in task_lower for word in ['exercise', 'health', 'doctor']):
                        category = 'health'
                    
                    task_data = {
                        'title': task_title,
                        'description': f'Created via voice command',
                        'priority': priority,
                        'category': category,
                        'dueDate': None,
                        'createdAt': datetime.datetime.now().isoformat()
                    }
                    
                    success = create_task_in_db(task_data)
                    if success:
                        return {
                            'reply': f"Perfect! ✅ I've created the task '{task_title}' with {priority} priority. You can find it in your tasks page and mark it complete when done!",
                            'action': 'task_created'
                        }
                    else:
                        return {
                            'reply': f"I understood you want to create the task '{task_title}', but I'm having trouble saving it right now. Please add it manually on the tasks page.",
                            'action': 'task_error'
                        }
                except Exception as e:
                    return {
                        'reply': f"I'd love to create that task '{task_title}' for you, but the task system isn't available right now. You can add it manually on the tasks page.",
                        'action': 'task_error'
                    }
    
    return None

def clean_habit_name(name):
    """Clean and normalize habit/task names"""
    if not name:
        return ""
    
    # Remove common noise words
    noise_words = ['the', 'a', 'an', 'my', 'this', 'that', 'for', 'to', 'of', 'with', 'habit', 'task', 'daily', 'every day']
    words = name.strip().split()
    cleaned_words = [w for w in words if w.lower() not in noise_words]
    
    # Join back and clean up
    cleaned = ' '.join(cleaned_words).strip()
    
    # Remove quotes and extra punctuation
    cleaned = re.sub(r'["\'\`]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.title()  # Title case for consistency

def find_best_habit_match(target, habit_names):
    """Find the best matching habit name using fuzzy matching"""
    target_lower = target.lower()
    
    # Exact match first
    for habit in habit_names:
        if habit.lower() == target_lower:
            return habit
    
    # Partial match
    for habit in habit_names:
        if target_lower in habit.lower() or habit.lower() in target_lower:
            return habit
    
    # Word overlap match
    target_words = set(target_lower.split())
    best_match = None
    best_score = 0
    
    for habit in habit_names:
        habit_words = set(habit.lower().split())
        overlap = len(target_words.intersection(habit_words))
        if overlap > best_score:
            best_score = overlap
            best_match = habit
    
    return best_match if best_score > 0 else None
