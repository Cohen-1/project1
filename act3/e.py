import sqlite3
import os

DB_PATH = 'forum.db'
print("Reading from DB:", os.path.abspath(DB_PATH))

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT email, role FROM users ORDER BY id DESC LIMIT 10")
print(c.fetchall())
conn.close()
