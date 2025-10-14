import requests
import random


def get_ai_reply_with_context(user_message, conversation_context=""):
    """Get AI reply with conversation context for continuity"""
    base_prompt = (
        "You are Zelda, an intelligent and empathetic AI personal assistant. Keep your responses concise (2-3 sentences max), warm, and actionable. Use markdown formatting for emphasis (**bold**, *italic*) and bullet points when listing items. Be encouraging and focus on one main suggestion per response rather than overwhelming with information."
    )
    
    full_prompt = base_prompt + conversation_context + f"\n\nUser: {user_message}\nZelda:"
    
    try:
        print("🤖 Attempting to connect to Ollama with context...")
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama3.2',
                'prompt': full_prompt,
                'stream': False
            },
            timeout=15  # Slightly longer timeout for context processing
        )
        response.raise_for_status()
        data = response.json()
        reply = data.get('response', 'I am here for you. How can I help?')
        print("✅ Got contextual response from Ollama")
        return reply
        
    except requests.exceptions.ConnectionError:
        print("❌ Ollama not available, using fallback responses")
        return get_fallback_response_with_context(user_message, conversation_context)
    except Exception as e:
        print(f"❌ Error with Ollama: {str(e)}")
        return get_fallback_response_with_context(user_message, conversation_context)


def get_ai_reply(user_message):
    """Get AI reply with fallback responses if Ollama is not available"""
    return get_ai_reply_with_context(user_message, "")


def get_fallback_response_with_context(user_message, conversation_context=""):
    """Provide intelligent fallback responses with context awareness"""
    message_lower = user_message.lower()
    
    # Check if this is a follow-up question
    is_followup = any(word in message_lower for word in ['also', 'and', 'what about', 'how about', 'tell me more', 'more details', 'continue', 'go on'])
    
    if is_followup and conversation_context:
        return "I'd love to continue our conversation! **Let me help you** with that next step. What specific area would you like to focus on?"
    
    # Use the regular fallback response for new topics
    return get_fallback_response(user_message)


def get_fallback_response(user_message):
    """Provide intelligent fallback responses when Ollama is not available"""
    message_lower = user_message.lower()
    
    # Greeting responses
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
        responses = [
            "Hello! **I'm Zelda**, your personal assistant. I'm here to help you stay organized and productive. What's on your mind?",
            "Hi there! **Ready to tackle your goals?** I'd love to help you organize your day. What would you like to work on?",
            "Good day! **Let's make today productive** together. How can I assist you?"
        ]
        
    # How are you responses
    elif any(word in message_lower for word in ['how are you', 'how do you feel', 'what\'s up']):
        responses = [
            "I'm doing great, thank you! **I'm here to support you** - what can I help you accomplish today?",
            "I'm excellent and **ready to help!** What's on your agenda?",
            "I'm at your service! **Let's focus on your goals** - what would you like to work on?"
        ]
        
    # Habit-related responses
    elif any(word in message_lower for word in ['habit', 'routine', 'daily', 'exercise', 'workout', 'reading', 'water']):
        responses = [
            "**Great thinking!** Building habits is so powerful. What specific habit would you like to start?",
            "I love helping with habits! **Small steps = big results.** What routine interests you?",
            "**Habits are game-changers!** What would you like to make consistent in your life?"
        ]
        
    # Task/productivity responses
    elif any(word in message_lower for word in ['task', 'work', 'productive', 'busy', 'schedule', 'plan', 'organize']):
        responses = [
            "**Let's get organized!** What's the most important thing you need to tackle today?",
            "**Smart approach!** ⚡ I can help you prioritize. What's on your to-do list?",
            "**I'm here to help!** � What would you like to organize first?"
        ]
        
    # Goal and achievement responses
    elif any(word in message_lower for word in ['goal', 'achieve', 'success', 'improve', 'better', 'progress']):
        responses = [
            "I'm excited to help you reach your goals! Every small step counts toward bigger achievements. What specific area would you like to focus on?",
            "Success is built one day at a time!  Let's break down your goals into actionable steps. What would you like to work on first?",
            "Progress is the best motivator! I can help you track your improvements in both tasks and habits. What's your main focus right now?"
        ]
        
    # Motivation/encouragement
    elif any(word in message_lower for word in ['tired', 'stressed', 'difficult', 'hard', 'struggle', 'help']):
        responses = [
            "I hear you, and I want you to know that what you're feeling is completely valid.  Every challenge is an opportunity to grow stronger. Let's take this one step at a time.",
            "You're being so brave by reaching out!  Remember, even the smallest progress is still progress. What's one tiny thing we can do right now to make you feel better?",
            "I'm here for you!  Life can be challenging, but you have more strength than you realize. Let's find a small, manageable way to move forward together."
        ]
        
    # Default friendly responses
    else:
        responses = [
            "That's interesting!  I'm here to help you with whatever you're working on. Whether it's building better habits, staying organized, or just having a friendly chat - I'm all ears!",
            "I appreciate you sharing that with me!  As your AI companion, I'm here to support you in creating positive changes in your life. How can we make today a little bit better?",
            "Thanks for talking with me!  I love helping people discover their potential and build amazing routines. What aspect of your life would you like to improve?"
        ]
    
    return random.choice(responses)


def get_motivation_message():
    """Get motivational message with fallback if Ollama is not available"""
    try:
        print("🤖 Getting motivation from Ollama...")
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama3.2',
                'prompt': "Give me a short, positive motivational message for today in a small sentence.",
                'stream': False
            },
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        message = data.get('response', 'Stay motivated!')
        print("✅ Got motivation from Ollama")
        return message
        
    except Exception:
        print("❌ Using fallback motivation")
        motivational_messages = [
            "Every small step counts! You're building something amazing. ",
            "Today is full of possibilities. Let's make it count! ",
            "You have the power to create positive change. Believe in yourself! ",
            "Progress, not perfection. You're doing great! ",
            "Your future self will thank you for the effort you put in today! ",
            "Small consistent actions lead to extraordinary results! ",
            "You're stronger than you think and capable of more than you imagine! "
        ]
        return random.choice(motivational_messages)
