"""
Intent Parser for Zelda AI Assistant

This module analyzes user text to detect habit-related actions and route them
appropriately for database operations vs normal conversation.
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

class IntentParser:
    """Intelligent intent parser for detecting habit actions in user text"""
    
    def __init__(self):
        # Comprehensive voice command patterns for all app actions
        self.habit_action_patterns = {
            'add_habit': [
                # Habit creation patterns
                r'(?:add|create|start|begin|make).*?(?:habit|routine).*?(?:called|named|for|to)\s+([a-zA-Z0-9\s]+?)(?:\s*$|daily|every|regularly|\.)',
                r'(?:add|create|start|begin|make).*?(?:habit|routine).*?to\s+([a-zA-Z0-9\s]+?)(?:\s*$|daily|every|regularly|\.)',
                r'(?:add|create|start).*?(?:a|the)?\s*habit.*?(?:of|for|to)\s+([a-zA-Z0-9\s]+?)(?:\s*$|daily|every|regularly|\.)',
                r'(?:track|build|start).*?habit.*?(?:called|named|for|to)\s+([a-zA-Z0-9\s]+?)(?:\s*$|daily|every|regularly|\.)',
                r'(?:i want to|need to|should).*?(?:start|begin|track).*?([a-zA-Z0-9\s]+?)(?:\s+(?:daily|every day|regularly|as a habit))',
                r'(?:help me|remind me).*?(?:to\s+)?(?:track|build|start).*?([a-zA-Z0-9\s]+?)(?:\s+(?:daily|every day|regularly|habit))',
                r'(?:new|a)\s+habit.*?(?:called|named|for|to)\s+([a-zA-Z0-9\s]+?)(?:\s*$|daily|every|regularly|\.)',
                r'track\s+([a-zA-Z0-9\s]+?)(?:\s+(?:daily|every day|regularly|as a habit))',
                r'let.*?(?:start|begin).*?([a-zA-Z0-9\s]+?)(?:\s+(?:habit|routine|daily))'
            ],
            'complete_habit': [
                r'(?:mark|complete|did|finished|done|check off|completed).*?([^.,!?]+)(?:today|for today|now|as done)?',
                r'(?:i|just).*?(?:did|finished|completed).*?([^.,!?]+)(?:today|now)?',
                r'(?:completed|done with|finished).*?([^.,!?]+)',
                r'([^.,!?]+).*?(?:is|was).*?(?:done|completed|finished)(?:today|now)?',
                r'(?:mark).*?([^.,!?]+).*?(?:as).*?(?:complete|done|finished)'
            ],
            'complete_habit_date': [
                r'(?:mark|complete).*?([^.,!?]+).*?(?:as done|as complete).*?(?:on|for)\s*([^.,!?]+)',
                r'(?:did|completed|finished).*?([^.,!?]+).*?(?:on|yesterday|last)\s*([^.,!?]*)',
                r'(?:mark).*?([^.,!?]+).*?(?:done|complete).*?(?:on)\s*([^.,!?]+)'
            ],
            'edit_habit': [
                r'(?:rename|change).*?(?:habit|routine)?.*?([^.,!?]+).*?(?:to).*?([^.,!?]+)',
                r'(?:edit|modify|update).*?(?:habit|routine)?.*?([^.,!?]+)',
                r'(?:change).*?([^.,!?]+).*?(?:habit|routine).*?(?:to).*?([^.,!?]+)'
            ],
            'delete_habit': [
                r'(?:remove|delete|stop|quit|cancel).*?(?:habit|routine).*?(?:called|named)?["\s]*([^".,!?]+)["\s]*',
                r'(?:remove|delete|stop|quit|cancel).*?(?:the)?["\s]*([^".,!?]+)["\s]*(?:habit|routine)?',
                r'(?:don\'t want to|no longer want to|stop).*?(?:track|do).*?([^.,!?]+)(?:anymore|any more)?',
                r'(?:get rid of|eliminate).*?(?:habit|routine)?.*?(?:called|named)?["\s]*([^".,!?]+)["\s]*'
            ],
            'show_habits': [
                r'(?:show|list|display).*?(?:my|all)?.*?(?:habits|routines)',
                r'(?:what are|what\'s).*?(?:my)?.*?(?:habits|routines)',
                r'(?:view|see).*?(?:my)?.*?(?:habits|routines)',
                r'(?:how many|what).*?(?:habits|routines).*?(?:do i have|i have)'
            ],
            'habit_status': [
                r'(?:how am i doing|progress|status).*?(?:with|on).*?([^.,!?]+)',
                r'(?:show|tell me).*?(?:progress|status).*?(?:for|on|with).*?([^.,!?]+)',
                r'(?:what\'s my|whats my).*?(?:progress|streak).*?(?:for|on|with).*?([^.,!?]+)',
                r'(?:check).*?([^.,!?]+).*?(?:progress|status|streak)'
            ],
            
            # Navigation commands
            'navigate_home': [
                r'(?:go to|open|show|navigate to).*?(?:home|dashboard|main)(?:\s+page)?',
                r'(?:take me to|bring me to).*?(?:home|main|dashboard)',
                r'(?:home|main page|dashboard)',
                r'(?:go back to|return to).*?(?:home|main)'
            ],
            'navigate_habits': [
                r'(?:go to|open|show|navigate to).*?(?:habits|habit tracker|tracking)(?:\s+page)?',
                r'(?:take me to|bring me to).*?(?:habits|habit tracker)',
                r'(?:habits page|habit tracker|tracking page)',
                r'(?:show|open).*?(?:my)?.*?habits'
            ],
            'navigate_analytics': [
                r'(?:go to|open|show|navigate to).*?(?:analytics|stats|statistics|reports?)(?:\s+page)?',
                r'(?:take me to|bring me to).*?(?:analytics|stats|reports)',
                r'(?:analytics page|statistics|reports page)',
                r'(?:show|open).*?(?:my)?.*?(?:analytics|stats|progress|reports)'
            ],
            'navigate_chat': [
                r'(?:go to|open|show|navigate to).*?(?:chat|conversation|talk)(?:\s+page)?',
                r'(?:take me to|bring me to).*?(?:chat|conversation)',
                r'(?:chat page|conversation|talk)',
                r'(?:open|start).*?(?:chat|conversation)'
            ],
            'navigate_settings': [
                r'(?:go to|open|show|navigate to).*?(?:settings|preferences|config)(?:\s+page)?',
                r'(?:take me to|bring me to).*?(?:settings|preferences)',
                r'(?:settings page|preferences|configuration)',
                r'(?:open|show).*?(?:settings|preferences|config)'
            ],
            
            # Account and authentication commands
            'logout': [
                r'(?:log out|logout|sign out|signout)',
                r'(?:exit|quit).*?(?:account|app|application)',
                r'(?:disconnect|end session)'
            ],
            'view_account': [
                r'(?:show|view|open).*?(?:account|profile)(?:\s+info)?',
                r'(?:go to|navigate to).*?(?:account|profile)',
                r'(?:my account|my profile|account info|profile info)'
            ],
            
            # App control commands
            'refresh_page': [
                r'(?:refresh|reload).*?(?:page|data|screen)',
                r'(?:update|sync).*?(?:data|info|information)',
                r'(?:refresh everything|reload all)'
            ],
            'clear_data': [
                r'(?:clear|reset|delete).*?(?:all data|everything)',
                r'(?:clean|wipe).*?(?:data|storage)',
                r'(?:start over|reset everything)'
            ],
            
            # Help and information commands
            'show_help': [
                r'(?:help|assistance|guide|tutorial)',
                r'(?:how do i|how to|what can i).*?(?:do|use|say)',
                r'(?:show|tell me).*?(?:commands|options|features)',
                r'(?:what commands|voice commands|available commands)'
            ],
            'app_info': [
                r'(?:about|version|info).*?(?:app|application|zelda)',
                r'(?:what is|tell me about).*?(?:this app|zelda)',
                r'(?:app information|application info)'
            ],
            
            # Date and time related commands
            'show_today': [
                r'(?:show|what\'s).*?(?:today|today\'s).*?(?:habits|schedule|tasks)',
                r'(?:today\'s|todays).*?(?:agenda|plan|habits)',
                r'(?:what do i need to do|what\'s on).*?(?:today|my schedule)'
            ],
            'show_calendar': [
                r'(?:show|open|view).*?(?:calendar|schedule|dates)',
                r'(?:go to|navigate to).*?calendar',
                r'(?:calendar view|monthly view|date picker)'
            ]
        }
        
        # Keywords that strongly suggest habit-related intent
        self.habit_keywords = [
            'habit', 'routine', 'daily', 'track', 'streak', 'complete', 'mark',
            'meditation', 'exercise', 'workout', 'reading', 'water', 'study',
            'journal', 'walk', 'run', 'yoga', 'sleep', 'wake up'
        ]
        
        # Common conversational patterns that are NOT habit actions
        self.conversation_patterns = [
            r'^(?:hi|hello|hey|good morning|good evening)',
            r'^(?:how are you|what\'s up|how\'s it going)',
            r'^(?:thanks?|thank you|appreciate)',
            r'^(?:yes|no|ok|okay|sure|alright)',
            r'\?.*$',  # Questions
            r'^(?:tell me|explain|what is|what are)',
            r'^(?:why|when|where|who|how)',
            r'weather|time|date|news|joke|story'
        ]
    
    def parse_intent(self, text: str) -> Dict[str, Any]:
        """
        Parse user text to determine intent and extract relevant information
        
        Args:
            text: User input text
            
        Returns:
            Dictionary with intent information
        """
        text = text.strip()
        text_lower = text.lower()
        
        if not text:
            return self._create_result('unknown', {}, 0.0)
        
        logger.info(f"🧠 Parsing intent for: '{text}'")
        
        # Check if it's clearly conversational first
        if self._is_conversational(text_lower):
            logger.info("💬 Detected conversational intent")
            return self._create_result('conversation', {'text': text}, 0.9)
        
        # Check for habit actions
        habit_result = self._check_habit_actions(text, text_lower)
        if habit_result['confidence'] > 0.5:
            logger.info(f"🎯 Detected habit action: {habit_result['action']}")
            return habit_result
        
        # If contains habit keywords but no clear action, it might be habit-related conversation
        if self._contains_habit_keywords(text_lower):
            logger.info("🤔 Contains habit keywords but unclear action")
            return self._create_result('habit_conversation', {'text': text}, 0.6)
        
        # Default to conversation
        logger.info("💬 Defaulting to conversational intent")
        return self._create_result('conversation', {'text': text}, 0.7)
    
    def _check_habit_actions(self, text: str, text_lower: str) -> Dict[str, Any]:
        """Check for specific habit actions"""
        
        for action, patterns in self.habit_action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    result = self._extract_habit_details(action, match, text)
                    if result:
                        return result
        
        return self._create_result('unknown', {}, 0.0)
    
    def _extract_habit_details(self, action: str, match, original_text: str) -> Optional[Dict[str, Any]]:
        """Extract details from regex match for habit actions"""
        
        try:
            if action == 'add_habit':
                habit_name = self._clean_habit_name(match.group(1))
                if habit_name and len(habit_name) > 1:
                    return self._create_result('add_habit', {
                        'habit_name': habit_name,
                        'original_text': original_text
                    }, 0.85)
            
            elif action == 'complete_habit':
                habit_name = self._clean_habit_name(match.group(1))
                if habit_name and len(habit_name) > 1:
                    return self._create_result('complete_habit', {
                        'habit_name': habit_name,
                        'date': None,  # Today
                        'original_text': original_text
                    }, 0.85)
            
            elif action == 'complete_habit_date':
                habit_name = self._clean_habit_name(match.group(1))
                date_str = match.group(2).strip() if len(match.groups()) > 1 else None
                parsed_date = self._parse_date(date_str) if date_str else None
                
                if habit_name and len(habit_name) > 1:
                    return self._create_result('complete_habit', {
                        'habit_name': habit_name,
                        'date': parsed_date,
                        'original_text': original_text
                    }, 0.8)
            
            elif action == 'edit_habit':
                if len(match.groups()) >= 2:
                    old_name = self._clean_habit_name(match.group(1))
                    new_name = self._clean_habit_name(match.group(2))
                    if old_name and new_name:
                        return self._create_result('edit_habit', {
                            'old_name': old_name,
                            'new_name': new_name,
                            'original_text': original_text
                        }, 0.8)
                else:
                    habit_name = self._clean_habit_name(match.group(1))
                    if habit_name:
                        return self._create_result('edit_habit', {
                            'habit_name': habit_name,
                            'original_text': original_text
                        }, 0.7)
            
            elif action == 'delete_habit':
                habit_name = self._clean_habit_name(match.group(1))
                if habit_name and len(habit_name) > 1:
                    return self._create_result('delete_habit', {
                        'habit_name': habit_name,
                        'original_text': original_text
                    }, 0.85)
            
            elif action == 'show_habits':
                return self._create_result('show_habits', {
                    'original_text': original_text
                }, 0.9)
            
            elif action == 'habit_status':
                habit_name = self._clean_habit_name(match.group(1))
                if habit_name and len(habit_name) > 1:
                    return self._create_result('habit_status', {
                        'habit_name': habit_name,
                        'original_text': original_text
                    }, 0.8)
            
            # Navigation commands
            elif action in ['navigate_home', 'navigate_habits', 'navigate_analytics', 'navigate_chat', 'navigate_settings']:
                return self._create_result(action, {
                    'target_page': action.replace('navigate_', ''),
                    'original_text': original_text
                }, 0.9)
            
            # Account commands
            elif action in ['logout', 'view_account']:
                return self._create_result(action, {
                    'original_text': original_text
                }, 0.9)
            
            # App control commands
            elif action in ['refresh_page', 'clear_data']:
                return self._create_result(action, {
                    'original_text': original_text
                }, 0.85)
            
            # Information commands
            elif action in ['show_help', 'app_info', 'show_today', 'show_calendar']:
                return self._create_result(action, {
                    'original_text': original_text
                }, 0.9)
        
        except (IndexError, AttributeError) as e:
            logger.warning(f"⚠️ Error extracting habit details: {e}")
        
        return None
    
    def _clean_habit_name(self, name: str) -> str:
        """Clean and normalize habit name"""
        if not name:
            return ""
        
        # First, clean up the raw text
        cleaned = name.strip()
        
        # Remove quotes and extra punctuation
        cleaned = re.sub(r'["\'\`]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common noise words and phrases at the beginning
        noise_patterns = [
            r'^(?:add|create|start|begin|make|track|build)\s+',
            r'^(?:a|an|the)\s+',
            r'^(?:habit|routine)\s+',
            r'^(?:called|named|for|to)\s+',
            r'^(?:my|this|that)\s+',
            r'\s+(?:habit|routine|daily|every day)$'
        ]
        
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove individual noise words if they remain
        noise_words = ['the', 'a', 'an', 'my', 'this', 'that', 'for', 'to', 'of', 'with', 'called', 'named']
        words = cleaned.split()
        cleaned_words = [w for w in words if w.lower() not in noise_words]
        
        # Join back and final cleanup
        cleaned = ' '.join(cleaned_words).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.title() if cleaned else ""
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse natural language date to ISO format"""
        if not date_str:
            return None
        
        date_str = date_str.lower().strip()
        today = date.today()
        
        # Handle common date expressions
        if 'yesterday' in date_str:
            target_date = today - timedelta(days=1)
        elif 'today' in date_str:
            target_date = today
        elif 'tomorrow' in date_str:
            target_date = today + timedelta(days=1)
        elif 'last week' in date_str:
            target_date = today - timedelta(weeks=1)
        elif 'next week' in date_str:
            target_date = today + timedelta(weeks=1)
        else:
            # Try to parse specific dates (basic patterns)
            date_patterns = [
                r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # MM/DD/YYYY or MM-DD-YYYY
                r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
                r'september (\d{1,2})',  # "september 20"
                r'(\d{1,2}) september',  # "20 september"
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    try:
                        if 'september' in pattern:
                            day = int(match.group(1))
                            target_date = date(today.year, 9, day)  # September = month 9
                        else:
                            # More complex date parsing could be added here
                            return None
                        break
                    except ValueError:
                        continue
            else:
                return None
        
        return target_date.isoformat()
    
    def _is_conversational(self, text_lower: str) -> bool:
        """Check if text is clearly conversational"""
        for pattern in self.conversation_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def _contains_habit_keywords(self, text_lower: str) -> bool:
        """Check if text contains habit-related keywords"""
        return any(keyword in text_lower for keyword in self.habit_keywords)
    
    def _create_result(self, action: str, data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Create standardized result dictionary"""
        return {
            'action': action,
            'data': data,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }

# Global parser instance
_intent_parser = None

def get_intent_parser() -> IntentParser:
    """Get the global intent parser instance"""
    global _intent_parser
    if _intent_parser is None:
        _intent_parser = IntentParser()
    return _intent_parser

def parse_user_intent(text: str) -> Dict[str, Any]:
    """Convenience function for parsing user intent"""
    parser = get_intent_parser()
    return parser.parse_intent(text)

def is_habit_action(text: str) -> bool:
    """Quick check if text contains a habit action"""
    result = parse_user_intent(text)
    return result['action'] != 'conversation' and result['confidence'] > 0.6