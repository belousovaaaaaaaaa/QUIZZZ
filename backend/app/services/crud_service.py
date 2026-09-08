from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from typing import List, Optional
from app.models import Question, Category, Quiz, GameResult, PlayerResult
from app.schemas import QuestionCreate, QuestionUpdate, CategoryCreate, QuizCreate, GameResultCreate


class QuestionService:
    @staticmethod
    async def get_all(db: AsyncSession, category_id: Optional[int] = None, difficulty: Optional[str] = None) -> List[Question]:
        query = select(Question)
        if category_id:
            query = query.where(Question.category_id == category_id)
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
        result = await db.execute(query.order_by(Question.created_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(db: AsyncSession, question_id: int) -> Optional[Question]:
        result = await db.execute(select(Question).where(Question.id == question_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(db: AsyncSession, question: QuestionCreate) -> Question:
        db_question = Question(**question.model_dump())
        db.add(db_question)
        await db.flush()
        await db.refresh(db_question)
        return db_question
    
    @staticmethod
    async def update(db: AsyncSession, question_id: int, question_update: QuestionUpdate) -> Optional[Question]:
        db_question = await QuestionService.get_by_id(db, question_id)
        if not db_question:
            return None
        update_data = question_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_question, field, value)
        await db.flush()
        await db.refresh(db_question)
        return db_question
    
    @staticmethod
    async def delete(db: AsyncSession, question_id: int) -> bool:
        db_question = await QuestionService.get_by_id(db, question_id)
        if not db_question:
            return False
        await db.delete(db_question)
        await db.flush()
        return True
    
    @staticmethod
    async def get_by_ids(db: AsyncSession, ids: List[int]) -> List[Question]:
        result = await db.execute(select(Question).where(Question.id.in_(ids)))
        return list(result.scalars().all())


class CategoryService:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Category]:
        result = await db.execute(select(Category).order_by(Category.name))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> Optional[Category]:
        result = await db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(db: AsyncSession, category: CategoryCreate) -> Category:
        db_category = Category(**category.model_dump())
        db.add(db_category)
        await db.flush()
        await db.refresh(db_category)
        return db_category
    
    @staticmethod
    async def delete(db: AsyncSession, category_id: int) -> bool:
        db_category = await CategoryService.get_by_id(db, category_id)
        if not db_category:
            return False
        await db.delete(db_category)
        await db.flush()
        return True


class QuizService:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Quiz]:
        result = await db.execute(select(Quiz).order_by(Quiz.created_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(db: AsyncSession, quiz_id: int) -> Optional[Quiz]:
        result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(db: AsyncSession, quiz: QuizCreate) -> Quiz:
        db_quiz = Quiz(**quiz.model_dump())
        db.add(db_quiz)
        await db.flush()
        await db.refresh(db_quiz)
        return db_quiz
    
    @staticmethod
    async def delete(db: AsyncSession, quiz_id: int) -> bool:
        db_quiz = await QuizService.get_by_id(db, quiz_id)
        if not db_quiz:
            return False
        await db.delete(db_quiz)
        await db.flush()
        return True


class GameResultService:
    @staticmethod
    async def get_by_room_id(db: AsyncSession, room_id: str) -> Optional[GameResult]:
        result = await db.execute(
            select(GameResult)
            .where(GameResult.room_id == room_id)
        )
        game_result = result.scalar_one_or_none()
        if game_result:
            # Load players
            await db.refresh(game_result)
        return game_result
    
    @staticmethod
    async def create_with_players(db: AsyncSession, room_id: str, quiz_title: str, 
                                   total_questions: int, players_data: List[dict]) -> GameResult:
        game_result = GameResult(
            room_id=room_id,
            quiz_title=quiz_title,
            total_questions=total_questions
        )
        db.add(game_result)
        await db.flush()
        await db.refresh(game_result)
        
        for idx, player in enumerate(sorted(players_data, key=lambda x: x['score'], reverse=True)):
            player_result = PlayerResult(
                game_result_id=game_result.id,
                name=player['name'],
                score=player['score'],
                answers=player.get('answers', []),
                rank=idx + 1
            )
            db.add(player_result)
        
        await db.flush()
        return game_result
