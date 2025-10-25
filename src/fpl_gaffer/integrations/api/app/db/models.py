# from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, func
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.dialects.postgresql import UUID
# import uuid
# import datetime as dt
# from datetime import datetime
#
# Base = declarative_base()
#
#
# class User(Base):
#     __tablename__ = "users"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     email = Column(String(255), unique=True, nullable=True)
#     phone = Column(String(20), unique=True, nullable=True)
#     created_at = Column(DateTime, default=lambda: datetime.now(dt.timezone.utc))
#     updated_at = Column(
#         DateTime,
#         default=lambda: datetime.now(dt.timezone.utc),
#         onupdate=lambda: datetime.now(dt.timezone.utc)
#     )
#
#
# class Request(Base):
#     __tablename__ = "requests"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
#     route = Column(String(255))
#     prompt = Column(Text)
#     response = Column(Text, nullable=True)
#     tokens_in = Column(Integer, default=0)
#     tokens_out = Column(Integer, default=0)
#     cost_usd = Column(Float, default=0.0)
#     latency_ms = Column(Float, default=0.0)
#     model = Column(String(100))
#     status = Column(String(20), default="ok")  # ok, error, timeout
#     tool_used = Column(String(255), nullable=True)
#     created_at = Column(DateTime, default=lambda: datetime.now(dt.timezone.utc), index=True)
#
#
# class ToolUsage(Base):
#     __tablename__ = "tools_usage"
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), nullable=True)
#     tool_name = Column(String(255))
#     duration_ms = Column(Float)
#     created_at = Column(DateTime, default=lambda: datetime.now(dt.timezone.utc))
#
#
# class Session(Base):
#     __tablename__ = "sessions"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
#     token = Column(String(500), unique=True)
#     expires_at = Column(DateTime)
#     created_at = Column(DateTime, default=lambda: datetime.now(dt.timezone.utc))
