"""
Comprehensive Voice Command Handler for Zelda AI Assistant

This module processes all possible voice commands and executes the appropriate actions
throughout the entire application.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
from habit_automation import execute_habit_action

logger = logging.getLogger(__name__)

class VoiceCommandHandler:
    """Handles execution of all voice commands across the entire app"""
    
    def __init__(self):
        self.command_handlers = {
            # Habit-related commands
            'add_habit': self._handle_habit_action,
            'complete_habit': self._handle_habit_action,
            'edit_habit': self._handle_habit_action,
            'delete_habit': self._handle_habit_action,
            'show_habits': self._handle_habit_action,
            'habit_status': self._handle_habit_action,
            
            # Navigation commands
            'navigate_home': self._handle_navigation,
            'navigate_habits': self._handle_navigation,
            'navigate_analytics': self._handle_navigation,
            'navigate_chat': self._handle_navigation,
            'navigate_settings': self._handle_navigation,
            
            # Account commands
            'logout': self._handle_logout,
            'view_account': self._handle_view_account,
            
            # App control commands
            'refresh_page': self._handle_refresh_page,
            'clear_data': self._handle_clear_data,
            
            # Information commands
            'show_help': self._handle_show_help,
            'app_info': self._handle_app_info,
            'show_today': self._handle_show_today,
            'show_calendar': self._handle_show_calendar,
        }
    
    def execute_command(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Execute a voice command based on parsed intent
        
        Args:
            intent_result: Result from intent parser
            user_id: User ID for personalized actions
            
        Returns:
            Dictionary with execution results and response message
        """
        action = intent_result.get('action')
        
        logger.info(f"🎙️ Executing voice command: {action} for user {user_id}")
        
        try:
            if action in self.command_handlers:
                return self.command_handlers[action](intent_result, user_id)
            else:
                return {
                    'success': False,
                    'action': action,
                    'message': f"I understand you want to {action.replace('_', ' ')}, but I don't know how to do that yet.",
                    'data': {},
                    'frontend_action': None
                }
        
        except Exception as e:
            logger.error(f"❌ Error executing voice command {action}: {str(e)}")
            return {
                'success': False,
                'action': action,
                'message': "Sorry, I couldn't complete that command. Please try again.",
                'data': {},
                'error': str(e),
                'frontend_action': None
            }
    
    def _handle_habit_action(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle habit-related actions using existing habit automation"""
        from habit_automation import HabitAutomationSystem
        
        habit_system = HabitAutomationSystem()
        result = habit_system.execute_habit_action(intent_result, user_id)
        
        # Add frontend action for habits
        if result.get('success'):
            result['frontend_action'] = {
                'type': 'refresh_habits',
                'navigate': None
            }
        
        return result
    
    def _handle_navigation(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle navigation commands"""
        action = intent_result.get('action')
        target_page = intent_result.get('data', {}).get('target_page', '')
        
        page_mapping = {
            'home': '/',
            'habits': '/habits',
            'analytics': '/analytics',
            'chat': '/chat',
            'settings': '/settings'
        }
        
        route = page_mapping.get(target_page, '/')
        page_name = target_page.replace('_', ' ').title()
        
        return {
            'success': True,
            'action': action,
            'message': f"Taking you to the {page_name} page!",
            'data': {
                'route': route,
                'page': target_page
            },
            'frontend_action': {
                'type': 'navigate',
                'navigate': route
            }
        }
    
    def _handle_logout(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle logout command"""
        return {
            'success': True,
            'action': 'logout',
            'message': "Logging you out now. See you soon!",
            'data': {},
            'frontend_action': {
                'type': 'logout',
                'navigate': '/login'
            }
        }
    
    def _handle_view_account(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle view account command"""
        return {
            'success': True,
            'action': 'view_account',
            'message': "Opening your account settings!",
            'data': {},
            'frontend_action': {
                'type': 'navigate',
                'navigate': '/account'
            }
        }
    
    def _handle_refresh_page(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle page refresh command"""
        return {
            'success': True,
            'action': 'refresh_page',
            'message': "Refreshing the page for you!",
            'data': {},
            'frontend_action': {
                'type': 'refresh',
                'navigate': None
            }
        }
    
    def _handle_clear_data(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle clear data command"""
        return {
            'success': False,  # Require confirmation for destructive actions
            'action': 'clear_data',
            'message': "For safety, please use the settings page to clear data. I can't do that through voice commands.",
            'data': {},
            'frontend_action': {
                'type': 'navigate',
                'navigate': '/settings'
            }
        }
    
    def _handle_show_help(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle show help command"""
        help_message = """Here are the voice commands you can use:

🏠 NAVIGATION:
• "Go to home" / "Take me home"
• "Open habits" / "Show my habits"
• "Go to analytics" / "Show stats"
• "Open chat" / "Start conversation"
• "Go to settings"

🎯 HABITS:
• "Add a habit to [habit name]"
• "Mark [habit] as complete"
• "Delete [habit] habit"
• "Show my habits"
• "How am I doing with [habit]?"

⚙️ APP CONTROLS:
• "Refresh page"
• "Log out"
• "Show account"
• "Help" / "What can I do?"

📅 INFORMATION:
• "What's today's schedule?"
• "Show calendar"
• "About this app"

Just speak naturally - I'll understand what you want to do!"""
        
        return {
            'success': True,
            'action': 'show_help',
            'message': help_message,
            'data': {'help_shown': True},
            'frontend_action': None
        }
    
    def _handle_app_info(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle app info command"""
        info_message = """🤖 About Zelda AI Assistant

Zelda is your intelligent habit tracking and productivity assistant. I can help you:

✅ Track and build positive habits
📊 Analyze your progress with detailed analytics  
💬 Have natural conversations about your goals
🎤 Control everything with voice commands
📱 Access all features across devices

I'm powered by advanced AI and designed to help you become your best self through consistent habit building!

Version: 2.0 with Enhanced Voice Commands"""
        
        return {
            'success': True,
            'action': 'app_info',
            'message': info_message,
            'data': {'info_shown': True},
            'frontend_action': None
        }
    
    def _handle_show_today(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle show today command"""
        # This would typically fetch today's habits and show progress
        return {
            'success': True,
            'action': 'show_today',
            'message': "Here's your schedule for today! Opening your habits page to show today's progress.",
            'data': {'date': date.today().isoformat()},
            'frontend_action': {
                'type': 'navigate',
                'navigate': '/habits'
            }
        }
    
    def _handle_show_calendar(self, intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle show calendar command"""
        return {
            'success': True,
            'action': 'show_calendar',
            'message': "Opening your habit calendar!",
            'data': {},
            'frontend_action': {
                'type': 'navigate',
                'navigate': '/habits'
            }
        }

# Global instance
_voice_command_handler = None

def get_voice_command_handler() -> VoiceCommandHandler:
    """Get the global voice command handler instance"""
    global _voice_command_handler
    if _voice_command_handler is None:
        _voice_command_handler = VoiceCommandHandler()
    return _voice_command_handler

def execute_voice_command(intent_result: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Convenience function for executing voice commands"""
    handler = get_voice_command_handler()
    return handler.execute_command(intent_result, user_id)