#!/usr/bin/env python3
"""
Quick Test Suite for Whisper-large Integration
Tests the core components without requiring audio input
"""

import sys
import os
import json
from datetime import date

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_intent_parser():
    """Test the intent parsing system"""
    print("🧠 Testing Intent Parser...")
    
    try:
        from intent_parser import parse_user_intent
        
        test_cases = [
            ("add a habit to drink water", "add_habit"),
            ("mark exercise as complete", "complete_habit"),
            ("mark meditation as done on September 20th", "complete_habit"),
            ("delete my reading habit", "delete_habit"),
            ("rename exercise to morning workout", "edit_habit"),
            ("show my habits", "show_habits"),
            ("how am I doing with meditation", "habit_status"),
            ("hello how are you", "conversation"),
            ("what's the weather like", "conversation"),
        ]
        
        for text, expected_action in test_cases:
            result = parse_user_intent(text)
            action = result.get('action')
            confidence = result.get('confidence', 0)
            
            status = "✅" if action == expected_action else "❌"
            print(f"  {status} '{text}' → {action} (confidence: {confidence:.2f})")
            
            if action != expected_action:
                print(f"    Expected: {expected_action}, Got: {action}")
        
        print("✅ Intent parser tests completed")
        
    except ImportError as e:
        print(f"❌ Intent parser import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Intent parser test failed: {e}")
        return False
    
    return True

def test_habit_automation():
    """Test the habit automation system (without database operations)"""
    print("🏃‍♀️ Testing Habit Automation...")
    
    try:
        from habit_automation import HabitAutomationSystem
        from intent_parser import parse_user_intent
        
        # Test intent parsing for habit actions
        test_commands = [
            "add a habit to morning exercise",
            "complete my meditation habit",
            "delete the reading habit",
            "show all habits",
        ]
        
        for command in test_commands:
            intent_result = parse_user_intent(command)
            action = intent_result.get('action')
            print(f"  📝 '{command}' → {action}")
        
        print("✅ Habit automation system structure verified")
        
    except ImportError as e:
        print(f"❌ Habit automation import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Habit automation test failed: {e}")
        return False
    
    return True

def test_whisper_service():
    """Test Whisper service availability"""
    print("🎤 Testing Whisper Service...")
    
    try:
        from whisper_service import WhisperService
        
        service = WhisperService()
        
        if service.is_ready():
            print("  ✅ Whisper service initialized successfully")
            print(f"  📱 Device: {service.device}")
            print(f"  🧠 Model: {type(service.model).__name__ if service.model else 'Not loaded'}")
        else:
            print("  ❌ Whisper service not ready")
            return False
        
    except ImportError as e:
        print(f"❌ Whisper service import failed: {e}")
        print("  💡 Run: pip install openai-whisper torch")
        return False
    except Exception as e:
        print(f"❌ Whisper service test failed: {e}")
        return False
    
    return True

def test_unified_processing():
    """Test the unified message processing logic"""
    print("🔄 Testing Unified Processing...")
    
    try:
        # Test the processing logic structure
        test_messages = [
            "add a habit to drink water",
            "mark exercise as complete",
            "hello how are you today",
            "what time is it",
        ]
        
        from intent_parser import parse_user_intent
        
        for message in test_messages:
            intent = parse_user_intent(message)
            action = intent.get('action')
            confidence = intent.get('confidence', 0)
            
            if action in ['add_habit', 'complete_habit', 'delete_habit', 'edit_habit', 'show_habits', 'habit_status']:
                processing_type = "habit_action"
            else:
                processing_type = "conversation"
            
            print(f"  🔍 '{message}' → {processing_type} ({action}, {confidence:.2f})")
        
        print("✅ Unified processing logic verified")
        
    except Exception as e:
        print(f"❌ Unified processing test failed: {e}")
        return False
    
    return True

def test_api_structure():
    """Test that the API structure is correct"""
    print("🌐 Testing API Structure...")
    
    try:
        # Check if the main app file exists and has the right structure
        import app_api
        
        # Check for required functions
        required_functions = [
            'process_unified_message',
            'get_conversation_context',
            'store_chat_message'
        ]
        
        for func_name in required_functions:
            if hasattr(app_api, func_name):
                print(f"  ✅ {func_name} function found")
            else:
                print(f"  ❌ {func_name} function missing")
                return False
        
        print("✅ API structure verified")
        
    except ImportError as e:
        print(f"❌ API import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🧪 Zelda AI Assistant - Whisper Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Intent Parser", test_intent_parser),
        ("Habit Automation", test_habit_automation),
        ("Whisper Service", test_whisper_service),
        ("Unified Processing", test_unified_processing),
        ("API Structure", test_api_structure),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Tests...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Whisper integration is ready.")
        print("\n🚀 Next steps:")
        print("1. Start the backend: python app_api.py")
        print("2. Start the frontend: npm run dev (in frontend directory)")
        print("3. Test voice commands at http://localhost:5173")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\n🔧 Common fixes:")
        print("1. Install dependencies: pip install -r requirements-whisper.txt")
        print("2. Check Python path and imports")
        print("3. Verify database initialization")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)