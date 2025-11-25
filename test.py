import sqlite3
conn = sqlite3.connect("data/chat.db")
query = "SELECT * FROM users;"
out = conn.execute(query).fetchall()
conn.close()
print(out)