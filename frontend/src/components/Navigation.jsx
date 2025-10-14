import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Home, BarChart3, MessageCircle, Settings, TrendingUp, LogOut, Eye, EyeOff, User, Lock, Mail, UserCheck } from 'lucide-react';
import './Navigation.css';

const Navigation = ({ currentPath }) => {
  const { user, logout, login, signup } = useAuth();
  const navigate = useNavigate();
  
  const [isSignup, setIsSignup] = useState(currentPath === '/signup');
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    full_name: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const navItems = [
    { path: '/home', icon: Home, label: 'Home' },
    { path: '/habits', icon: TrendingUp, label: 'Habits' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics' },
    { path: '/chat', icon: MessageCircle, label: 'Chat' },
    { path: '/settings', icon: Settings, label: 'Settings' }
  ];

  const handleLogout = () => {
    logout();
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    if (error) setError('');
  };

  const validateSignupForm = () => {
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long');
      return false;
    }
    if (formData.username.length < 3) {
      setError('Username must be at least 3 characters long');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    let result;
    if (isSignup) {
      if (!validateSignupForm()) {
        setLoading(false);
        return;
      }
      const { confirmPassword, ...signupData } = formData;
      result = await signup(signupData);
    } else {
      result = await login({ username: formData.username, password: formData.password });
    }
    
    if (result.success) {
      navigate('/home');
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  const toggleAuthMode = () => {
    setIsSignup(!isSignup);
    setError('');
    setFormData({
      username: '',
      password: '',
      email: '',
      full_name: '',
      confirmPassword: ''
    });
  };

  const isAuthPage = currentPath === '/login' || currentPath === '/signup';

  return (
    <nav className="navigation">
      <div className="nav-header">
        <h2 className="nav-title">Zelda</h2>
        {user && !isAuthPage ? (
          <div className="user-info">
            <div className="user-avatar">
              {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <span className="username">{user?.full_name || user?.username}</span>
          </div>
        ) : null}
      </div>
      
      <div className="nav-content">
        {user && !isAuthPage ? (
          <div className="nav-items">
            {navItems.map((item) => {
              const IconComponent = item.icon;
              const isActive = currentPath === item.path;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                >
                  <IconComponent size={20} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="auth-form-container">
            <div className="auth-header">
              <h3>{isSignup ? 'Join Zelda' : 'Welcome Back'}</h3>
              <p>{isSignup ? 'Create your account' : 'Sign in to continue'}</p>
            </div>

            {error && (
              <div className="auth-error">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="sidebar-auth-form">
              {isSignup && (
                <div className="form-group">
                  <label htmlFor="full_name">
                    <UserCheck size={16} />
                    Full Name
                  </label>
                  <input
                    type="text"
                    id="full_name"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleInputChange}
                    placeholder="Enter your full name"
                    required
                  />
                </div>
              )}

              <div className="form-group">
                <label htmlFor="username">
                  <User size={16} />
                  Username
                </label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  value={formData.username}
                  onChange={handleInputChange}
                  placeholder={isSignup ? "Choose a username" : "Enter your username"}
                  required
                />
              </div>

              {isSignup && (
                <div className="form-group">
                  <label htmlFor="email">
                    <Mail size={16} />
                    Email
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="Enter your email"
                    required
                  />
                </div>
              )}

              <div className="form-group">
                <label htmlFor="password">
                  <Lock size={16} />
                  Password
                </label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    placeholder={isSignup ? "Create a password" : "Enter your password"}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {isSignup && (
                <div className="form-group">
                  <label htmlFor="confirmPassword">
                    <Lock size={16} />
                    Confirm Password
                  </label>
                  <div className="password-input-wrapper">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      id="confirmPassword"
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                      placeholder="Confirm your password"
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    >
                      {showConfirmPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
              )}

              <button 
                type="submit" 
                className="auth-submit-btn"
                disabled={loading}
              >
                {loading ? (isSignup ? 'Creating Account...' : 'Signing in...') : (isSignup ? 'Create Account' : 'Sign In')}
              </button>
            </form>

            <div className="auth-switch">
              <p>
                {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
                <button onClick={toggleAuthMode} className="auth-toggle-btn">
                  {isSignup ? 'Sign In' : 'Sign Up'}
                </button>
              </p>
            </div>
          </div>
        )}
      </div>
      
      {user && !isAuthPage && (
        <div className="nav-footer">
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      )}
    </nav>
  );
};

export default Navigation;
