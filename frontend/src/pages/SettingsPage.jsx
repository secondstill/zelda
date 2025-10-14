import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { User, Key, LogOut } from 'lucide-react';
import './SettingsPage.css';

const SettingsPage = () => {
  const { user, logout, updateProfile, changePassword } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  
  // Profile form state
  const [profileData, setProfileData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    username: user?.username || ''
  });
  
  // Password form state
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  
  // Loading and message states
  const [profileLoading, setProfileLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [profileError, setProfileError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const handleLogout = () => {
    logout();
  };

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear messages when user starts typing
    if (profileMessage) setProfileMessage('');
    if (profileError) setProfileError('');
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear messages when user starts typing
    if (passwordMessage) setPasswordMessage('');
    if (passwordError) setPasswordError('');
  };

  const handleProfileSave = async (e) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileError('');
    setProfileMessage('');

    const result = await updateProfile(profileData);
    
    if (result.success) {
      setProfileMessage('Profile updated successfully!');
    } else {
      setProfileError(result.error);
    }
    
    setProfileLoading(false);
  };

  const validatePasswordForm = () => {
    if (!passwordData.current_password) {
      setPasswordError('Current password is required');
      return false;
    }
    if (!passwordData.new_password) {
      setPasswordError('New password is required');
      return false;
    }
    if (passwordData.new_password.length < 6) {
      setPasswordError('New password must be at least 6 characters long');
      return false;
    }
    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordError('New passwords do not match');
      return false;
    }
    return true;
  };

  const handlePasswordSave = async (e) => {
    e.preventDefault();
    setPasswordLoading(true);
    setPasswordError('');
    setPasswordMessage('');

    if (!validatePasswordForm()) {
      setPasswordLoading(false);
      return;
    }

    const result = await changePassword({
      current_password: passwordData.current_password,
      new_password: passwordData.new_password
    });
    
    if (result.success) {
      setPasswordMessage('Password updated successfully!');
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
    } else {
      setPasswordError(result.error);
    }
    
    setPasswordLoading(false);
  };

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Key },
  ];

  return (
    <div className="settings-page">
      <div className="settings-container">
        <div className="settings-header">
          <h1>⚙️ Settings</h1>
          <p>Manage your profile and security settings</p>
        </div>

        <div className="settings-content">
          <div className="settings-sidebar">
            {tabs.map(tab => {
              const IconComponent = tab.icon;
              return (
                <button
                  key={tab.id}
                  className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <IconComponent size={20} />
                  {tab.label}
                </button>
              );
            })}
            
            <button className="tab-btn logout" onClick={handleLogout}>
              <LogOut size={20} />
              Sign Out
            </button>
          </div>

          <div className="settings-main">
            {activeTab === 'profile' && (
              <div className="settings-section">
                <h2>Profile Information</h2>
                <div className="profile-card">
                  <div className="profile-avatar">
                    <User size={48} />
                  </div>
                  <div className="profile-info">
                    <h3>{user?.full_name}</h3>
                    <p>{user?.email}</p>
                    <span className="username">@{user?.username}</span>
                  </div>
                </div>
                
                {profileMessage && (
                  <div className="success-message">
                    {profileMessage}
                  </div>
                )}
                
                {profileError && (
                  <div className="error-message">
                    {profileError}
                  </div>
                )}
                
                <form onSubmit={handleProfileSave}>
                  <div className="form-group">
                    <label>Full Name</label>
                    <input 
                      type="text" 
                      name="full_name"
                      value={profileData.full_name}
                      onChange={handleProfileChange}
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>Email</label>
                    <input 
                      type="email" 
                      name="email"
                      value={profileData.email}
                      onChange={handleProfileChange}
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>Username</label>
                    <input 
                      type="text" 
                      name="username"
                      value={profileData.username}
                      onChange={handleProfileChange}
                      required
                    />
                  </div>
                  
                  <button 
                    type="submit" 
                    className="save-btn"
                    disabled={profileLoading}
                  >
                    {profileLoading ? 'Saving...' : 'Save Changes'}
                  </button>
                </form>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="settings-section">
                <h2>Security</h2>
                
                {passwordMessage && (
                  <div className="success-message">
                    {passwordMessage}
                  </div>
                )}
                
                {passwordError && (
                  <div className="error-message">
                    {passwordError}
                  </div>
                )}
                
                <form onSubmit={handlePasswordSave}>
                  <div className="form-group">
                    <label>Current Password</label>
                    <input 
                      type="password" 
                      name="current_password"
                      value={passwordData.current_password}
                      onChange={handlePasswordChange}
                      placeholder="Enter current password"
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>New Password</label>
                    <input 
                      type="password" 
                      name="new_password"
                      value={passwordData.new_password}
                      onChange={handlePasswordChange}
                      placeholder="Enter new password"
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>Confirm New Password</label>
                    <input 
                      type="password" 
                      name="confirm_password"
                      value={passwordData.confirm_password}
                      onChange={handlePasswordChange}
                      placeholder="Confirm new password"
                      required
                    />
                  </div>
                  
                  <button 
                    type="submit" 
                    className="save-btn"
                    disabled={passwordLoading}
                  >
                    {passwordLoading ? 'Updating...' : 'Update Password'}
                  </button>
                </form>
                
                <div className="security-info">
                  <h4>Account Security</h4>
                  <p>Last login: Today at 2:15 PM</p>
                  <p>Account created: September 2025</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
