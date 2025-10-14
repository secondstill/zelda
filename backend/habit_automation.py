"""
Habit Automation System for Zelda AI Assistant

This module handles automated habit operations based on parsed intents,
including database updates and generating appropriate responses.
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import json

logger = logging.getLogger(__name__)

class HabitAutomationSystem:
    """Handles automated habit operations and database updates"""
    
    def __init__(self, db_file: str = 'habits.db'):
        self.db_file = db_file
    
    def execute_habit_action(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Execute a habit action based on parsed intent
        
        Args:
            intent_result: Result from intent parser
            user_id: User ID for database operations
            
        Returns:
            Dictionary with execution results and response message
        """
        action = intent_result.get('action')
        data = intent_result.get('data', {})
        
        logger.info(f"🎯 Executing habit action: {action} for user {user_id}")
        
        try:
            if action == 'add_habit':
                return self._add_habit(data, user_id)
            elif action == 'complete_habit':
                return self._complete_habit(data, user_id)
            elif action == 'edit_habit':
                return self._edit_habit(data, user_id)
            elif action == 'delete_habit':
                return self._delete_habit(data, user_id)
            elif action == 'show_habits':
                return self._show_habits(user_id)
            elif action == 'habit_status':
                return self._get_habit_status(data, user_id)
            else:
                return {
                    'success': False,
                    'action': 'unknown',
                    'message': "I'm not sure what habit action you want to perform.",
                    'data': {}
                }
        
        except Exception as e:
            logger.error(f"❌ Error executing habit action {action}: {str(e)}")
            return {
                'success': False,
                'action': action,
                'message': f"Sorry, I couldn't complete that habit action. Please try again.",
                'data': {},
                'error': str(e)
            }
    
    def _add_habit(self, data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Add a new habit for the user"""
        habit_name = data.get('habit_name', '').strip()
        
        if not habit_name or len(habit_name) < 2:
            return {
                'success': False,
                'action': 'add_habit',
                'message': "Please provide a valid habit name.",
                'data': {}
            }
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Check if habit already exists
            cursor.execute('SELECT id FROM habits WHERE name = ? AND user_id = ?', (habit_name, user_id))
            existing_habit = cursor.fetchone()
            
            if existing_habit:
                conn.close()
                return {
                    'success': False,
                    'action': 'add_habit',
                    'message': f"You already have a habit called '{habit_name}'. Try completing it or creating a different one!",
                    'data': {'habit_name': habit_name, 'already_exists': True}
                }
            
            # Add new habit with default color
            cursor.execute('''
                INSERT INTO habits (name, user_id, color, created_at) 
                VALUES (?, ?, ?, ?)
            ''', (habit_name, user_id, '#2ecc40', datetime.now().isoformat()))
            
            habit_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Added habit '{habit_name}' for user {user_id}")
            
            return {
                'success': True,
                'action': 'add_habit',
                'message': f"Perfect! I've added '{habit_name}' to your habits tracker. 🌟 You can start tracking it today!",
                'data': {
                    'habit_name': habit_name,
                    'habit_id': habit_id,
                    'created': True
                }
            }
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database error adding habit: {str(e)}")
            return {
                'success': False,
                'action': 'add_habit',
                'message': "Sorry, I couldn't add that habit right now. Please try again.",
                'data': {},
                'error': str(e)
            }
    
    def _complete_habit(self, data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Mark a habit as complete for a specific date"""
        habit_name = data.get('habit_name', '').strip()
        target_date = data.get('date')  # None means today
        
        if not habit_name:
            return {
                'success': False,
                'action': 'complete_habit',
                'message': "Please specify which habit you want to mark as complete.",
                'data': {}
            }
        
        # Use today's date if none specified
        if not target_date:
            target_date = date.today().isoformat()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Find the habit (with fuzzy matching)
            habit_id, actual_name = self._find_habit_by_name(cursor, habit_name, user_id)
            
            if not habit_id:
                conn.close()
                return {
                    'success': False,
                    'action': 'complete_habit',
                    'message': f"I couldn't find a habit called '{habit_name}'. Would you like me to create it for you?",
                    'data': {'habit_name': habit_name, 'not_found': True}
                }
            
            # Check if already completed for this date
            cursor.execute('''
                SELECT completed FROM habit_entries 
                WHERE user_id = ? AND habit_id = ? AND date = ?
            ''', (user_id, habit_id, target_date))
            
            existing = cursor.fetchone()
            
            if existing and existing[0]:
                conn.close()
                date_str = "today" if target_date == date.today().isoformat() else target_date
                return {
                    'success': False,
                    'action': 'complete_habit',
                    'message': f"You already completed '{actual_name}' {date_str}! Great job maintaining your streak! 🎉",
                    'data': {
                        'habit_name': actual_name,
                        'date': target_date,
                        'already_completed': True
                    }
                }
            
            # Mark as complete
            if existing:
                cursor.execute('''
                    UPDATE habit_entries SET completed = 1 
                    WHERE user_id = ? AND habit_id = ? AND date = ?
                ''', (user_id, habit_id, target_date))
            else:
                cursor.execute('''
                    INSERT INTO habit_entries (user_id, habit_id, date, completed) 
                    VALUES (?, ?, ?, 1)
                ''', (user_id, habit_id, target_date))
            
            conn.commit()
            conn.close()
            
            date_str = "today" if target_date == date.today().isoformat() else f"on {target_date}"
            logger.info(f"✅ Marked habit '{actual_name}' complete for {target_date}, user {user_id}")
            
            return {
                'success': True,
                'action': 'complete_habit',
                'message': f"Awesome! 🎉 I've marked '{actual_name}' as completed {date_str}. You're building great habits!",
                'data': {
                    'habit_name': actual_name,
                    'date': target_date,
                    'completed': True
                }
            }
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database error completing habit: {str(e)}")
            return {
                'success': False,
                'action': 'complete_habit',
                'message': "Sorry, I couldn't mark that habit as complete. Please try again.",
                'data': {},
                'error': str(e)
            }
    
    def _edit_habit(self, data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Edit/rename a habit"""
        old_name = data.get('old_name', '').strip()
        new_name = data.get('new_name', '').strip()
        habit_name = data.get('habit_name', '').strip()  # For simple edit requests
        
        if new_name:  # Rename operation
            return self._rename_habit(old_name, new_name, user_id)
        elif habit_name:  # Simple edit request
            return {
                'success': True,
                'action': 'edit_habit',
                'message': f"What would you like to change about '{habit_name}'? You can say 'rename {habit_name} to [new name]'.",
                'data': {'habit_name': habit_name, 'edit_request': True}
            }
        else:
            return {
                'success': False,
                'action': 'edit_habit',
                'message': "Please specify which habit you want to edit and what changes to make.",
                'data': {}
            }
    
    def _rename_habit(self, old_name: str, new_name: str, user_id: int) -> Dict[str, Any]:
        """Rename a habit"""
        if not old_name or not new_name:
            return {
                'success': False,
                'action': 'edit_habit',
                'message': "Please provide both the current name and new name for the habit.",
                'data': {}
            }
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Find the habit
            habit_id, actual_name = self._find_habit_by_name(cursor, old_name, user_id)
            
            if not habit_id:
                conn.close()
                return {
                    'success': False,
                    'action': 'edit_habit',
                    'message': f"I couldn't find a habit called '{old_name}' to rename.",
                    'data': {'old_name': old_name, 'not_found': True}
                }
            
            # Check if new name already exists
            cursor.execute('SELECT id FROM habits WHERE name = ? AND user_id = ? AND id != ?', 
                          (new_name, user_id, habit_id))
            
            if cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'action': 'edit_habit',
                    'message': f"You already have a habit called '{new_name}'. Please choose a different name.",
                    'data': {'new_name': new_name, 'name_exists': True}
                }
            
            # Update habit name
            cursor.execute('UPDATE habits SET name = ? WHERE id = ?', (new_name, habit_id))
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Renamed habit '{actual_name}' to '{new_name}' for user {user_id}")
            
            return {
                'success': True,
                'action': 'edit_habit',
                'message': f"Perfect! I've renamed '{actual_name}' to '{new_name}'. 📝",
                'data': {
                    'old_name': actual_name,
                    'new_name': new_name,
                    'renamed': True
                }
            }
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database error renaming habit: {str(e)}")
            return {
                'success': False,
                'action': 'edit_habit',
                'message': "Sorry, I couldn't rename that habit. Please try again.",
                'data': {},
                'error': str(e)
            }
    
    def _delete_habit(self, data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Delete a habit and all its entries"""
        habit_name = data.get('habit_name', '').strip()
        
        if not habit_name:
            return {
                'success': False,
                'action': 'delete_habit',
                'message': "Please specify which habit you want to delete.",
                'data': {}
            }
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Find the habit
            habit_id, actual_name = self._find_habit_by_name(cursor, habit_name, user_id)
            
            if not habit_id:
                conn.close()
                return {
                    'success': False,
                    'action': 'delete_habit',
                    'message': f"I couldn't find a habit called '{habit_name}' to delete.",
                    'data': {'habit_name': habit_name, 'not_found': True}
                }
            
            # Delete habit entries first (foreign key constraint)
            cursor.execute('DELETE FROM habit_entries WHERE habit_id = ?', (habit_id,))
            
            # Delete the habit
            cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Deleted habit '{actual_name}' for user {user_id}")
            
            return {
                'success': True,
                'action': 'delete_habit',
                'message': f"I've successfully removed '{actual_name}' from your habits tracker. ✨",
                'data': {
                    'habit_name': actual_name,
                    'deleted': True
                }
            }
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database error deleting habit: {str(e)}")
            return {
                'success': False,
                'action': 'delete_habit',
                'message': "Sorry, I couldn't delete that habit. Please try again.",
                'data': {},
                'error': str(e)
            }
    
    def _show_habits(self, user_id: int) -> Dict[str, Any]:
        """Show all user habits with current status"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get all habits for user
            cursor.execute('SELECT id, name, color FROM habits WHERE user_id = ? ORDER BY name', (user_id,))
            habits = cursor.fetchall()
            
            if not habits:
                conn.close()
                return {
                    'success': True,
                    'action': 'show_habits',
                    'message': "You don't have any habits yet. Try saying 'Add a habit to drink water' to get started! 💧",
                    'data': {'habits': [], 'empty': True}
                }
            
            # Get today's completion status
            today = date.today().isoformat()
            habit_list = []
            completed_today = []
            
            for habit_id, name, color in habits:
                cursor.execute('''
                    SELECT completed FROM habit_entries 
                    WHERE habit_id = ? AND date = ?
                ''', (habit_id, today))
                
                result = cursor.fetchone()
                is_completed = result and result[0]
                
                habit_list.append({
                    'id': habit_id,
                    'name': name,
                    'color': color,
                    'completed_today': is_completed
                })
                
                if is_completed:
                    completed_today.append(name)
            
            conn.close()
            
            # Build response message
            habit_names = [h['name'] for h in habit_list]
            message = f"Your habits are: {', '.join(habit_names)}. "
            
            if completed_today:
                message += f"Today you've completed: {', '.join(completed_today)}. Great job! 🎉"
            else:
                message += "You haven't completed any habits today yet. You can do it! 💪"
            
            return {
                'success': True,
                'action': 'show_habits',
                'message': message,
                'data': {
                    'habits': habit_list,
                    'completed_today': completed_today,
                    'total_count': len(habit_list)
                }
            }
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database error showing habits: {str(e)}")
            return {
                'success': False,
                'action': 'show_habits',
                'message': "Sorry, I couldn't retrieve your habits right now.",
                'data': {},
                'error': str(e)
            }
    
    def _get_habit_status(self, data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Get status and progress for a specific habit"""
        habit_name = data.get('habit_name', '').strip()
        
        if not habit_name:
            return {
                'success': False,
                'action': 'habit_status',
                'message': "Please specify which habit you want to check.",
                'data': {}
            }
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Find the habit
            habit_id, actual_name = self._find_habit_by_name(cursor, habit_name, user_id)
            
            if not habit_id:
                conn.close()
                return {
                    'success': False,
                    'action': 'habit_status',
                    'message': f"I couldn't find a habit called '{habit_name}'.",
                    'data': {'habit_name': habit_name, 'not_found': True}
                }
            
            # Get recent entries (last 30 days)
            cursor.execute('''
                SELECT date, completed FROM habit_entries 
                WHERE habit_id = ? AND date >= date('now', '-30 days')
                ORDER BY date DESC
            ''', (habit_id,))
            
            entries = cursor.fetchall()
            conn.close()
            
            # Calculate statistics
            total_days = len(entries)
            completed_days = sum(1 for _, completed in entries if completed)
            completion_rate = (completed_days / total_days * 100) if total_days > 0 else 0
            
            # Check today's status
            today = date.today().isoformat()
            completed_today = any(entry[0] == today and entry[1] for entry in entries)
            
            # Calculate current streak
            current_streak = self._calculate_current_streak(entries)
            
            status_msg = "completed" if completed_today else "not completed yet"
            message = f"For '{actual_name}': You've completed it {completed_days} out of the last {total_days} days ({completion_rate:.1f}%). "
            message += f"Current streak: {current_streak} days. Today it's {status_msg}."
            
            if completed_today:
                message += " Keep up the excellent work! 🌟"
            elif current_streak > 0:
                message += " You can still complete it today to keep your streak going! 💪"
            else:
                message += " Start building your streak today! 🚀"
            
            return {
                'success': True,
                'action': 'habit_status',
                'message': message,
                'data': {
                    'habit_name': actual_name,
                    'completed_days': completed_days,
                    'total_days': total_days,
                    'completion_rate': completion_rate,
                    'current_streak': current_streak,
                    'completed_today': completed_today
                }
            }
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database error getting habit status: {str(e)}")
            return {
                'success': False,
                'action': 'habit_status',
                'message': "Sorry, I couldn't check that habit's status right now.",
                'data': {},
                'error': str(e)
            }
    
    def _find_habit_by_name(self, cursor, habit_name: str, user_id: int) -> Tuple[Optional[int], Optional[str]]:
        """Find habit by name using fuzzy matching"""
        # First try exact match
        cursor.execute('SELECT id, name FROM habits WHERE name = ? AND user_id = ?', 
                      (habit_name, user_id))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        
        # Try case-insensitive match
        cursor.execute('SELECT id, name FROM habits WHERE LOWER(name) = LOWER(?) AND user_id = ?', 
                      (habit_name, user_id))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        
        # Try partial matching
        cursor.execute('SELECT id, name FROM habits WHERE user_id = ?', (user_id,))
        all_habits = cursor.fetchall()
        
        habit_name_lower = habit_name.lower()
        
        # Check if habit_name is contained in any existing habit
        for habit_id, name in all_habits:
            if habit_name_lower in name.lower() or name.lower() in habit_name_lower:
                return habit_id, name
        
        # Check word overlap
        habit_words = set(habit_name_lower.split())
        best_match = None
        best_score = 0
        
        for habit_id, name in all_habits:
            name_words = set(name.lower().split())
            overlap = len(habit_words.intersection(name_words))
            if overlap > best_score:
                best_score = overlap
                best_match = (habit_id, name)
        
        if best_match and best_score > 0:
            return best_match
        
        return None, None
    
    def _calculate_current_streak(self, entries: List[Tuple[str, int]]) -> int:
        """Calculate current streak from habit entries"""
        if not entries:
            return 0
        
        # Sort by date descending
        sorted_entries = sorted(entries, key=lambda x: x[0], reverse=True)
        
        streak = 0
        for entry_date, completed in sorted_entries:
            if completed:
                streak += 1
            else:
                break
        
        return streak

# Global automation system instance
_automation_system = None

def get_automation_system(db_file: str = 'habits.db') -> HabitAutomationSystem:
    """Get the global habit automation system instance"""
    global _automation_system
    if _automation_system is None:
        _automation_system = HabitAutomationSystem(db_file)
    return _automation_system

def execute_habit_action(intent_result: Dict[str, Any], user_id: int, db_file: str = 'habits.db') -> Dict[str, Any]:
    """Convenience function for executing habit actions"""
    system = get_automation_system(db_file)
    return system.execute_habit_action(intent_result, user_id)