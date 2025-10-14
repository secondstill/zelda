import sqlite3

DB_FILE = 'habits.db'

# Migration script: add 'id' column to 'habits' table if missing

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def migrate_habits_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if not column_exists(cursor, 'habits', 'id'):
        print("Migrating 'habits' table: adding 'id' column...")
        # Rename old table
        cursor.execute('ALTER TABLE habits RENAME TO habits_old')
        # Create new table with 'id' column
        cursor.execute('''
            CREATE TABLE habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#2ecc40',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        ''')
        # Copy data
        cursor.execute('''
            INSERT INTO habits (user_id, name, color, created_at)
            SELECT user_id, name, color, created_at FROM habits_old
        ''')
        # Drop old table
        cursor.execute('DROP TABLE habits_old')
        conn.commit()
        print("Migration complete.")
    else:
        print("No migration needed. 'id' column already exists.")
    conn.close()

if __name__ == '__main__':
    migrate_habits_table()
