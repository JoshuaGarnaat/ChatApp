from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import sqlite3, re, time

app = FastAPI()

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

manager = ConnectionManager()

# Helper functions

def validate_username(username: str):
    if not re.match(r"^[A-Za-z0-9_]+$", username): # Check for special characters
        raise HTTPException(400, "Username invalid")

def validate_password(password: str):
    if not re.match(r"^[A-Za-z0-9_]+$", password): # Check for special characters
        raise HTTPException(400, "Password invalid")

# Schemas

class RegisterReq(BaseModel):
    username: str = Field(..., min_length=5, max_length=20) # Set length
    password: str = Field(..., min_length=8, max_length=128) # Set length

# Routes

@app.post("/register")
def register(req: RegisterReq): # Handle registration
    username = req.username
    password = req.password
    
    # Validate values server-side
    validate_username(username)
    validate_password(password)

    try:
        conn = sqlite3.connect("data/chat.db")
        query = "INSERT INTO users (username, password, time) VALUES (?, ?, ?)"
        # Save username, password and time of registration
        params = (username, password, int(time.time()))
        conn.execute(query, params)
        conn.commit()
        conn.close()
        return {"status": "ok"}
    
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Username already exists")

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