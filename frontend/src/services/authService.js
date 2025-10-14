import { api } from './api';

export const authService = {
  async login(credentials) {
    try {
      const response = await api.post('/login', credentials);
      return {
        success: true,
        user: response.data.user,
        token: response.data.token
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Login failed'
      };
    }
  },

  async signup(userData) {
    try {
      const response = await api.post('/signup', userData);
      return {
        success: true,
        user: response.data.user,
        token: response.data.token
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Signup failed'
      };
    }
  },

  async updateProfile(profileData) {
    try {
      const response = await api.post('/api/update-profile', profileData);
      return {
        success: true,
        user: response.data.user
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Profile update failed'
      };
    }
  },

  async changePassword(passwordData) {
    try {
      const response = await api.post('/api/change-password', passwordData);
      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Password change failed'
      };
    }
  }
};
