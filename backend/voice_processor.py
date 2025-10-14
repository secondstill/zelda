"""
Voice Command Processor Module

This module handles natural language voice commands for habit management using OpenAI.
It processes user voice commands and translates them into specific actions like adding,
completing, editing, or deleting habits.
"""

import re
import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any

# OpenAI integration (optional, falls back to pattern matching if not available)
try:
    from openai import OpenAI
    import os
    
    # Try to get OpenAI API key from environment variable
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
        print("✅ OpenAI API integration enabled")
    else:
        openai_client = None
        OPENAI_AVAILABLE = False
        print("⚠️ OpenAI API key not found in environment variables")
except ImportError:
    openai_client = None
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI package not installed, using pattern matching fallback")

DB_FILE = 'habits.db'

class VoiceCommandProcessor:
    """Main class for processing voice commands"""
    
    def __init__(self):
        self.action_patterns = {
            'add_habit': [
                r'add (?:a |the )?habit (?:called |named |to |for )?(.+)',
                r'create (?:a |the )?habit (?:called |named |to |for )?(.+)',
                r'start tracking (.+)',
                r'i want to (?:track|start) (.+)',
                r'help me track (.+)',
                r'new habit (?:called |named )?(.+)',
            ],
            'complete_habit': [
                r'mark (.+) (?:as )?(?:complete|completed|done)',
                r'complete (?:the )?(.+)',
                r'i (?:did|completed|finished) (?:the )?(.+)',
                r'finished (?:the )?(.+)',
                r'done with (?:the )?(.+)',
            ],
            'delete_habit': [
                r'delete (?:the )?habit (.+)',
                r'remove (?:the )?habit (.+)',
                r'stop tracking (.+)',
                r'get rid of (.+)',
                r'cancel (?:the )?(.+) habit',
            ],
            'edit_habit': [
                r'rename (?:the )?habit (.+) to (.+)',
                r'change (.+) to (.+)',
                r'edit (?:the )?habit (.+)',
                r'modify (?:the )?(.+)',
            ],
            'show_habits': [
                r'show (?:me )?(?:my )?habits',
                r'list (?:my )?habits',
                r'what are my habits',
                r'display (?:my )?habits',
                r'view (?:my )?habits',
            ],
            'habit_status': [
                r'how am i doing with (.+)',
                r'status of (.+)',
                r'progress on (.+)',
                r'check (.+)',
            ]
        }
    
    def process_command(self, command: str, user_id: int) -> Dict[str, Any]:
        """
        Process a voice command and return appropriate response
        
        Args:
            command: The voice command text
            user_id: The user's ID
            
        Returns:
            Dictionary with response, action, and data
        """
        if not command or not command.strip():
            return {
                'response': 'I didn\'t hear anything. Could you please try again?',
                'action': 'error',
                'data': {}
            }
        
        command = command.strip().lower()
        print(f"🎤 Processing command: '{command}' for user {user_id}")
        
        # Try OpenAI processing first if available
        if OPENAI_AVAILABLE and OPENAI_API_KEY:
            try:
                result = self._process_with_ai(command, user_id)
                if result:
                    return result
            except Exception as e:
                print(f"⚠️ OpenAI processing failed: {e}, falling back to pattern matching")
        
        # Fallback to pattern matching
        return self._process_with_patterns(command, user_id)
    
    def _process_with_ai(self, command: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Process command using OpenAI"""
        try:
            # Get current habits for context
            habits = self._get_user_habits(user_id)
            habit_names = list(habits.keys()) if habits else []
            
            # Create prompt for OpenAI
            prompt = self._create_ai_prompt(command, habit_names)
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Zelda, a helpful habit tracking assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Parse AI response to extract action
            return self._parse_ai_response(ai_response, command, user_id)
            
        except Exception as e:
            print(f"❌ OpenAI processing error: {e}")
            return None
    
    def _create_ai_prompt(self, command: str, habit_names: List[str]) -> str:
        """Create a structured prompt for OpenAI"""
        habits_context = f"Current habits: {', '.join(habit_names)}" if habit_names else "No habits yet"
        
        return f"""
Analyze this voice command for habit tracking: "{command}"

{habits_context}

Respond with JSON in this exact format:
{{
    "action": "add_habit|complete_habit|delete_habit|edit_habit|show_habits|habit_status",
    "habit_name": "exact habit name",
    "additional_data": {{}},
    "response_message": "friendly response to user"
}}

Actions:
- add_habit: Create new habit
- complete_habit: Mark habit as done today  
- delete_habit: Remove habit completely
- edit_habit: Modify habit (not implemented yet)
- show_habits: List all habits
- habit_status: Check habit progress

For habit names, use clean, proper case titles. Only return valid JSON.
"""
    
    def _parse_ai_response(self, ai_response: str, original_command: str, user_id: int) -> Dict[str, Any]:
        """Parse OpenAI response and execute the action"""
        try:
            # Extract JSON from AI response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if not json_match:
                return self._process_with_patterns(original_command, user_id)
            
            parsed = json.loads(json_match.group())
            action = parsed.get('action', '')
            habit_name = parsed.get('habit_name', '')
            response_message = parsed.get('response_message', '')
            
            # Execute the action
            if action == 'add_habit' and habit_name:
                return self._add_habit(habit_name, user_id, response_message)
            elif action == 'complete_habit' and habit_name:
                return self._complete_habit(habit_name, user_id, response_message)
            elif action == 'delete_habit' and habit_name:
                return self._delete_habit(habit_name, user_id, response_message)
            elif action == 'show_habits':
                return self._show_habits(user_id, response_message)
            elif action == 'habit_status' and habit_name:
                return self._habit_status(habit_name, user_id, response_message)
            else:
                return self._process_with_patterns(original_command, user_id)
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Failed to parse AI response: {e}")
            return self._process_with_patterns(original_command, user_id)
    
    def _process_with_patterns(self, command: str, user_id: int) -> Dict[str, Any]:
        """Fallback pattern matching processing"""
        
        # Check each action type
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    return self._execute_action(action_type, match, user_id)
        
        # No pattern matched
        return {
            'response': 'I\'m not sure how to help with that. Try saying things like "Add a habit to exercise" or "Mark reading as complete".',
            'action': 'unknown',
            'data': {}
        }
    
    def _execute_action(self, action_type: str, match: re.Match, user_id: int) -> Dict[str, Any]:
        """Execute a specific action based on pattern match"""
        
        if action_type == 'add_habit':
            habit_name = match.group(1).strip().title()
            habit_name = self._clean_habit_name(habit_name)
            return self._add_habit(habit_name, user_id)
            
        elif action_type == 'complete_habit':
            habit_name = match.group(1).strip().title()
            habit_name = self._clean_habit_name(habit_name)
            return self._complete_habit(habit_name, user_id)
            
        elif action_type == 'delete_habit':
            habit_name = match.group(1).strip().title()
            habit_name = self._clean_habit_name(habit_name)
            return self._delete_habit(habit_name, user_id)
            
        elif action_type == 'edit_habit':
            if len(match.groups()) >= 2:
                old_name = match.group(1).strip().title()
                new_name = match.group(2).strip().title()
                return self._edit_habit(old_name, new_name, user_id)
            else:
                habit_name = match.group(1).strip().title()
                return {
                    'response': f'What would you like to change about "{habit_name}"? You can say "rename {habit_name} to [new name]".',
                    'action': 'edit_request',
                    'data': {'habit_name': habit_name}
                }
                
        elif action_type == 'show_habits':
            return self._show_habits(user_id)
            
        elif action_type == 'habit_status':
            habit_name = match.group(1).strip().title()
            habit_name = self._clean_habit_name(habit_name)
            return self._habit_status(habit_name, user_id)
    
    def _clean_habit_name(self, name: str) -> str:
        """Clean and normalize habit name"""
        # Remove common suffixes and normalize
        name = re.sub(r'\s+(daily|every day|everyday|habit)$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^(the|a|an)\s+', '', name, flags=re.IGNORECASE)
        return name.strip().title()
    
    def _add_habit(self, habit_name: str, user_id: int, custom_response: str = None) -> Dict[str, Any]:
        """Add a new habit"""
        if not habit_name or len(habit_name) < 2:
            return {
                'response': 'Please provide a valid habit name.',
                'action': 'error',
                'data': {}
            }
        
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Check if habit already exists
            cursor.execute('SELECT id FROM habits WHERE name = ? AND user_id = ?', (habit_name, user_id))
            if cursor.fetchone():
                conn.close()
                return {
                    'response': f'You already have a habit called "{habit_name}". Try completing it or creating a different one!',
                    'action': 'duplicate',
                    'data': {'habit_name': habit_name}
                }
            
            # Add new habit
            cursor.execute('INSERT INTO habits (name, user_id) VALUES (?, ?)', (habit_name, user_id))
            conn.commit()
            conn.close()
            
            response = custom_response or f'Great! I\'ve added "{habit_name}" to your habits. Start tracking it today!'
            
            return {
                'response': response,
                'action': 'habit_added',
                'data': {'habit_name': habit_name}
            }
            
        except Exception as e:
            print(f"❌ Error adding habit: {e}")
            return {
                'response': 'Sorry, I couldn\'t add that habit right now. Please try again.',
                'action': 'error',
                'data': {}
            }
    
    def _complete_habit(self, habit_name: str, user_id: int, custom_response: str = None) -> Dict[str, Any]:
        """Mark a habit as complete for today"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Find the habit (case-insensitive search)
            cursor.execute('SELECT id, name FROM habits WHERE user_id = ?', (user_id,))
            habits = cursor.fetchall()
            
            habit_id = None
            actual_name = None
            
            # Find matching habit (fuzzy matching)
            for h_id, h_name in habits:
                if habit_name.lower() in h_name.lower() or h_name.lower() in habit_name.lower():
                    habit_id = h_id
                    actual_name = h_name
                    break
            
            if not habit_id:
                conn.close()
                # Suggest creating the habit
                return {
                    'response': f'I don\'t see a habit called "{habit_name}". Would you like me to create it for you?',
                    'action': 'habit_not_found',
                    'data': {'suggested_habit': habit_name}
                }
            
            # Mark habit as complete for today
            today = date.today().isoformat()
            
            # Check if already completed today
            cursor.execute('''
                SELECT completed FROM habit_entries 
                WHERE user_id = ? AND habit_id = ? AND date = ?
            ''', (user_id, habit_id, today))
            
            existing = cursor.fetchone()
            
            if existing and existing[0]:
                conn.close()
                return {
                    'response': f'You already completed "{actual_name}" today! Keep up the great work! 🎉',
                    'action': 'already_completed',
                    'data': {'habit_name': actual_name}
                }
            
            # Insert or update completion
            if existing:
                cursor.execute('''
                    UPDATE habit_entries SET completed = 1 
                    WHERE user_id = ? AND habit_id = ? AND date = ?
                ''', (user_id, habit_id, today))
            else:
                cursor.execute('''
                    INSERT INTO habit_entries (user_id, habit_id, date, completed) 
                    VALUES (?, ?, ?, 1)
                ''', (user_id, habit_id, today))
            
            conn.commit()
            conn.close()
            
            response = custom_response or f'Awesome! I\'ve marked "{actual_name}" as completed for today. You\'re building great habits! 🌟'
            
            return {
                'response': response,
                'action': 'habit_completed',
                'data': {'habit_name': actual_name, 'date': today}
            }
            
        except Exception as e:
            print(f"❌ Error completing habit: {e}")
            return {
                'response': 'Sorry, I couldn\'t mark that habit as complete. Please try again.',
                'action': 'error',
                'data': {}
            }
    
    def _delete_habit(self, habit_name: str, user_id: int, custom_response: str = None) -> Dict[str, Any]:
        """Delete a habit"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Find the habit (case-insensitive search)
            cursor.execute('SELECT id, name FROM habits WHERE user_id = ?', (user_id,))
            habits = cursor.fetchall()
            
            habit_id = None
            actual_name = None
            
            for h_id, h_name in habits:
                if habit_name.lower() in h_name.lower() or h_name.lower() in habit_name.lower():
                    habit_id = h_id
                    actual_name = h_name
                    break
            
            if not habit_id:
                conn.close()
                return {
                    'response': f'I couldn\'t find a habit called "{habit_name}" to delete.',
                    'action': 'habit_not_found',
                    'data': {'habit_name': habit_name}
                }
            
            # Delete habit and all entries
            cursor.execute('DELETE FROM habit_entries WHERE habit_id = ?', (habit_id,))
            cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
            
            conn.commit()
            conn.close()
            
            response = custom_response or f'I\'ve removed "{actual_name}" from your habits tracker.'
            
            return {
                'response': response,
                'action': 'habit_deleted',
                'data': {'habit_name': actual_name}
            }
            
        except Exception as e:
            print(f"❌ Error deleting habit: {e}")
            return {
                'response': 'Sorry, I couldn\'t delete that habit. Please try again.',
                'action': 'error',
                'data': {}
            }
    
    def _edit_habit(self, old_name: str, new_name: str, user_id: int) -> Dict[str, Any]:
        """Rename a habit"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Find the habit
            cursor.execute('SELECT id FROM habits WHERE name LIKE ? AND user_id = ?', (f'%{old_name}%', user_id))
            habit = cursor.fetchone()
            
            if not habit:
                conn.close()
                return {
                    'response': f'I couldn\'t find a habit called "{old_name}" to rename.',
                    'action': 'habit_not_found',
                    'data': {'habit_name': old_name}
                }
            
            # Update habit name
            cursor.execute('UPDATE habits SET name = ? WHERE id = ?', (new_name, habit[0]))
            conn.commit()
            conn.close()
            
            return {
                'response': f'Perfect! I\'ve renamed "{old_name}" to "{new_name}".',
                'action': 'habit_renamed',
                'data': {'old_name': old_name, 'new_name': new_name}
            }
            
        except Exception as e:
            print(f"❌ Error editing habit: {e}")
            return {
                'response': 'Sorry, I couldn\'t rename that habit. Please try again.',
                'action': 'error',
                'data': {}
            }
    
    def _show_habits(self, user_id: int, custom_response: str = None) -> Dict[str, Any]:
        """Show all user habits"""
        try:
            habits = self._get_user_habits(user_id)
            
            if not habits:
                response = custom_response or 'You don\'t have any habits yet. Try saying "Add a habit to drink water" to get started!'
                return {
                    'response': response,
                    'action': 'no_habits',
                    'data': {'habits': []}
                }
            
            habit_list = list(habits.keys())
            
            # Get completion status for today
            today = date.today().isoformat()
            completed_today = []
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            for habit_name in habit_list:
                cursor.execute('''
                    SELECT he.completed FROM habit_entries he
                    JOIN habits h ON he.habit_id = h.id
                    WHERE h.name = ? AND h.user_id = ? AND he.date = ?
                ''', (habit_name, user_id, today))
                
                result = cursor.fetchone()
                if result and result[0]:
                    completed_today.append(habit_name)
            
            conn.close()
            
            if custom_response:
                response = custom_response
            else:
                response = f'Your habits are: {", ".join(habit_list)}. '
                if completed_today:
                    response += f'Today you\'ve completed: {", ".join(completed_today)}. Great job!'
                else:
                    response += 'You haven\'t completed any habits today yet. You can do it!'
            
            return {
                'response': response,
                'action': 'habits_listed',
                'data': {
                    'habits': habit_list,
                    'completed_today': completed_today
                }
            }
            
        except Exception as e:
            print(f"❌ Error showing habits: {e}")
            return {
                'response': 'Sorry, I couldn\'t retrieve your habits right now.',
                'action': 'error',
                'data': {}
            }
    
    def _habit_status(self, habit_name: str, user_id: int, custom_response: str = None) -> Dict[str, Any]:
        """Get status of a specific habit"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Find the habit
            cursor.execute('SELECT id, name FROM habits WHERE user_id = ?', (user_id,))
            habits = cursor.fetchall()
            
            habit_id = None
            actual_name = None
            
            for h_id, h_name in habits:
                if habit_name.lower() in h_name.lower() or h_name.lower() in habit_name.lower():
                    habit_id = h_id
                    actual_name = h_name
                    break
            
            if not habit_id:
                conn.close()
                return {
                    'response': f'I couldn\'t find a habit called "{habit_name}".',
                    'action': 'habit_not_found',
                    'data': {'habit_name': habit_name}
                }
            
            # Get recent completion data
            cursor.execute('''
                SELECT date, completed FROM habit_entries 
                WHERE habit_id = ? AND date >= date('now', '-7 days')
                ORDER BY date DESC
            ''', (habit_id,))
            
            recent_entries = cursor.fetchall()
            conn.close()
            
            completed_days = sum(1 for _, completed in recent_entries if completed)
            total_days = min(7, len(recent_entries))
            
            today = date.today().isoformat()
            completed_today = any(entry[0] == today and entry[1] for entry in recent_entries)
            
            if custom_response:
                response = custom_response
            else:
                status = "completed" if completed_today else "not completed yet"
                response = f'For "{actual_name}": You\'ve completed it {completed_days} out of the last {total_days} days. Today it\'s {status}.'
                
                if completed_today:
                    response += ' Keep up the excellent work! 🎉'
                else:
                    response += ' You can still complete it today!'
            
            return {
                'response': response,
                'action': 'habit_status',
                'data': {
                    'habit_name': actual_name,
                    'completed_days': completed_days,
                    'total_days': total_days,
                    'completed_today': completed_today
                }
            }
            
        except Exception as e:
            print(f"❌ Error getting habit status: {e}")
            return {
                'response': 'Sorry, I couldn\'t check that habit\'s status right now.',
                'action': 'error',
                'data': {}
            }
    
    def _get_user_habits(self, user_id: int) -> Dict[str, Dict]:
        """Get all habits for a user"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name, color FROM habits WHERE user_id = ?', (user_id,))
            rows = cursor.fetchall()
            
            habits = {}
            for habit_id, name, color in rows:
                cursor.execute('SELECT date, completed FROM habit_entries WHERE habit_id = ?', (habit_id,))
                dates = {row[0]: bool(row[1]) for row in cursor.fetchall()}
                habits[name] = {'dates': dates, 'color': color or '#2ecc40'}
            
            conn.close()
            return habits
            
        except Exception as e:
            print(f"❌ Error getting user habits: {e}")
            return {}

# Global processor instance
processor = VoiceCommandProcessor()

def process_voice_command(command: str, user_id: int) -> Dict[str, Any]:
    """
    Main function to process voice commands
    
    Args:
        command: The voice command text
        user_id: The user's ID
        
    Returns:
        Dictionary with response, action, and data
    """
    return processor.process_command(command, user_id)
