from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict
import sqlite3, json, secrets, re, time

STATUS_OK = {"status": "ok"}
NON_EXISTENT_USERNAME = "Username does not exist"

TOKEN_EXPIRATION_MINUTES = 60

# WebSocket Manager

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    # Accept and add the websocket connection
    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    # Disconnect and close a specific websocket connection 
    def disconnect(self, user_id: int):
        ws = self.active_connections.get(user_id)
        if ws:
            del ws

    # Send a message to a specific user from a sender
    async def send_message_to_user(self, sender_id: int, user_id: int, message: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json({"sender": sender_id, "message": message})

    # Send info to a user
    async def send_info_to_user(self, user_id: int, info_msg: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json({"info": info_msg})

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

    if row is None:
        return None
    return row[0]

def get_id_from_user(username: str):
    with db_connect() as conn:
        cur = conn.cursor()
        # Get id from users with username
        cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )
        row = cur.fetchone()

    if row is None:
        return None
    return row[0]
 
# Schemas

class AuthReq(BaseModel):
    username: str = Field(..., min_length=5, max_length=20) # Set length
    password: str = Field(..., min_length=8, max_length=128) # Set length

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
        print(e)
        raise HTTPException(500, "Database Error")
    
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
        raise HTTPException(500, "Database Error")
    
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
        raise HTTPException(500, "Database Error")

    return {"token": token, "expires_at": expires_at}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str): # Handle websocket
    user_id = get_user_from_token(token)
    if not user_id:
        await websocket.close()
        return
    
    # Register connection
    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            receiver = data.get("receiver")
            msg = data.get("message")
            
            # Validate values server-side
            validate_username(receiver)

            # Get id from username
            receiver_id = get_id_from_user(receiver)
            if receiver_id is None:
                # Inform the client of incorrect receiver username
                await manager.send_info_to_user(user_id, NON_EXISTENT_USERNAME)
            else:
                # Send the message
                await manager.send_message_to_user(user_id, receiver_id, msg)

    except WebSocketDisconnect:
        manager.disconnect(user_id)

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
app.mount("/", NoCacheStaticFiles(directory="static", html=True), name="static")

# Start server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)