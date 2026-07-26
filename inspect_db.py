import sqlite3

db_path = 'backend/leads.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]
print('Tables:', tables)

for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [(row[1], row[2]) for row in cur.fetchall()]
    print(f'\n{t} columns:', cols)

conn.close()
