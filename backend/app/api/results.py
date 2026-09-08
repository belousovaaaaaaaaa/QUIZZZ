from fastapi import APIRouter, HTTPException, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.crud_service import GameResultService
from typing import Annotated

router = APIRouter(prefix="/api/results", tags=["Results"])


@router.get("/{room_id}")
async def get_game_result(room_id: str, db: AsyncSession = Depends(get_db)):
    result = await GameResultService.get_by_room_id(db, room_id)
    if not result:
        raise HTTPException(status_code=404, detail="Результаты не найдены")
    return result


@router.get("/{room_id}/export")
async def export_results_csv(room_id: str, db: AsyncSession = Depends(get_db)):
    result = await GameResultService.get_by_room_id(db, room_id)
    if not result:
        raise HTTPException(status_code=404, detail="Результаты не найдены")
    
    csv_rows = []
    csv_rows.append('Место,Имя,Очки,Правильных ответов')
    
    sorted_players = sorted(result.players, key=lambda p: p.score, reverse=True)
    for idx, player in enumerate(sorted_players):
        correct_count = 0
        if isinstance(player.answers, list):
            correct_count = sum(1 for a in player.answers if isinstance(a, dict) and a.get('isCorrect', False))
        
        csv_rows.append(f'{idx + 1},"{player.name}",{player.score},{correct_count}')
    
    csv_content = '\n'.join(csv_rows)
    
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=results-{room_id}.csv"
        }
    )
