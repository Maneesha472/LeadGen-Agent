import sqlite3
import os

db_path = os.path.join('backend', 'leads.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('PRAGMA table_info(users)')
cols = [row[1] for row in cur.fetchall()]
print('Current columns:', cols)

if 'groq_api_key' not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN groq_api_key TEXT DEFAULT ''")
    conn.commit()
    print('Added groq_api_key column successfully.')
else:
    print('groq_api_key column already exists.')

conn.close()
print('Database migration complete.')
