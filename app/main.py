from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import sqlite3, secrets, re, time

STATUS_OK = {"status": "ok"}

TOKEN_EXPIRATION_MINUTES = 60

# WebSocket Manager

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("Connected:", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

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