from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, BigInteger, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={"timeout": 10}
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _ensure_system_settings_columns(sync_conn):
            columns = {col["name"] for col in inspect(sync_conn).get_columns("system_settings")}
            if "subscription_required" not in columns:
                sync_conn.execute(
                    text("ALTER TABLE system_settings ADD COLUMN subscription_required BOOLEAN DEFAULT 1")
                )

        await conn.run_sync(_ensure_system_settings_columns)


class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    system_status = Column(String, default="active")  # active / maintenance
    min_passing_score = Column(Integer, default=20)
    subscription_required = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String)
    phone_number = Column(String, unique=True)
    is_verified = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    applications = relationship("Application", back_populates="user")


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    role = Column(String, nullable=False)  # super_admin / good_admin / admin
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Personal info
    birth_date = Column(String)
    region = Column(String)
    district = Column(String)
    mahalla = Column(String)
    work_start_date = Column(String)
    experience_years = Column(Float)
    
    # Professional flags
    lang_certs = Column(String)  # comma-separated
    namunali_winner = Column(Boolean, default=False)
    top100_winner = Column(Boolean, default=False)
    initiative_respublika = Column(Boolean, default=False)
    initiative_hudud = Column(Boolean, default=False)
    initiative_tuman = Column(Boolean, default=False)
    additional_achievements = Column(Text)
    state_award = Column(Boolean, default=False)
    argos_status = Column(Boolean, default=False)
    social_telegram = Column(String)
    social_facebook = Column(String)
    social_instagram = Column(String)
    mega_projects = Column(String)  # comma-separated
    
    # Status
    current_stage = Column(Integer, default=1)  # 1 or 2
    final_status = Column(String, default="pending")  
    # pending / stage1_passed / stage1_rejected / interview_scheduled / accepted / reserve / rejected
    
    submitted_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="applications")
    documents = relationship("Document", back_populates="application")
    score = relationship("Score", back_populates="application", uselist=False)
    interview = relationship("Interview", back_populates="application", uselist=False)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    file_type = Column(String)  # essay, obyektivka, diploma, sertifikat, argos, award, initiative
    file_path = Column(String)
    file_name = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    application = relationship("Application", back_populates="documents")


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    experience_score = Column(Integer, default=0)  # 0-10
    results_score = Column(Integer, default=0)     # 0-20
    motivation_score = Column(Integer, default=0)  # 0-10
    essay_score = Column(Integer, default=0)       # 0-20
    total_score = Column(Integer, default=0)
    comment = Column(Text)
    status = Column(String)  # passed / rejected
    scored_at = Column(DateTime, default=datetime.utcnow)
    application = relationship("Application", back_populates="score")


class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    interview_date = Column(String)
    interview_time = Column(String)
    location = Column(String)
    status = Column(String, default="scheduled")  # scheduled / accepted / reserve / rejected
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    application = relationship("Application", back_populates="interview")


class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    action = Column(String)
    target_id = Column(Integer)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserDraft(Base):
    __tablename__ = "user_drafts"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    state_name = Column(String, nullable=False)
    state_data = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReminderLog(Base):
    __tablename__ = "reminder_logs"
    id = Column(Integer, primary_key=True)
    reminder_key = Column(String, unique=True, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    reminder_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
