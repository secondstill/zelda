import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';
import { isAuthenticated, getUserFromToken, logout as authLogout } from '../utils/auth';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in on app start using auth utilities
    if (isAuthenticated()) {
      const userData = getUserFromToken();
      if (userData) {
        setUser({
          id: userData.user_id,
          username: userData.username,
          email: userData.email,
          full_name: userData.full_name
        });
      }
    }
    setLoading(false);
  }, []);

  const login = async (credentials) => {
    try {
      console.log('🔐 Attempting login with:', credentials.username);
      const response = await authService.login(credentials);
      console.log('📝 Login response:', response);
      
      if (response.success && response.token && response.user) {
        console.log('✅ Login successful, storing user data');
        
        // Store token (using consistent key name)
        localStorage.setItem('token', response.token);
        localStorage.setItem('user', JSON.stringify(response.user));
        console.log('💾 Stored token:', response.token.substring(0, 20) + '...');
        
        // Then set user state
        setUser(response.user);
        
        return { success: true };
      }
      console.log('❌ Login failed:', response.error);
      return { success: false, error: response.error || 'Login failed' };
    } catch (error) {
      console.log('💥 Login error:', error);
      return { success: false, error: 'Login failed' };
    }
  };

  const signup = async (userData) => {
    try {
      const response = await authService.signup(userData);
      if (response.success) {
        setUser(response.user);
        localStorage.setItem('token', response.token);
        localStorage.setItem('user', JSON.stringify(response.user));
        return { success: true };
      }
      return { success: false, error: response.error };
    } catch (error) {
      return { success: false, error: 'Signup failed' };
    }
  };

  const logout = () => {
    setUser(null);
    authLogout(); // Use auth utility for consistent logout
  };

  const updateUser = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const updateProfile = async (profileData) => {
    try {
      const response = await authService.updateProfile(profileData);
      if (response.success) {
        setUser(response.user);
        localStorage.setItem('user', JSON.stringify(response.user));
        return { success: true };
      }
      return { success: false, error: response.error };
    } catch (error) {
      return { success: false, error: 'Profile update failed' };
    }
  };

  const changePassword = async (passwordData) => {
    try {
      const response = await authService.changePassword(passwordData);
      return response;
    } catch (error) {
      return { success: false, error: 'Password change failed' };
    }
  };

  const value = {
    user,
    login,
    signup,
    logout,
    updateUser,
    updateProfile,
    changePassword,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
