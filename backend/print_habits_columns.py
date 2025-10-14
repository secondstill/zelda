import sqlite3

DB_FILE = 'habits.db'

def print_habits_columns():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(habits)")
    columns = cursor.fetchall()
    print("Current columns in 'habits' table:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    print_habits_columns()
