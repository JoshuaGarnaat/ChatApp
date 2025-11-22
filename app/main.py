import sqlite3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

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

# Routes

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            # (username: message)
            if ":" in data:
                username, content = data.split(":", 1)
                print(username, content)

            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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