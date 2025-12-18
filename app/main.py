from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict
from enum import Enum
import sqlite3, logging, secrets, re, time

DEBUG = False

STATUS_OK = {"status": "ok"}
NON_EXISTENT_USERNAME = "Username does not exist"

SEND_MESSAGE = "SEND_MESSAGE"
CREATE_GROUP = "CREATE_GROUP"
JOIN_GROUP = "JOIN_GROUP"

TOKEN_EXPIRATION_MINUTES = 60

# WebSocket Manager

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}

    # Accept and add the websocket connection
    async def connect(self, user_id: int, token: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][token] = websocket
        
    # Disconnect and close a specific websocket connection 
    def disconnect(self, token: str, user_id: int):
        self.active_connections.get(user_id).pop(token)
    
    async def safe_send(self, user_id: int, data: dict):
        websockets = self.active_connections.get(user_id)
        dead = []
        for token, ws in websockets.items():
            try:
                await ws.send_json(data)
            except:
                dead.append(token)

        # Remove all dead connections
        for token in dead:
            websockets.pop(token, None)

    # Send a message to a specific user from a sender
    async def send_message_to_user(self, message_id: int, sender_id: int, receiver_id: int, msg: str, send_time: int):
        message_data = {
            "id": message_id,
            "type": "private",
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": msg,
            "time": send_time,
        }
        await self.safe_send(receiver_id, message_data)
        await self.safe_send(sender_id, message_data)

    # Send info to a user
    async def send_info_to_user(self, user_id: int, info_msg: str):
        data = {"info": info_msg}
        await self.safe_send(user_id, data)

# FastAPI app
app = FastAPI()

# Websocket manager
manager = ConnectionManager()

# Helper functions

def validate_username(username: str):
    if not re.match(r"^[A-Za-z0-9_]+$", username): # Check for special characters
        raise HTTPException(400, "Username invalid")

def validate_password(password: str):
    if not re.match(r"^[A-Za-z0-9_]+$", password): # Check for special characters
        raise HTTPException(400, "Password invalid")

def validate_groupname(groupname: str):
    if not re.match(r"^[A-Za-z0-9_ ]+$", groupname): # Check for special characters, but allow spaces
        raise HTTPException(400, "Groupname invalid")

# Core Functions

def db_connect():
    conn = sqlite3.connect("data/chat.db", timeout=10, check_same_thread=False)
    return conn

def get_user_from_token(token: str):
    with db_connect() as conn:
        cur = conn.cursor()
        # Get user_id from sessions with token
        cur.execute(
            "SELECT user_id FROM sessions WHERE token = ?",
            (token,)
        )
        row = cur.fetchone()
    return row[0] if row else None

def get_id_from_user(username: str):
    with db_connect() as conn:
        cur = conn.cursor()
        # Get id from users with username
        cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )
        row = cur.fetchone()
    return row[0] if row else None

def get_group_id(name: str):
    with db_connect() as conn:
        cur = conn.cursor()
        # Get id from groups with username
        cur.execute(
            "SELECT id FROM groups WHERE name = ?",
            (name,)
        )
        row = cur.fetchone()
    return row[0] if row else None

