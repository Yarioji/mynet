from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, List
from database import get_db
from jose import jwt, JWTError
from auth_utils import SECRET_KEY, ALGORITHM
import models
import json

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[int, List[tuple]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        await websocket.accept()
        if chat_id not in self.rooms:
            self.rooms[chat_id] = []
        self.rooms[chat_id].append((websocket, user_id))

    def disconnect(self, websocket: WebSocket, chat_id: int):
        if chat_id in self.rooms:
            self.rooms[chat_id] = [
                (ws, uid) for ws, uid in self.rooms[chat_id] if ws != websocket
            ]

    async def broadcast(self, chat_id: int, message: dict, exclude_ws: WebSocket = None):
        if chat_id not in self.rooms:
            return
        dead = []
        for ws, uid in self.rooms[chat_id]:
            if ws == exclude_ws:
                continue
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False, default=str))
            except Exception:
                dead.append(ws)
        self.rooms[chat_id] = [
            (ws, uid) for ws, uid in self.rooms[chat_id] if ws not in dead
        ]


manager = ConnectionManager()


def get_user_from_token(token: str, db: Session) -> models.User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user_id = int(user_id)
        return db.query(models.User).filter(models.User.id == user_id).first()
    except (JWTError, ValueError):
        return None


@router.websocket("/chat/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001)
        return

    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat or user not in chat.members:
        await websocket.close(code=4003)
        return

    await manager.connect(websocket, chat_id, user.id)

    await manager.broadcast(chat_id, {
        "type": "user_online",
        "user_id": user.id,
        "username": user.username
    }, exclude_ws=websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue

                msg = models.Message(
                    content=content,
                    chat_id=chat_id,
                    sender_id=user.id
                )
                db.add(msg)
                db.commit()
                db.refresh(msg)

                await manager.broadcast(chat_id, {
                    "type": "message",
                    "id": msg.id,
                    "content": msg.content,
                    "chat_id": chat_id,
                    "sender_id": user.id,
                    "sender_username": user.username,
                    "sender_display_name": user.display_name,
                    "created_at": str(msg.created_at)
                })

            elif data.get("type") == "typing":
                await manager.broadcast(chat_id, {
                    "type": "typing",
                    "user_id": user.id,
                    "username": user.username
                }, exclude_ws=websocket)

            # Уведомление о входящем звонке
            elif data.get("type") == "call_invite":
                await manager.broadcast(chat_id, {
                    "type": "call_invite",
                    "caller_id": user.id,
                    "caller_name": user.display_name or user.username,
                    "call_type": data.get("call_type", "audio"),
                    "chat_id": chat_id
                }, exclude_ws=websocket)

            # Отмена звонка
            elif data.get("type") == "call_cancel":
                await manager.broadcast(chat_id, {
                    "type": "call_cancel",
                    "caller_id": user.id,
                }, exclude_ws=websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)
        await manager.broadcast(chat_id, {
            "type": "user_offline",
            "user_id": user.id,
            "username": user.username
        })
