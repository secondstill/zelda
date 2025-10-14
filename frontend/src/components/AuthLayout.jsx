import React from 'react';
import Navigation from './Navigation';
import { useLocation } from 'react-router-dom';
import './Layout.css';

const AuthLayout = ({ children }) => {
  const location = useLocation();
  
  return (
    <div className="app-container">
      <div className="app-sidebar">
        <Navigation currentPath={location.pathname} />
      </div>
      <main className="app-main">
        <div className="auth-page">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AuthLayout;
