import sqlite3
import pandas as pd

conn = sqlite3.connect('backend/talksense.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

try:
    cursor.execute('SELECT id, mode, duration, audio_file_path FROM sessions')
    print(cursor.fetchall())
except Exception as e:
    print(e)
    print(e)
