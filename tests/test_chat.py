import pytest
from app.models import User, Chat
from app.utils import get_password_hash, create_access_token
from datetime import timedelta

@pytest.mark.asyncio
async def test_history_endpoint(client, db_session):
    user = User(name="TestUser", email="test@example.com", hashed_password=get_password_hash("1234"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    chat = Chat(name="Test Chat", type="private")
    db_session.add(chat)
    await db_session.commit()
    await db_session.refresh(chat)

    token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=30))
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/chat/history/{chat.id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_message(client, db_session):
    user = User(
        name="MessageTester",
        email="msgtester@example.com",
        hashed_password=get_password_hash("password")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    chat = Chat(name="Test Chat 2", type="private")
    db_session.add(chat)
    await db_session.commit()
    await db_session.refresh(chat)
    
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=30))
    headers = {"Authorization": f"Bearer {token}"}
    
    message_payload = {"chat_id": chat.id, "text": "Hello via REST!"}
    response = await client.post("/chat/message", json=message_payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["chat_id"] == chat.id
    assert data["sender_id"] == user.id
    assert data["text"] == "Hello via REST!"
    assert isinstance(data["id"], int)
    assert data["read"] is False

@pytest.mark.asyncio
async def test_create_group_and_mark_message_read(client, db_session):
    creator = User(
        name="GroupCreator",
        email="groupcreator@example.com",
        hashed_password=get_password_hash("password")
    )
    participant = User(
        name="GroupParticipant",
        email="participant@example.com",
        hashed_password=get_password_hash("password")
    )
    db_session.add_all([creator, participant])
    await db_session.commit()
    await db_session.refresh(creator)
    await db_session.refresh(participant)
    
    token_creator = create_access_token(data={"sub": str(creator.id)}, expires_delta=timedelta(minutes=30))
    headers_creator = {"Authorization": f"Bearer {token_creator}"}
    
    group_payload = {
        "name": "Test Group",
        "participant_ids": [participant.id]
    }
    response_group = await client.post("/chat/group", json=group_payload, headers=headers_creator)
    assert response_group.status_code == 200, response_group.text
    group_data = response_group.json()
    assert group_data["name"] == "Test Group"
    assert "chat_id" in group_data
    assert creator.id in group_data["participant_ids"]
    assert participant.id in group_data["participant_ids"]
    
    chat = Chat(name="Group Chat", type="group")
    db_session.add(chat)
    await db_session.commit()
    await db_session.refresh(chat)
    
    token_participant = create_access_token(data={"sub": str(participant.id)}, expires_delta=timedelta(minutes=30))
    headers_participant = {"Authorization": f"Bearer {token_participant}"}
    msg_payload = {"chat_id": chat.id, "text": "Hello from participant"}
    response_msg = await client.post("/chat/message", json=msg_payload, headers=headers_participant)
    assert response_msg.status_code == 200, response_msg.text
    msg_data = response_msg.json()
    message_id = msg_data["id"]
    
    response_patch = await client.patch(f"/chat/message/{message_id}/read", headers=headers_creator)
    assert response_patch.status_code == 200, response_patch.text
    patched_data = response_patch.json()
    assert patched_data["read"] is True

@pytest.mark.asyncio
async def test_auto_create_private_chat(client, db_session):
    sender = User(name="Sender", email="sender@example.com", hashed_password=get_password_hash("password"))
    recipient = User(name="Recipient", email="recipient@example.com", hashed_password=get_password_hash("password"))
    db_session.add_all([sender, recipient])
    await db_session.commit()
    await db_session.refresh(sender)
    await db_session.refresh(recipient)

    token = create_access_token(data={"sub": str(sender.id)}, expires_delta=timedelta(minutes=30))
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"recipient_id": recipient.id, "text": "Hello, auto-created chat!"}
    response = await client.post("/chat/message", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["chat_id"] is not None

@pytest.mark.asyncio
async def test_create_group_and_mark_message_read(client, db_session):
    creator = User(
        name="GroupCreator",
        email="groupcreator@example.com",
        hashed_password=get_password_hash("password")
    )
    participant = User(
        name="GroupParticipant",
        email="participant@example.com",
        hashed_password=get_password_hash("password")
    )
    db_session.add_all([creator, participant])
    await db_session.commit()
    await db_session.refresh(creator)
    await db_session.refresh(participant)
    
    token_creator = create_access_token(data={"sub": str(creator.id)}, expires_delta=timedelta(minutes=30))
    headers_creator = {"Authorization": f"Bearer {token_creator}"}
    
    group_payload = {
        "name": "Test Group",
        "participant_ids": [participant.id]
    }
    response_group = await client.post("/chat/group", json=group_payload, headers=headers_creator)
    assert response_group.status_code == 200, response_group.text
    group_data = response_group.json()
    assert group_data["name"] == "Test Group"
    assert "chat_id" in group_data
    assert creator.id in group_data["participant_ids"]
    assert participant.id in group_data["participant_ids"]
    
    group_chat_id = group_data["chat_id"]
    token_participant = create_access_token(data={"sub": str(participant.id)}, expires_delta=timedelta(minutes=30))
    headers_participant = {"Authorization": f"Bearer {token_participant}"}
    msg_payload = {"chat_id": group_chat_id, "text": "Hello from participant in group"}
    response_msg = await client.post("/chat/message", json=msg_payload, headers=headers_participant)
    assert response_msg.status_code == 200, response_msg.text
    msg_data = response_msg.json()
    message_id = msg_data["id"]
    
    response_patch = await client.patch(f"/chat/message/{message_id}/read", headers=headers_creator)
    assert response_patch.status_code == 200, response_patch.text
    patched_data = response_patch.json()
    assert patched_data["read"] is True
