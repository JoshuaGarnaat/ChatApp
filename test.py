import sqlite3
conn = sqlite3.connect("data/chat.db")
query_users = "SELECT * FROM users;"
out_users = conn.execute(query_users).fetchall()
query_messages = "SELECT * FROM messages;"
out_messages = conn.execute(query_messages).fetchall()
query_sessions = "SELECT * FROM sessions;"
out_sessions = conn.execute(query_sessions).fetchall()
conn.close()
print(out_users)
print(out_messages)
print(out_sessions)