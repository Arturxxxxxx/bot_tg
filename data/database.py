import sqlite3

conn = sqlite3.connect("data.db")
conn.execute("PRAGMA foreign_keys = ON;")  # Включаем внешние ключи
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS portions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    company_name TEXT,
    week TEXT,
    day TEXT,
    time TEXT,
    portion INTEGER,
    created_at TEXT
)
''')
cursor.execute("CREATE INDEX IF NOT EXISTS idx_portions_user_id ON portions(user_id);")

cursor.execute('''
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    created_at TEXT
)
''')
cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);")

cursor.execute('''
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_company (
    user_id INTEGER PRIMARY KEY,
    company_id INTEGER,
    FOREIGN KEY(company_id) REFERENCES companies(id)
)
''')

conn.commit()
