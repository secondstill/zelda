import React, { useState, useEffect } from 'react';
import { habitsService } from '../services/habitsService';
import { api } from '../services/api';
import { 
  TrendingUp, 
  Calendar, 
  Target, 
  Award, 
  BarChart3, 
  PieChart,
  Activity,
  Clock,
  Zap,
  CheckCircle
} from 'lucide-react';
import './AnalyticsPage.css';

const AnalyticsPage = () => {
  const [habits, setHabits] = useState({});
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      console.log('📊 Fetching analytics data...');
      
      // Fetch habits and stats
      const [habitsResult, statsResponse] = await Promise.all([
        habitsService.getHabits(),
        api.get('/api/user-stats')
      ]);

      if (habitsResult.success) {
        setHabits(habitsResult.habits);
      }

      if (statsResponse.data.success) {
        setStats(statsResponse.data.stats);
      }

    } catch (error) {
      console.error('❌ Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateAnalytics = () => {
    const habitNames = Object.keys(habits);
    if (habitNames.length === 0) return null;

    const today = new Date();
    let totalHabits = habitNames.length;
    let overallCompleted = 0;
    let overallTotal = 0;
    let streaks = [];
    let habitStats = {};

    habitNames.forEach(habitName => {
      const habitData = habits[habitName];
      const dates = habitData.dates || {};
      
      // Find the first date this habit was tracked (creation date)
      const trackedDates = Object.keys(dates).sort();
      if (trackedDates.length === 0) {
        habitStats[habitName] = {
          completed: 0,
          total: 0,
          percentage: 0,
          currentStreak: 0,
          createdDate: today.toISOString().split('T')[0]
        };
        return;
      }
      
      const createdDate = new Date(trackedDates[0]);
      const daysSinceCreation = Math.floor((today - createdDate) / (1000 * 60 * 60 * 24)) + 1;
      
      let completed = 0;
      let currentStreak = 0;
      let maxStreak = 0;
      let tempStreak = 0;

      // Calculate stats from creation date to today
      for (let i = 0; i < daysSinceCreation; i++) {
        const date = new Date(createdDate);
        date.setDate(date.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        
        if (dates[dateStr]) {
          completed++;
          tempStreak++;
          maxStreak = Math.max(maxStreak, tempStreak);
        } else {
          if (tempStreak > 0) {
            streaks.push(tempStreak);
            tempStreak = 0;
          }
        }
        
        // Current streak calculation (from today backwards)
        if (i === daysSinceCreation - 1 && dates[dateStr]) {
          currentStreak = tempStreak;
        }
      }

      if (tempStreak > 0) {
        streaks.push(tempStreak);
      }

      habitStats[habitName] = {
        completed,
        total: daysSinceCreation,
        percentage: daysSinceCreation > 0 ? Math.round((completed / daysSinceCreation) * 100) : 0,
        currentStreak: currentStreak,
        maxStreak: maxStreak,
        createdDate: trackedDates[0]
      };

      overallTotal += daysSinceCreation;
      overallCompleted += completed;
    });

    const overallPercentage = overallTotal > 0 ? Math.round((overallCompleted / overallTotal) * 100) : 0;
    const bestStreak = streaks.length > 0 ? Math.max(...streaks) : 0;
    const avgStreak = streaks.length > 0 ? Math.round(streaks.reduce((a, b) => a + b, 0) / streaks.length) : 0;
    const activeHabits = Object.values(habitStats).filter(stat => stat.total > 0).length;

    return {
      overallPercentage,
      totalDays: overallTotal,
      completedDays: overallCompleted,
      bestStreak,
      avgStreak,
      habitStats,
      totalHabits,
      activeHabits
    };
  };

  const analytics = calculateAnalytics();

  if (loading) {
    return (
      <div className="analytics-page">
        <div className="analytics-container">
          <div className="loading">Loading analytics...</div>
        </div>
      </div>
    );
  }

  if (!analytics || Object.keys(habits).length === 0) {
    return (
      <div className="analytics-page">
        <div className="analytics-container">
          <div className="empty-state">
            <BarChart3 size={64} />
            <h2>No Analytics Available</h2>
            <p>Start tracking some habits to see your analytics!</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      <div className="analytics-container">
        {/* Header */}
        <div className="analytics-header">
          <div className="header-content">
            <h1>📈 Analytics Dashboard</h1>
            <p>Track your progress and celebrate your achievements</p>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="metrics-grid">
          <div className="metric-card completion">
            <div className="metric-icon">
              <Target size={32} />
            </div>
            <div className="metric-content">
              <h3>Overall Completion</h3>
              <div className="metric-value">{analytics.overallPercentage}%</div>
              <p>{analytics.completedDays} of {analytics.totalDays} days</p>
            </div>
          </div>

          <div className="metric-card streak">
            <div className="metric-icon">
              <Zap size={32} />
            </div>
            <div className="metric-content">
              <h3>Best Streak</h3>
              <div className="metric-value">{analytics.bestStreak}</div>
              <p>consecutive days</p>
            </div>
          </div>

          <div className="metric-card habits">
            <div className="metric-icon">
              <Activity size={32} />
            </div>
            <div className="metric-content">
              <h3>Active Habits</h3>
              <div className="metric-value">{analytics.activeHabits}</div>
              <p>habits tracked</p>
            </div>
          </div>

          <div className="metric-card average">
            <div className="metric-icon">
              <Clock size={32} />
            </div>
            <div className="metric-content">
              <h3>Avg Streak</h3>
              <div className="metric-value">{analytics.avgStreak}</div>
              <p>days per streak</p>
            </div>
          </div>
        </div>

        {/* Habit Breakdown */}
        <div className="habit-breakdown">
          <h2>Habit Performance</h2>
          <div className="habit-stats">
            {Object.entries(analytics.habitStats).map(([habitName, data]) => (
              <div key={habitName} className="habit-stat-card">
                <div className="habit-header">
                  <h3>{habitName}</h3>
                  <div className="completion-badge">
                    {data.percentage}%
                  </div>
                </div>
                
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${data.percentage}%` }}
                  />
                </div>
                
                <div className="habit-details">
                  <div className="detail-item">
                    <CheckCircle size={16} />
                    <span>{data.completed} completed</span>
                  </div>
                  <div className="detail-item">
                    <Zap size={16} />
                    <span>{data.currentStreak} day streak</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Weekly Performance Chart (Visual representation) */}
        <div className="performance-chart">
          <h2>Recent Performance</h2>
          <div className="chart-container">
            <div className="chart-placeholder">
              <PieChart size={48} />
              <p>Visual charts coming soon!</p>
              <p>Your overall completion rate: <strong>{analytics.overallPercentage}%</strong></p>
            </div>
          </div>
        </div>

        {/* Insights */}
        <div className="insights-section">
          <h2>💡 Insights</h2>
          <div className="insights">
            {analytics.overallPercentage >= 80 && (
              <div className="insight success">
                <Award size={24} />
                <div>
                  <h4>Excellent Progress!</h4>
                  <p>You're maintaining an {analytics.overallPercentage}% completion rate. Keep up the amazing work!</p>
                </div>
              </div>
            )}
            
            {analytics.overallPercentage < 50 && (
              <div className="insight warning">
                <TrendingUp size={24} />
                <div>
                  <h4>Room for Improvement</h4>
                  <p>Try focusing on one habit at a time to build momentum. Small consistent steps lead to big wins!</p>
                </div>
              </div>
            )}
            
            {analytics.bestStreak >= 7 && (
              <div className="insight achievement">
                <Zap size={24} />
                <div>
                  <h4>Streak Master!</h4>
                  <p>You've achieved a {analytics.bestStreak}-day streak! Consistency is the key to lasting change.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    
  );
};

export default AnalyticsPage;
