import sqlite3

conn = sqlite3.connect('habits.db')
cursor = conn.cursor()

# Delete the malformed habit
cursor.execute("DELETE FROM habits WHERE name = ? AND user_id = ?", ('add a habbit to drink water', 3))
print(f'Deleted {cursor.rowcount} malformed habits')

# Also clean up any related entries
cursor.execute("DELETE FROM habit_entries WHERE habit_id NOT IN (SELECT id FROM habits)")  
print(f'Cleaned up {cursor.rowcount} orphaned entries')

conn.commit()
conn.close()
print('Database cleanup completed!')
