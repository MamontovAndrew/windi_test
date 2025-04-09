from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Enum, Table, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime
import enum

Base = declarative_base()

class ChatType(str, enum.Enum):
    private = "private"
    group = "group"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    messages = relationship("Message", back_populates="sender")

association_table = Table(
    "user_group", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("group_id", Integer, ForeignKey("groups.id"))
)

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    type = Column(Enum(ChatType), default=ChatType.private)

    messages = relationship("Message", back_populates="chat")

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"))
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)

    creator = relationship("User")
    participants = relationship("User", secondary=association_table, lazy="selectin")
    chat = relationship("Chat")

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("dedup_key", name="uq_message_dedup_key"),)

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    read = Column(Boolean, default=False)
    dedup_key = Column(String, nullable=False)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")
