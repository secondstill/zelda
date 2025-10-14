import axios from 'axios';
import { getAuthHeader, logout, validateToken } from '../utils/auth';

const API_BASE_URL = 'http://localhost:8091';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    // Use auth utilities for consistent token handling
    const token = localStorage.getItem('token');
    const validation = validateToken(token);
    
    if (validation.valid) {
      const authHeader = getAuthHeader();
      if (authHeader) {
        console.log('🔑 Adding valid token to request');
        config.headers['Authorization'] = authHeader;
      }
    } else {
      console.log('⚠️ No valid token found:', validation.reason);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle common errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - use auth utility for consistent handling
      console.log('🚪 401 Unauthorized - clearing auth and redirecting to login');
      logout();
    }
    return Promise.reject(error);
  }
);

export { api };
export default API_BASE_URL;
