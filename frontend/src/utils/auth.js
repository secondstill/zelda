import API_BASE_URL from '../services/api';

export const validateToken = (token) => {
  if (!token) return { valid: false, reason: 'No token provided' };
  
  const parts = token.split('.');
  if (parts.length !== 3) {
    return { valid: false, reason: 'Invalid token structure' };
  }
  
  try {
    const payload = JSON.parse(atob(parts[1]));
    const now = Math.floor(Date.now() / 1000);
    
    if (payload.exp && payload.exp < now) {
      return { 
        valid: false, 
        reason: 'Token expired',
        expiredAt: new Date(payload.exp * 1000).toISOString()
      };
    }
    
    return { 
      valid: true, 
      payload,
      expiresAt: new Date(payload.exp * 1000).toISOString()
    };
    
  } catch (error) {
    return { valid: false, reason: 'Invalid token format' };
  }
};

export const getAuthHeader = () => {
  const token = localStorage.getItem('token');
  const validation = validateToken(token);
  
  if (!validation.valid) {
    console.error('❌ Token validation failed:', validation.reason);
    localStorage.removeItem('token');
    return null;
  }
  
  return `Bearer ${token}`;
};

export const makeAuthenticatedRequest = async (url, options = {}) => {
  const authHeader = getAuthHeader();
  
  if (!authHeader) {
    throw new Error('Authentication required');
  }
  
  // Ensure we use the full URL if it's a relative path
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  
  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': authHeader,
    },
  });
  
  if (response.status === 401) {
    localStorage.removeItem('token');
    throw new Error('Authentication failed - please login again');
  }
  
  return response;
};

// Additional utility functions
export const isAuthenticated = () => {
  const token = localStorage.getItem('token');
  return validateToken(token).valid;
};

export const getUserFromToken = () => {
  const token = localStorage.getItem('token');
  const validation = validateToken(token);
  
  if (validation.valid) {
    return validation.payload;
  }
  
  return null;
};

export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  
  // Redirect to login page if not already there
  if (window.location.pathname !== '/login' && window.location.pathname !== '/signup') {
    window.location.href = '/login';
  }
};

export const getTokenInfo = () => {
  const token = localStorage.getItem('token');
  const validation = validateToken(token);
  
  return {
    isValid: validation.valid,
    reason: validation.reason,
    payload: validation.payload,
    expiresAt: validation.expiresAt,
    expiredAt: validation.expiredAt
  };
};

// Helper function for handling auth errors consistently
export const handleAuthError = (error, setError = null, setMessage = null) => {
  console.error('🚨 Authentication error:', error);
  
  if (error.message.includes('Authentication') || error.message.includes('401')) {
    const message = 'Session expired. Please login again.';
    
    if (setError) setError(message);
    if (setMessage) setMessage(message);
    
    localStorage.removeItem('token');
    
    // Auto redirect after a short delay
    setTimeout(() => {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }, 2000);
  } else {
    const message = `Error: ${error.message}`;
    if (setError) setError(message);
    if (setMessage) setMessage(message);
  }
};