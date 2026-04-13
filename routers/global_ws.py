from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from jose import jwt, JWTError
from auth_utils import SECRET_KEY, ALGORITHM
import models, json
from typing import Dict

router = APIRouter()


class GlobalManager:
    """Глобальные соединения — одно на пользователя."""

    def __init__(self):
        # user_id -> WebSocket
        self.connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.connections[user_id] = ws

    def disconnect(self, user_id: int):
        self.connections.pop(user_id, None)

    async def send(self, user_id: int, data: dict):
        ws = self.connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data, ensure_ascii=False, default=str))
            except Exception:
                self.disconnect(user_id)

    async def send_to_chat_members(self, chat, exclude_user_id: int, data: dict, db: Session):
        """Отправить всем участникам чата кроме отправителя."""
        for member in chat.members:
            if member.id != exclude_user_id:
                await self.send(member.id, data)


global_manager = GlobalManager()


def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return db.query(models.User).filter(models.User.id == user_id).first()
    except (JWTError, ValueError):
        return None


@router.websocket("/global")
async def websocket_global(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    user = get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001)
        return

    await global_manager.connect(user.id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "call_invite":
                chat_id = data.get("chat_id")
                if not chat_id:
                    continue
                chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
                if not chat or user not in chat.members:
                    continue

                await global_manager.send_to_chat_members(chat, user.id, {
                    "type": "call_invite",
                    "caller_id": user.id,
                    "caller_name": user.display_name or user.username,
                    "call_type": data.get("call_type", "audio"),
                    "chat_id": chat_id
                }, db)

            elif data.get("type") == "call_cancel":
                chat_id = data.get("chat_id")
                if not chat_id:
                    continue
                chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
                if not chat or user not in chat.members:
                    continue

                await global_manager.send_to_chat_members(chat, user.id, {
                    "type": "call_cancel",
                    "caller_id": user.id,
                }, db)

    except WebSocketDisconnect:
        global_manager.disconnect(user.id)
