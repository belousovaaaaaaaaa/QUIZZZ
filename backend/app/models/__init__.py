from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    questions = relationship("Question", back_populates="category", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    question_type = Column(String(20), default="single")  # single, multiple, text
    options = Column(JSON, default=list)  # ["Option A", "Option B", ...]
    correct_answer = Column(JSON, nullable=False)  # [1] for single/multiple, "text" for text type
    image_url = Column(String(500), nullable=True)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(20), default="medium")  # easy, medium, hard
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    category = relationship("Category", back_populates="questions")


class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    question_ids = Column(JSON, default=list)  # List of question IDs
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GameResult(Base):
    __tablename__ = "game_results"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(20), nullable=False, unique=True)
    quiz_title = Column(String(200), nullable=False)
    total_questions = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    players = relationship("PlayerResult", back_populates="game_result", cascade="all, delete-orphan")


class PlayerResult(Base):
    __tablename__ = "player_results"
    
    id = Column(Integer, primary_key=True, index=True)
    game_result_id = Column(Integer, ForeignKey("game_results.id"), nullable=False)
    name = Column(String(100), nullable=False)
    score = Column(Integer, default=0)
    answers = Column(JSON, default=list)  # [{questionId, userAnswer, isCorrect}]
    rank = Column(Integer, nullable=True)
    
    game_result = relationship("GameResult", back_populates="players")
