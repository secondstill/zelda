import { api } from './api';

export const habitsService = {
  async getHabits() {
    try {
      console.log('🎯 Getting habits from API...');
      const response = await api.get('/api/habits');
      console.log('✅ Get habits response:', response.data);
      return {
        success: true,
        habits: response.data.habits
      };
    } catch (error) {
      console.log('❌ Get habits error:', error.response?.data || error.message);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to fetch habits'
      };
    }
  },

  async toggleHabitDate(habitName, date) {
    try {
      const response = await api.post('/api/habits', {
        habit: habitName,
        date: date
      });
      return {
        success: true,
        habits: response.data.habits
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to toggle habit'
      };
    }
  },

  async addHabit(habitName) {
    try {
      console.log('🆕 Adding habit:', habitName);
      const response = await api.post('/api/habits/new', {
        habit: habitName
      });
      console.log('✅ Add habit response:', response.data);
      return {
        success: true,
        habits: response.data.habits
      };
    } catch (error) {
      console.log('❌ Add habit error:', error.response?.data || error.message);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to add habit'
      };
    }
  },

  async updateHabitColor(habitName, color) {
    try {
      const response = await api.post('/api/habits/color', {
        habit: habitName,
        color: color
      });
      return {
        success: true,
        habits: response.data.habits
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to update color'
      };
    }
  },

  async renameHabit(oldName, newName) {
    try {
      const response = await api.post('/api/habits/rename', {
        old: oldName,
        new: newName
      });
      return {
        success: true,
        habits: response.data.habits
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to rename habit'
      };
    }
  },

  async deleteHabit(habitName) {
    try {
      const response = await api.post('/api/habits/delete', {
        habit: habitName
      });
      return {
        success: true,
        habits: response.data.habits
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to delete habit'
      };
    }
  }
};
