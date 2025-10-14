import React from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navigation from './Navigation';
import EnhancedVoiceAssistant from './EnhancedVoiceAssistant';
import './Layout.css';

const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Handle voice command results
  const handleVoiceCommand = (result) => {
    console.log('🎙️ Voice command result received in Layout:', result);
    
    // Handle different types of voice command results
    if (result.action_taken && result.habit_action) {
      const commandAction = result.habit_action.action;
      const frontendAction = result.frontend_action;
      
      console.log('🎯 Voice command detected:', commandAction);
      console.log('🎬 Frontend action:', frontendAction);
      
      // Handle frontend actions first
      if (frontendAction) {
        console.log('🎬 Processing frontend action:', frontendAction);
        switch (frontendAction.type) {
          case 'navigate':
            if (frontendAction.navigate) {
              console.log('🧭 Navigating to:', frontendAction.navigate);
              // Use React Router navigation properly
              navigate(frontendAction.navigate);
            }
            break;
          
          case 'logout':
            console.log('👋 Logging out user');
            localStorage.removeItem('token');
            window.location.href = '/login';
            break;
          
          case 'refresh':
            console.log('🔄 Refreshing page');
            window.location.reload();
            break;
          
          case 'refresh_habits':
            console.log('📡 Dispatching habitDataChanged event');
            window.dispatchEvent(new CustomEvent('habitDataChanged', { 
              detail: { 
                action: commandAction,
                data: result.habit_action.data 
              }
            }));
            break;
        }
      }
      
      // Handle habit-specific refreshes if no frontend action specified
      if (!frontendAction && commandAction && ['add_habit', 'complete_habit', 'delete_habit', 'edit_habit'].includes(commandAction)) {
        console.log('📡 Dispatching habitDataChanged event (fallback)');
        window.dispatchEvent(new CustomEvent('habitDataChanged', { 
          detail: { 
            action: commandAction,
            data: result.habit_action.data 
          }
        }));
      }
    }
    
    // Show success notification if needed
    if (result.reply) {
      console.log('Voice command result:', result.reply);
    }
  };
  
  return (
    <div className="app-container">
      <div className="app-sidebar">
        <Navigation currentPath={location.pathname} />
      </div>
      <main className="app-main">
        {user ? (
          <div className="content-page">
            <Outlet />
            {/* Enhanced Voice Assistant - Only show when user is authenticated */}
            <EnhancedVoiceAssistant onVoiceCommand={handleVoiceCommand} />
          </div>
        ) : (
          <div className="auth-welcome-page">
            <div className="welcome-content">
              <h1>Welcome to Zelda</h1>
              <p>Your intelligent habit tracking and productivity assistant</p>
              <div className="welcome-features">
                <div className="feature">
                  <h3>🎯 Track Habits</h3>
                  <p>Build and maintain positive habits with intelligent tracking</p>
                </div>
                <div className="feature">
                  <h3>📊 Analytics</h3>
                  <p>Get insights into your progress and performance</p>
                </div>
                <div className="feature">
                  <h3>💬 AI Assistant</h3>
                  <p>Chat with your personal productivity assistant</p>
                </div>
                <div className="feature">
                  <h3>🎤 Voice Control</h3>
                  <p>Control your habits with natural voice commands</p>
                </div>
                <div className="feature">
                  <h3>⚙️ Personalization</h3>
                  <p>Customize your experience to fit your lifestyle</p>
                </div>
              </div>
              <p className="auth-instruction">Please sign in to get started!</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Layout;
