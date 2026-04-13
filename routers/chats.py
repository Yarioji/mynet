from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.ChatOut, status_code=201)
def create_chat(
    data: schemas.ChatCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Для личного чата — проверяем, нет ли уже такого
    if not data.is_group and len(data.member_ids) == 1:
        other_id = data.member_ids[0]
        # Ищем существующий личный чат между двумя пользователями
        existing = (
            db.query(models.Chat)
            .filter(models.Chat.is_group == False)
            .join(models.chat_members)
            .filter(models.chat_members.c.user_id == current_user.id)
            .all()
        )
        for chat in existing:
            member_ids = [m.id for m in chat.members]
            if other_id in member_ids and len(member_ids) == 2:
                return chat

    # Собираем участников
    members = [current_user]
    for uid in data.member_ids:
        user = db.query(models.User).filter(models.User.id == uid).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"Пользователь {uid} не найден")
        members.append(user)

    chat = models.Chat(
        name=data.name,
        is_group=data.is_group,
        members=members
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/", response_model=List[schemas.ChatOut])
def get_my_chats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return current_user.chats


@router.get("/{chat_id}", response_model=schemas.ChatOut)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if current_user not in chat.members:
        raise HTTPException(status_code=403, detail="Нет доступа к этому чату")
    return chat
