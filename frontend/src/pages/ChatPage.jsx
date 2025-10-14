import React, { useState, useEffect, useRef } from 'react';
import { chatService } from '../services/chatService';
import { Send, Sparkles, User, ArrowLeft, Mic } from 'lucide-react';
import { Link } from 'react-router-dom';
import { marked } from 'marked';
import './ChatPage.css';

// Configure marked for better rendering
marked.setOptions({
  breaks: true,
  gfm: true
});

const MessageContent = ({ content, isUser }) => {
  if (isUser) {
    return <span>{content}</span>;
  }
  
  // For assistant messages, render markdown
  const htmlContent = marked(content);
  return (
    <div 
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
};

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    // Load chat history from server
    loadChatHistory();
  }, []);

  const loadChatHistory = async () => {
    try {
      console.log('📖 Loading chat history...');
      const result = await chatService.getChatHistory();
      
      if (result.success && result.messages.length > 0) {
        // Convert timestamps to Date objects while preserving original times
        const messagesWithDates = result.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp) // This will correctly parse the stored timestamp
        }));
        setMessages(messagesWithDates);
        console.log(`✅ Loaded ${messagesWithDates.length} chat messages`);
      } else {
        // Add welcome message if no history
        const welcomeMessage = {
          id: 1,
          content: "Hello! I'm Zelda, your intelligent AI assistant. I'm here to help you stay organized and productive. Ask me anything or let's start by setting up your goals!",
          isUser: false,
          timestamp: new Date()
        };
        setMessages([welcomeMessage]);
        console.log('🎉 Added welcome message');
      }
    } catch (error) {
      console.error('❌ Error loading chat history:', error);
      // Fallback to welcome message
      const welcomeMessage = {
        id: 1,
        content: "Hello! I'm Zelda, your intelligent AI assistant. I'm here to help you stay organized and productive. Ask me anything or let's start by setting up your goals!",
        isUser: false,
        timestamp: new Date()
      };
      setMessages([welcomeMessage]);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const addMessage = (content, isUser = false) => {
    // Create timestamp in IST
    const currentTime = new Date();
    const newMessage = {
      id: Date.now() + Math.random(), // Ensure unique IDs
      content,
      isUser,
      timestamp: currentTime // Browser will handle IST conversion in formatTime
    };
    setMessages(prev => [...prev, newMessage]);
    return newMessage; // Return the message for potential use
  };

  const showTypingIndicator = () => {
    setIsTyping(true);
  };

  const hideTypingIndicator = () => {
    setIsTyping(false);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    const message = inputMessage.trim();
    if (!message || isLoading) return;

    // Add user message
    addMessage(message, true);
    setInputMessage('');
    setIsLoading(true);
    showTypingIndicator();

    try {
      const result = await chatService.sendMessage(message);
      
      hideTypingIndicator();
      setTimeout(() => {
        if (result.success) {
          addMessage(result.reply, false);
        } else {
          addMessage(result.reply || "I'm having trouble connecting right now, but I'm here to help when you need me!", false);
        }
        setIsLoading(false);
      }, 500); // Small delay for natural feel
    } catch (error) {
      console.error('Chat error:', error);
      hideTypingIndicator();
      setTimeout(() => {
        addMessage("I'm having trouble connecting right now, but I'm here to help when you need me!", false);
        setIsLoading(false);
      }, 500);
    }
  };

  const formatTime = (timestamp) => {
    // Ensure we have a proper Date object
    let date;
    if (timestamp instanceof Date) {
      date = timestamp;
    } else {
      date = new Date(timestamp);
    }
    
    // Format in IST (Indian Standard Time)
    return date.toLocaleTimeString('en-IN', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Kolkata'
    });
  };

  return (
    <div className="chat-page">
      <div className="chat-container">
        {/* Header */}
        <div className="chat-header">
          <div className="header-left">
            <Link to="/" className="back-link">
              <ArrowLeft size={20} />
              Home
            </Link>
            <h1>
              <Sparkles className="title-icon" />
              Chat with Zelda
            </h1>
          </div>
          <div className="voice-controls">
            <button className="voice-btn" title="Voice chat (coming soon)">
              <Mic size={20} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {messages.map((message) => (
            <div 
              key={message.id} 
              className={`chat-message ${message.isUser ? 'user' : 'assistant'}`}
            >
              <div className="message-avatar">
                {message.isUser ? <User size={18} /> : <Sparkles size={18} />}
              </div>
              <div className="message-content">
                <div className="message-bubble">
                  <MessageContent content={message.content} isUser={message.isUser} />
                </div>
                <div className="message-time">
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          ))}
          
          {isTyping && (
            <div className="chat-message assistant typing">
              <div className="message-avatar">
                <Sparkles size={18} />
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <div className="typing-dots">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                  <span>Zelda is thinking...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-container">
          <form onSubmit={handleSendMessage} className="chat-input-form">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Type your message here..."
              className="chat-input"
              disabled={isLoading}
              autoFocus
            />
            <button 
              type="submit" 
              className="send-button"
              disabled={isLoading || !inputMessage.trim()}
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