def user_is_in_group(user_id: int, group_id: int):
    with db_connect() as conn:
        cur = conn.cursor()
        # Get id from groups with username
        cur.execute(
            "SELECT 1 FROM group_members WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        )
        return cur.fetchone() is not None

def get_group_members(group_id: int):
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM group_members WHERE group_id = ?", (group_id,))
        return [row[0] for row in cur.fetchall()]
 
def add_member_to_group(user_id: int, group_id: int):
    with db_connect() as conn:
        cur = conn.cursor()
        # Add values to db
        cur.execute(
            "INSERT INTO group_members (group_id, user_id, added_at) VALUES (?, ?, ?)",
            (group_id, user_id, int(time.time()))
        )

# Schemas

class AuthReq(BaseModel):
    username: str = Field(..., min_length=5, max_length=20) # Set length
    password: str = Field(..., min_length=8, max_length=128) # Set length

class CreateGroupReq(BaseModel):
    token: str
    groupname: str = Field(..., min_length=1, max_length=64) # Set length

class JoinGroupReq(BaseModel):
    token: str
    groupToken: str

# Routes

@app.post("/register")
def register(req: AuthReq): # Handle registration
    username = req.username
    password = req.password
    
    # Validate values server-side
    validate_username(username)
    validate_password(password)

    try:
        with db_connect() as conn:
            cur = conn.cursor()
            # Add values to db
            cur.execute(
                "INSERT INTO users (username, password, time) VALUES (?, ?, ?)",
                (username, password, int(time.time()))
            )
    
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Username already exists")
    
    except sqlite3.Error as e:
        logging.error("Database Error Register")
        raise HTTPException(500, "Database Error Register")
    
    return STATUS_OK

@app.post("/login")
def login(req: AuthReq): # Handle registration
    username = req.username
    password = req.password
    
    # Validate values server-side
    validate_username(username)
    validate_password(password)

    try:
        with db_connect() as conn:
            cur = conn.cursor()
            # Check values in db
            cur.execute(
                "SELECT id FROM users WHERE username = ? AND password = ?",
                (username, password)
            )
            row = cur.fetchone()

    except sqlite3.Error:
        logging.error("Database Error Get Login")
        raise HTTPException(500, "Database Error Get Login")
    
    if row is None:
        raise HTTPException(401, "Invalid username or password")

    user_id = row[0]
    
    token = secrets.token_hex(16)
    created_at = int(time.time())
    expires_at = created_at + TOKEN_EXPIRATION_MINUTES * 60
    
    try:
        with db_connect() as conn:
            cur = conn.cursor()
            # Add values to db
            cur.execute(
                "INSERT INTO sessions (user_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (user_id, token, created_at, expires_at)
            )

    except sqlite3.Error:
        raise HTTPException(500, "Database Error Set Login")

    return {"token": token, "expires_at": expires_at}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str): # Handle websocket
    sender_id = get_user_from_token(token)
    if not sender_id:
        await websocket.close()
        return
    
    # Register connection
    await manager.connect(sender_id, token, websocket)

    try:
        while True:
            # Check if the correct format was sent
            data = None
            try:
                data = await websocket.receive_json()
            except Exception as e:
                logging.warning("Websocket receive json error")
                return
            
            # Check for None
            if data is None:
                logging.error("Data is None")
                return
            
            req_type = data.get("req_type")
            if req_type is None:
                logging.error("Request type is None")
                return
            
            # Send Message Request
            if req_type == SEND_MESSAGE:
                # Get values from data
                receiver = data.get("receiver")
                message = data.get("message")

                # Check for None
                if receiver is None:
                    logging.error("Message Receiver is None")
                    return
                if message is None:
                    logging.error("Message is None")
                    return
                
                # Validate values server-side
                validate_username(receiver)

                # Get id from username
                receiver_id = get_id_from_user(receiver)
                if receiver_id is None:
                    # Inform the client of incorrect receiver username
                    await manager.send_info_to_user(sender_id, NON_EXISTENT_USERNAME)
                else:
                    send_time = int(time.time())
                    try:
                        with db_connect() as conn:
                            cur = conn.cursor()
                            # Add values to db
                            cur.execute(
                                "INSERT INTO private_messages (sender_id, receiver_id, message, time) VALUES (?, ?, ?, ?)",
                                (sender_id, receiver_id, message, send_time)
                            )
                            message_id = cur.lastrowid

                    except sqlite3.Error as e:
                        logging.error(e)
                        raise HTTPException(500, "Database Error Send Message")

                    # Send the message
                    await manager.send_message_to_user(message_id, sender_id, receiver_id, message, send_time)

            # Create Group Request
            elif req_type == CREATE_GROUP:
                # Get values from data
                groupname = data.get("groupname")

                # Check for None
                if groupname is None:
                    logging.error("Groupname is None")
                    continue

                # Validate values server-side
                validate_groupname(groupname)

                created_time = int(time.time())
                try:
                    with db_connect() as conn:
                        cur = conn.cursor()
                        # Add values to db
                        cur.execute(
                            "INSERT INTO groups (groupname, created_at) VALUES (?, ?)",
                            (groupname, created_time)
                        )
                        group_id = cur.lastrowid
                    add_member_to_group(sender_id, group_id)
                
                except sqlite3.Error as e:
                    logging.error(e)
                    raise HTTPException(500, "Database Error Create Group")

                # Send token
                await manager.send_info_to_user(sender_id, group_id)

            elif req_type == JOIN_GROUP:
                # Get values from data
                grouptoken = data.get("grouptoken")

                # Check for None
                if grouptoken is None:
                    logging.error("Grouptoken is None")
                    continue
                group_id = grouptoken

                if user_is_in_group(sender_id, group_id):
                    await manager.send_info_to_user(sender_id, "Already in group")
                    continue

                try:
                    add_member_to_group(sender_id, group_id)
                except sqlite3.Error as e:
                    logging.error(e)
                    raise HTTPException(500, "Database Error Join Group")

                # Send confirmation
                await manager.send_info_to_user(sender_id, "Group joined")

    except WebSocketDisconnect:
        manager.disconnect(token, sender_id)

# Serve static files like index.html, script.js, etc.

# Do not cache static files, handy for development but it slows down loading the webpage
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers.update({
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        })
        return response
    
# Endpoint to serve static files
if DEBUG:
    app.mount("/", NoCacheStaticFiles(directory="static", html=True), name="static")
else:
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Start server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)