from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from database import engine, Base
from routers import auth, users, chats, messages, websocket, calls
from routers.global_ws import router as global_ws_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MyNet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(calls.router, prefix="/ws", tags=["calls"])
app.include_router(global_ws_router, prefix="/ws", tags=["global"])

@app.get("/")
def root():
    return FileResponse("index.html")

@app.get("/call")
def call_page():
    return FileResponse("call.html")
