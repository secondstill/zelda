import React, { useState, useEffect } from 'react';
import { habitsService } from '../services/habitsService';
import { Plus, Palette, Edit2, Trash2, Mic, Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import './HabitsPage.css';

const HabitsPage = () => {
  const [habits, setHabits] = useState({});
  const [loading, setLoading] = useState(true);
  const [newHabitName, setNewHabitName] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [viewMode, setViewMode] = useState('week'); // 'week' or 'month'
  const [currentMonth, setCurrentMonth] = useState(new Date());

  useEffect(() => {
    fetchHabits();
    
    // Listen for habit data changes from voice commands
    const handleHabitDataChanged = () => {
      console.log('🎙️ Voice command detected, refreshing habits...');
      fetchHabits();
    };
    
    window.addEventListener('habitDataChanged', handleHabitDataChanged);
    
    // Cleanup event listener on component unmount
    return () => {
      window.removeEventListener('habitDataChanged', handleHabitDataChanged);
    };
  }, []);

  const fetchHabits = async () => {
    try {
      console.log('🎯 Fetching habits...');
      setLoading(true);
      const result = await habitsService.getHabits();
      if (result.success) {
        console.log('✅ Habits fetched:', Object.keys(result.habits));
        setHabits(result.habits);
      } else {
        console.log('❌ Habits fetch failed:', result.error);
      }
    } catch (error) {
      console.error('💥 Habits fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddHabit = async (e) => {
    e.preventDefault();
    if (!newHabitName.trim()) return;

    const result = await habitsService.addHabit(newHabitName.trim());
    if (result.success) {
      setHabits(result.habits);
      setNewHabitName('');
      setShowAddForm(false);
    }
  };

  const handleToggleHabit = async (habitName, date) => {
    // Prevent toggling future dates
    const today = new Date().toISOString().split('T')[0];
    if (date > today) {
      return; // Don't allow future date changes
    }
    
    const result = await habitsService.toggleHabitDate(habitName, date);
    if (result.success) {
      setHabits(result.habits);
    }
  };

  const generateDateRange = () => {
    const dates = [];
    const today = new Date();
    
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      dates.push(date.toISOString().split('T')[0]);
    }
    
    return dates;
  };

  const generateMonthDates = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startDay = firstDay.getDay();

    const dates = [];

    // Leading empty cells
    for (let i = 0; i < startDay; i++) {
      dates.push(null);
    }

    // Actual days of the current month
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day);
      dates.push(date.toISOString().split('T')[0]);
    }

    // Trailing empty cells to complete last week
    const totalCells = Math.ceil((startDay + daysInMonth) / 7) * 7;
    while (dates.length < totalCells) {
      dates.push(null);
    }

    return dates;
  };

  const navigateMonth = (direction) => {
    const newMonth = new Date(currentMonth);
    newMonth.setMonth(currentMonth.getMonth() + direction);
    setCurrentMonth(newMonth);
  };

  const formatDateLabel = (dateString) => {
    const date = new Date(dateString);
    const today = new Date().toISOString().split('T')[0];
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayString = yesterday.toISOString().split('T')[0];

    if (dateString === today) return 'Today';
    if (dateString === yesterdayString) return 'Yesterday';
    
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const formatMonthDateLabel = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.getDate();
  };

  const isToday = (dateString) => {
    return dateString === new Date().toISOString().split('T')[0];
  };

  const dateRange = generateDateRange();
  const monthDates = generateMonthDates();

  if (loading) {
    return (
      <div className="habits-page">
        <div className="loading">Loading your habits...</div>
      </div>
    );
  }

  return (
    <div className="habits-page">
      <div className="habits-header">
        <h1>🎯 Habit Tracker</h1>
        <div className="header-actions">
          <div className="view-toggle">
            <button 
              className={`view-btn ${viewMode === 'week' ? 'active' : ''}`}
              onClick={() => setViewMode('week')}
            >
              Week
            </button>
            <button 
              className={`view-btn ${viewMode === 'month' ? 'active' : ''}`}
              onClick={() => setViewMode('month')}
            >
              <Calendar size={16} />
              Month
            </button>
          </div>
        <button 
          className="voice-btn"
          title="Voice commands"
        >
          <Mic size={20} />
        </button>
        <button 
          className="add-habit-btn"
          onClick={() => setShowAddForm(true)}
        >
          <Plus size={20} />
          Add Habit
        </button>
        </div>
      </div>

      {showAddForm && (
        <div className="add-habit-form">
          <form onSubmit={handleAddHabit}>
            <input
              type="text"
              placeholder="Enter habit name"
              value={newHabitName}
              onChange={(e) => setNewHabitName(e.target.value)}
              autoFocus
            />
            <div className="form-actions">
              <button type="submit">Add</button>
              <button 
                type="button" 
                onClick={() => {
                  setShowAddForm(false);
                  setNewHabitName('');
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="habits-container">
        {viewMode === 'month' && (
          <div className="month-navigation">
            <button className="nav-btn" onClick={() => navigateMonth(-1)}>
              <ChevronLeft size={20} />
            </button>
            <h2>
              {currentMonth.toLocaleDateString('en-US', { 
                month: 'long', 
                year: 'numeric' 
              })}
            </h2>
            <button className="nav-btn" onClick={() => navigateMonth(1)}>
              <ChevronRight size={20} />
            </button>
          </div>
        )}

        {viewMode === 'week' ? (
          <div className="habits-grid">
            <div className="date-headers">
              <div className="habit-name-header">Habits</div>
              {dateRange.map(date => (
                <div key={date} className="date-header">
                  {formatDateLabel(date)}
                </div>
              ))}
            </div>

            {Object.entries(habits).map(([habitName, habitData]) => (
              <div key={habitName} className="habit-row">
                <div 
                  className="habit-name"
                  style={{ borderLeft: `4px solid ${habitData.color}` }}
                >
                  <span>{habitName}</span>
                  <div className="habit-actions">
                    <button className="habit-action-btn">
                      <Palette size={16} />
                    </button>
                    <button className="habit-action-btn">
                      <Edit2 size={16} />
                    </button>
                    <button className="habit-action-btn delete">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                
                {dateRange.map(date => {
                  const today = new Date().toISOString().split('T')[0];
                  const isFutureDate = date > today;
                  const isCompleted = habitData.dates[date] || false;
                  return (
                    <div 
                      key={date} 
                      className={`habit-date ${isCompleted ? 'completed' : ''} ${isFutureDate ? 'future' : ''}`}
                      onClick={() => !isFutureDate && handleToggleHabit(habitName, date)}
                      style={{ cursor: isFutureDate ? 'not-allowed' : 'pointer' }}
                    >
                      <div 
                        className="habit-checkbox"
                        style={{ 
                          backgroundColor: isCompleted ? habitData.color : 'transparent',
                          opacity: isFutureDate ? 0.5 : 1
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        ) : (
          <div className="month-view">
            {Object.entries(habits).map(([habitName, habitData]) => (
              <div key={habitName} className="habit-calendar-container">
                <div className="habit-title">
                  <span style={{ color: habitData.color }}>●</span>
                  <h3>{habitName}</h3>
                </div>
                
                <div className="calendar-grid">
                  <div className="calendar-header">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                      <div key={day} className="day-header">{day}</div>
                    ))}
                  </div>
                  
                  <div className="calendar-body">
                    {monthDates.map((date, index) => {
                      const today = new Date().toISOString().split('T')[0];
                      const isFutureDate = date && date > today;
                      const isCompleted = date && habitData.dates[date] || false;
                      const isToday = date === today;
                      
                      return (
                        <div 
                          key={index} 
                          className={`calendar-cell ${!date ? 'empty' : ''} ${isToday ? 'today' : ''} ${isFutureDate ? 'future' : ''} ${isCompleted ? 'completed' : ''}`}
                          onClick={() => date && !isFutureDate && handleToggleHabit(habitName, date)}
                        >
                          {date ? (
                            <>
                              <span className="date-number">{new Date(date).getDate()}</span>
                              <div 
                                className={`habit-indicator ${isCompleted ? 'done' : ''}`}
                                style={{
                                  backgroundColor: isCompleted ? habitData.color : 'transparent',
                                  borderColor: habitData.color
                                }}
                              />
                            </>
                          ) : (
                            <span className="date-number">&nbsp;</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {Object.keys(habits).length === 0 && (
          <div className="empty-state">
            <h2>No habits yet</h2>
            <p>Start building your daily habits by adding your first one!</p>
            <button 
              className="add-first-habit-btn"
              onClick={() => setShowAddForm(true)}
            >
              <Plus size={20} />
              Add Your First Habit
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default HabitsPage;
