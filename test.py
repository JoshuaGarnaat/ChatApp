import sqlite3
conn = sqlite3.connect("data/chat.db")
query_users = "SELECT * FROM users;"
out_users = conn.execute(query_users).fetchall()
query_messages = "SELECT * FROM messages;"
out_messages = conn.execute(query_messages).fetchall()
query_sessions = "SELECT * FROM sessions;"
out_sessions = conn.execute(query_sessions).fetchall()
query_groups = "SELECT * FROM groups;"
out_groups = conn.execute(query_groups).fetchall()
query_group_members = "SELECT * FROM group_members;"
out_group_members = conn.execute(query_group_members).fetchall()
query_group_messages = "SELECT * FROM group_messages;"
out_group_messages = conn.execute(query_group_messages).fetchall()
conn.close()
print(out_users)
print(out_messages)
print(out_sessions)
print(out_groups)
print(out_group_members)
print(out_group_messages)