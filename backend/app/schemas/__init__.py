from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from datetime import datetime


# Category Schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Question Schemas
class QuestionBase(BaseModel):
    text: str
    question_type: str = Field(default="single", pattern="^(single|multiple|text)$")
    options: List[str] = []
    correct_answer: Any  # Union[List[int], str]
    image_url: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    category_id: Optional[int] = None


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    question_type: Optional[str] = Field(None, pattern="^(single|multiple|text)$")
    options: Optional[List[str]] = None
    correct_answer: Optional[Any] = None
    image_url: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    category_id: Optional[int] = None


class QuestionResponse(QuestionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[CategoryResponse] = None
    
    class Config:
        from_attributes = True


# Quiz Schemas
class QuizBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    question_ids: List[int] = []
    is_active: bool = True
    created_by: Optional[str] = None


class QuizCreate(QuizBase):
    pass


class QuizResponse(QuizBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Game Result Schemas
class PlayerResultBase(BaseModel):
    name: str
    score: int = 0
    answers: List[dict] = []
    rank: Optional[int] = None


class PlayerResultCreate(PlayerResultBase):
    game_result_id: int


class PlayerResultResponse(PlayerResultBase):
    id: int
    
    class Config:
        from_attributes = True


class GameResultBase(BaseModel):
    room_id: str
    quiz_title: str
    total_questions: int = 0


class GameResultCreate(GameResultBase):
    pass


class GameResultResponse(GameResultBase):
    id: int
    completed_at: datetime
    players: List[PlayerResultResponse] = []
    
    class Config:
        from_attributes = True
