import { api } from './api';

export const chatService = {
  async sendMessage(message) {
    try {
      console.log(`💬 Sending message: ${message}`);
      const response = await api.post('/api/chat', {
        message: message
      });
      
      if (response.data.success) {
        console.log(`🤖 Received reply: ${response.data.reply.substring(0, 100)}...`);
        return {
          success: true,
          reply: response.data.reply
        };
      } else {
        throw new Error(response.data.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('❌ Chat error:', error);
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Failed to send message',
        reply: "I'm having trouble connecting right now, but I'm here to help when you need me!"
      };
    }
  },

  // Get chat history
  async getChatHistory() {
    try {
      console.log('📖 Loading chat history...');
      const response = await api.get('/api/chat-history');
      
      if (response.data.success) {
        console.log(`✅ Loaded ${response.data.messages.length} chat messages`);
        return {
          success: true,
          messages: response.data.messages
        };
      } else {
        return {
          success: false,
          messages: []
        };
      }
    } catch (error) {
      console.error('❌ Error loading chat history:', error);
      return {
        success: false,
        messages: [],
        error: error.message
      };
    }
  },

  async sendVoiceMessage(audioBlob) {
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice.wav');

      const response = await api.post('/api/voice', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return {
        success: true,
        transcript: response.data.transcript,
        reply: response.data.reply,
        action: response.data.action
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to process voice message'
      };
    }
  }
};
