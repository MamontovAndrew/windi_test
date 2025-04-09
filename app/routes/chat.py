import json
import hashlib
import datetime
from typing import List
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.dependencies import get_current_user, get_db
from app.models import Message, Chat, Group, User
from app.schemas import MessageCreate, MessageOut, GroupCreate, GroupOut, ChatType
from app.connection_manager import manager

router = APIRouter()

@router.get("/history/{chat_id}", response_model=List[MessageOut])
async def get_history(chat_id: int, limit: int = Query(100), offset: int = Query(0), db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    result = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.timestamp).offset(offset).limit(limit)
    )
    messages = result.scalars().all()
    return messages

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...), chat_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    from app.utils import decode_access_token
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        await websocket.close(code=1008)
        return
    user_id = int(payload["sub"])
    
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            text = msg_data.get("text")
            if not text:
                continue

            dedup_source = f"{user_id}_{chat_id}_{text}"
            dedup_key = hashlib.md5(dedup_source.encode()).hexdigest()

            chat_lock = manager.get_chat_lock(chat_id)
            async with chat_lock:
                result = await db.execute(select(Message).where(Message.dedup_key == dedup_key))
                existing_message = result.scalars().first()
                if existing_message:
                    continue

                new_message = Message(
                    chat_id=chat_id,
                    sender_id=user_id,
                    text=text,
                    dedup_key=dedup_key,
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(new_message)
                try:
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    raise HTTPException(status_code=500, detail="Error saving message")
                await db.refresh(new_message)

            await manager.send_personal_message(json.dumps({
                "id": new_message.id,
                "chat_id": new_message.chat_id,
                "sender_id": new_message.sender_id,
                "text": new_message.text,
                "timestamp": new_message.timestamp.isoformat(),
                "read": new_message.read
            }), user_id)
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


@router.post("/message", response_model=MessageOut)
async def create_message(message: MessageCreate, 
                         current_user = Depends(get_current_user), 
                         db: AsyncSession = Depends(get_db)):
    chat_obj = None

    if message.chat_id is not None:
        result = await db.execute(select(Chat).where(Chat.id == message.chat_id))
        chat_obj = result.scalars().first()
        if chat_obj is None and message.recipient_id:
            private_chat_name = f"private:{min(current_user.id, message.recipient_id)}:{max(current_user.id, message.recipient_id)}"
            chat_obj = Chat(name=private_chat_name, type=ChatType.private)
            db.add(chat_obj)
            await db.commit()
            await db.refresh(chat_obj)
        elif chat_obj is None:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        if not message.recipient_id:
            raise HTTPException(status_code=400, detail="Either chat_id or recipient_id must be provided")
        private_chat_name = f"private:{min(current_user.id, message.recipient_id)}:{max(current_user.id, message.recipient_id)}"
        result = await db.execute(
            select(Chat).where(Chat.name == private_chat_name, Chat.type == ChatType.private)
        )
        chat_obj = result.scalars().first()
        if chat_obj is None:
            chat_obj = Chat(name=private_chat_name, type=ChatType.private)
            db.add(chat_obj)
            await db.commit()
            await db.refresh(chat_obj)

    final_chat_id = chat_obj.id

    dedup_source = f"{current_user.id}_{final_chat_id}_{message.text}"
    dedup_key = hashlib.md5(dedup_source.encode()).hexdigest()

    result = await db.execute(select(Message).where(Message.dedup_key == dedup_key))
    existing_message = result.scalars().first()
    if existing_message:
        raise HTTPException(status_code=400, detail="Message already exists")

    new_message = Message(
        chat_id=final_chat_id,
        sender_id=current_user.id,
        text=message.text,
        dedup_key=dedup_key,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    return new_message



@router.post("/group", response_model=GroupOut)
async def create_group(group: GroupCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_chat = Chat(name=group.name, type=ChatType.group)
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    
    new_group = Group(name=group.name, creator_id=current_user.id, chat_id=new_chat.id)
    result = await db.execute(select(User).where(User.id.in_(group.participant_ids)))
    participants = result.scalars().all()
    if current_user not in participants:
        participants.append(current_user)
    new_group.participants = participants
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
    await db.refresh(new_group, attribute_names=["participants"])
    
    return GroupOut(
        id=new_group.id,
        name=new_group.name,
        creator_id=new_group.creator_id,
        chat_id=new_group.chat_id,
        participant_ids=[user.id for user in new_group.participants]
    )




@router.patch("/message/{message_id}/read", response_model=MessageOut)
async def mark_message_read(message_id: int, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.id == message_id))
    message_obj = result.scalars().first()
    if not message_obj:
        raise HTTPException(status_code=404, detail="Message not found")
    message_obj.read = True
    await db.commit()
    await db.refresh(message_obj)
    await manager.send_personal_message(json.dumps({
        "id": message_obj.id,
        "chat_id": message_obj.chat_id,
        "sender_id": message_obj.sender_id,
        "text": message_obj.text,
        "timestamp": message_obj.timestamp.isoformat(),
        "read": message_obj.read,
        "notification": "message_read"
    }), message_obj.sender_id)
    return message_obj
