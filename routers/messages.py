from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth_utils import get_current_user
import models, schemas

router = APIRouter()


@router.get("/{chat_id}", response_model=List[schemas.MessageOut])
def get_messages(
    chat_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if current_user not in chat.members:
        raise HTTPException(status_code=403, detail="Нет доступа")

    messages = (
        db.query(models.Message)
        .filter(models.Message.chat_id == chat_id)
        .order_by(models.Message.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


@router.post("/{chat_id}", response_model=schemas.MessageOut, status_code=201)
def send_message(
    chat_id: int,
    data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if current_user not in chat.members:
        raise HTTPException(status_code=403, detail="Нет доступа")

    msg = models.Message(
        content=data.content,
        chat_id=chat_id,
        sender_id=current_user.id
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.post("/{chat_id}/read")
def mark_as_read(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db.query(models.Message).filter(
        models.Message.chat_id == chat_id,
        models.Message.sender_id != current_user.id,
        models.Message.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "Прочитано"}
