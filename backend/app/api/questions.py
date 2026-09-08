from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas import QuestionCreate, QuestionResponse, QuestionUpdate, CategoryCreate, CategoryResponse
from app.services.crud_service import QuestionService, CategoryService

router = APIRouter(prefix="/api/questions", tags=["Questions"])


@router.get("", response_model=List[QuestionResponse])
async def get_questions(
    db: AsyncSession = Depends(get_db),
    category_id: Optional[int] = Query(None),
    difficulty: Optional[str] = Query(None)
):
    questions = await QuestionService.get_all(db, category_id=category_id, difficulty=difficulty)
    return questions


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)):
    question = await QuestionService.get_by_id(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return question


@router.post("", response_model=QuestionResponse, status_code=201)
async def create_question(question: QuestionCreate, db: AsyncSession = Depends(get_db)):
    return await QuestionService.create(db, question)


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(question_id: int, question_update: QuestionUpdate, db: AsyncSession = Depends(get_db)):
    question = await QuestionService.update(db, question_id, question_update)
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return question


@router.delete("/{question_id}")
async def delete_question(question_id: int, db: AsyncSession = Depends(get_db)):
    success = await QuestionService.delete(db, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return {"message": "Вопрос успешно удален"}


# Category endpoints
@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService.get_all(db)


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    return await CategoryService.create(db, category)


@router.delete("/categories/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    success = await CategoryService.delete(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return {"message": "Категория успешно удалена"}
