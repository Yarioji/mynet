"""
WebRTC сигнальный сервер.
Обменивается SDP offer/answer и ICE кандидатами между участниками звонка.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from auth_utils import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
import models, json
from typing import Dict, Tuple

router = APIRouter()


class CallManager:
    def __init__(self):
        # room_id -> {user_id: websocket}
        self.rooms: Dict[str, Dict[int, WebSocket]] = {}

    def get_room_id(self, chat_id: int) -> str:
        return f"call_{chat_id}"

    async def join(self, room_id: str, user_id: int, ws: WebSocket):
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][user_id] = ws

    def leave(self, room_id: str, user_id: int):
        if room_id in self.rooms:
            self.rooms[room_id].pop(user_id, None)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    def get_peers(self, room_id: str, exclude_user_id: int) -> list[Tuple[int, WebSocket]]:
        if room_id not in self.rooms:
            return []
        return [(uid, ws) for uid, ws in self.rooms[room_id].items() if uid != exclude_user_id]

    async def send_to(self, ws: WebSocket, data: dict):
        try:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

    async def broadcast(self, room_id: str, data: dict, exclude_user_id: int):
        for _, ws in self.get_peers(room_id, exclude_user_id):
            await self.send_to(ws, data)


call_manager = CallManager()


def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return db.query(models.User).filter(models.User.id == user_id).first()
    except JWTError:
        return None


@router.websocket("/call/{chat_id}")
async def websocket_call(
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

    await websocket.accept()
    room_id = call_manager.get_room_id(chat_id)
    peers_before = call_manager.get_peers(room_id, user.id)

    await call_manager.join(room_id, user.id, websocket)

    # Сообщаем новому участнику сколько уже в комнате
    await call_manager.send_to(websocket, {
        "type": "joined",
        "user_id": user.id,
        "peers": [uid for uid, _ in peers_before]
    })

    # Уведомляем остальных о новом участнике
    await call_manager.broadcast(room_id, {
        "type": "peer_joined",
        "user_id": user.id,
        "username": user.display_name or user.username
    }, exclude_user_id=user.id)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            # Все сигнальные сообщения — пересылаем нужному peer (или всем)
            if msg_type in ("offer", "answer", "ice-candidate", "screen-share-start", "screen-share-stop"):
                target_id = data.get("target_id")
                payload = {**data, "from_id": user.id, "from_name": user.display_name or user.username}

                if target_id:
                    # Адресное сообщение
                    peers = call_manager.get_peers(room_id, user.id)
                    for uid, ws in peers:
                        if uid == target_id:
                            await call_manager.send_to(ws, payload)
                            break
                else:
                    # Широковещательное
                    await call_manager.broadcast(room_id, payload, exclude_user_id=user.id)

            elif msg_type == "hang_up":
                await call_manager.broadcast(room_id, {
                    "type": "peer_left",
                    "user_id": user.id
                }, exclude_user_id=user.id)
                break

    except WebSocketDisconnect:
        pass
    finally:
        call_manager.leave(room_id, user.id)
        await call_manager.broadcast(room_id, {
            "type": "peer_left",
            "user_id": user.id
        }, exclude_user_id=user.id)
