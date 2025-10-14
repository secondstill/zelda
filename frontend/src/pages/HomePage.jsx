import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { TrendingUp, BarChart3, MessageCircle, Settings, CheckCircle } from 'lucide-react';
import { api } from '../services/api';
import './HomePage.css';

const HomePage = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Only fetch stats if user is logged in
    if (user) {
      fetchUserStats();
    }
  }, [user]);

  const fetchUserStats = async () => {
    try {
      console.log('📊 Fetching user stats...');
      const response = await api.get('/api/user-stats');
      if (response.data.success) {
        console.log('✅ Stats fetched:', response.data.stats);
        setStats(response.data.stats);
      } else {
        console.log('❌ Stats fetch failed:', response.data.error);
      }
    } catch (error) {
      console.error('💥 Failed to fetch stats:', error.response?.data || error.message);
    } finally {
      setLoading(false);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const dashboardCards = [
    {
      title: 'Habits',
      description: 'Track your daily habits',
      icon: TrendingUp,
      link: '/habits',
      color: '#2ecc40',
      stat: stats?.habits_count || 0,
      statLabel: 'Active Habits'
    },
    {
      title: 'Analytics',
      description: 'View your progress',
      icon: BarChart3,
      link: '/analytics',
      color: '#3498db',
      stat: stats?.completion_rate || 0,
      statLabel: 'Completion Rate'
    },
    {
      title: 'Chat',
      description: 'Talk with Zelda',
      icon: MessageCircle,
      link: '/chat',
      color: '#9b59b6',
      stat: stats?.current_streak || 0,
      statLabel: 'Day Streak'
    },
    {
      title: 'Settings',
      description: 'Manage your account',
      icon: Settings,
      link: '/settings',
      color: '#95a5a6',
      stat: stats?.monthly_completions || 0,
      statLabel: 'This Month'
    }
  ];

  if (loading) {
    return (
      <div className="home-page">
        <div className="loading">Loading your dashboard...</div>
      </div>
    );
  }

  return (
    <div className="home-page">
      <div className="home-container">
        <div className="home-header">
          <div className="greeting">
            <h1>{getGreeting()}, {user?.full_name || user?.username}!</h1>
            <p>Ready to make today productive?</p>
          </div>
          
          {stats && (
            <div className="quick-stats">
              <div className="stat-item">
                <CheckCircle size={24} className="stat-icon" />
                <div>
                  <span className="stat-number">{stats.monthly_completions}</span>
                  <span className="stat-label">Habits completed this month</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="dashboard-grid">
          {dashboardCards.map((card) => {
            const IconComponent = card.icon;
            
            return (
              <Link
                key={card.title}
                to={card.link}
                className="dashboard-card"
                style={{ '--card-color': card.color }}
              >
                <div className="card-header">
                  <div className="card-icon">
                    <IconComponent size={32} />
                  </div>
                  <div className="card-stat">
                    <span className="stat-number">{card.stat}</span>
                    <span className="stat-label">{card.statLabel}</span>
                  </div>
                </div>
                
                <div className="card-content">
                  <h3>{card.title}</h3>
                  <p>{card.description}</p>
                </div>
              </Link>
            );
          })}
        </div>

        <div className="motivational-section">
          <h2>Today's Focus</h2>
          <p>Small consistent actions lead to remarkable results. What will you accomplish today?</p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
