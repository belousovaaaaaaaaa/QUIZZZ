import socketio
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
app = socketio.ASGIApp(sio)

# Хранилище комнат
rooms: Dict[str, dict] = {}

QUESTION_TIME = 15
AUTO_ADVANCE_DELAY = 5


@sio.event
async def connect(sid, environ):
    print(f"✅ Подключился клиент: {sid}")


@sio.event
async def disconnect(sid):
    print(f"❌ Клиент отключился: {sid}")
    # Очистка комнат при отключении хоста
    for room_id, room in list(rooms.items()):
        if room.get('hostId') == sid:
            await sio.emit('game_ended', {'reason': 'host_left'}, room=room_id)
            rooms.pop(room_id, None)


@sio.on('create_room')
async def create_room(sid, data: dict):
    try:
        from app.services.crud_service import QuestionService
        from app.database import async_session_maker
        
        quiz_title = data.get('quizTitle', 'Викторина')
        question_ids = data.get('questionIds', [])
        
        room_id = ''.join(__import__('random').choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        
        questions = []
        if question_ids:
            async with async_session_maker() as db:
                questions_obj = await QuestionService.get_by_ids(db, question_ids)
                questions = [
                    {
                        'id': q.id,
                        'text': q.text,
                        'options': q.options or [],
                        'correct': q.correct_answer,
                        'type': q.question_type,
                        'image': q.image_url
                    }
                    for q in questions_obj
                ]
        
        if not questions:
            questions = [
                {'id': 'q1', 'text': "Столица Франции?", 'options': ["Лондон", "Париж", "Берлин"], 'correct': [1], 'type': 'single'},
                {'id': 'q2', 'text': "Введите формулу воды:", 'options': [], 'correct': "H2O", 'type': 'text'},
                {'id': 'q3', 'text': "Выберите чётные числа:", 'options': ["1", "2", "3", "4", "5"], 'correct': [1, 3], 'type': 'multiple'}
            ]
        
        rooms[room_id] = {
            'hostId': sid,
            'quizTitle': quiz_title,
            'players': [],
            'questionIndex': -1,
            'timer': None,
            'autoAdvanceTimer': None,
            'timeLeft': QUESTION_TIME,
            'questions': questions,
            'roomId': room_id
        }
        
        await sio.enter_room(sid, room_id)
        await sio.emit('room_created', {'roomId': room_id}, room=sid)
        print(f"🏠 Комната {room_id} создана")
    except Exception as e:
        print(f"Ошибка создания комнаты: {e}")
        await sio.emit('error', 'Не удалось создать комнату', room=sid)


@sio.on('join_room')
async def join_room(sid, data: dict):
    room_id = data.get('roomId')
    player_name = data.get('playerName')
    
    room = rooms.get(room_id)
    if room:
        await sio.enter_room(sid, room_id)
        room['players'].append({
            'id': sid,
            'name': player_name,
            'score': 0,
            'hasAnswered': False,
            'textAnswer': '',
            'currentAnswer': None
        })
        await sio.emit('player_joined', {'players': room['players']}, room=room['hostId'])
        await sio.emit('joined_success', {'roomId': room_id}, room=sid)
        print(f"👤 {player_name} присоединился к {room_id}")
    else:
        await sio.emit('error', 'Комната не найдена', room=sid)


@sio.on('confirm_answer')
async def confirm_answer(sid, data: dict):
    if not data:
        return
    
    room_id = data.get('roomId')
    answer_data = data.get('answerData')
    
    room = rooms.get(room_id)
    if not room or room['timeLeft'] <= 0 or not answer_data:
        print(f"⚠️ Некорректный ответ: {room_id}")
        return
    
    current_question = room['questions'][room['questionIndex']] if room['questionIndex'] >= 0 else None
    player = next((p for p in room['players'] if p['id'] == sid), None)
    
    if player and current_question and not player['hasAnswered']:
        player['hasAnswered'] = True
        is_correct = False
        q_type = current_question.get('type', 'single')
        
        if q_type == 'text':
            user_answer = (answer_data.get('textAnswer', '') or '').strip().lower()
            correct_answer = str(current_question.get('correct', '')).strip().lower()
            is_correct = user_answer == correct_answer
            player['textAnswer'] = answer_data.get('textAnswer', '')
            print(f"📝 {player['name']}: \"{user_answer}\" {'✅' if is_correct else '❌'}")
            await sio.emit('text_answer_received', {
                'playerName': player['name'],
                'answer': player['textAnswer'],
                'isCorrect': is_correct
            }, room=room['hostId'])
        else:
            correct_arr = current_question.get('correct', [])
            if not isinstance(correct_arr, list):
                correct_arr = [correct_arr]
            user_arr = answer_data.get('answerIndices', [])
            if not isinstance(user_arr, list):
                user_arr = [user_arr] if user_arr is not None else []
            sorted_c = sorted(correct_arr)
            sorted_u = sorted(user_arr)
            is_correct = len(sorted_c) == len(sorted_u) and all(c == u for c, u in zip(sorted_c, sorted_u))
            print(f"🔘 {player['name']}: [{sorted_u}] {'✅' if is_correct else '❌'}")
        
        if is_correct:
            player['score'] += 100 + int(room['timeLeft'] * 5)
        
        player['currentAnswer'] = {
            'questionId': current_question.get('id'),
            'userAnswer': player['textAnswer'] if q_type == 'text' else answer_data.get('answerIndices'),
            'isCorrect': is_correct
        }
        
        answered_count = sum(1 for p in room['players'] if p['hasAnswered'])
        total_players = len(room['players'])
        
        print(f"📊 Прогресс: {answered_count}/{total_players}")
        
        await sio.emit('answer_progress', {
            'answered': answered_count,
            'total': total_players,
            'allAnswered': answered_count == total_players
        }, room=room['hostId'])
        
        sorted_players = sorted(room['players'], key=lambda x: x['score'], reverse=True)
        await sio.emit('update_leaderboard', {'players': sorted_players}, room=room['hostId'])
        
        if answered_count == total_players and total_players > 0 and not room.get('autoAdvanceTimer'):
            print(f"✅ Все ответили! Авто-перелистывание через {AUTO_ADVANCE_DELAY} сек")
            asyncio.create_task(start_auto_advance(room, room_id))
        
        await sio.emit('answer_confirmed', {'isCorrect': is_correct}, room=sid)


@sio.on('next_question')
async def next_question(sid, data: dict):
    room_id = data.get('roomId')
    room = rooms.get(room_id)
    if room and room.get('hostId') == sid:
        await advance_question(room, room_id)


@sio.on('end_game')
async def end_game(sid, data: dict):
    room_id = data.get('roomId')
    room = rooms.get(room_id)
    if room and room.get('hostId') == sid:
        try:
            from app.services.crud_service import GameResultService
            from app.database import async_session_maker
            
            sorted_players = sorted(room['players'], key=lambda x: x['score'], reverse=True)
            results = []
            for i, p in enumerate(sorted_players):
                medal = '🥇' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else None
                results.append({
                    'rank': i + 1,
                    'name': p['name'],
                    'score': p['score'],
                    'medal': medal
                })
            
            async with async_session_maker() as db:
                players_data = [{'name': p['name'], 'score': p['score'], 'answers': [p['currentAnswer']] if p.get('currentAnswer') else []} for p in sorted_players]
                await GameResultService.create_with_players(
                    db, room_id, room['quizTitle'], len(room['questions']), players_data
                )
            
            await sio.emit('game_over', {
                'results': results,
                'totalQuestions': len(room['questions']),
                'canExport': True,
                'roomId': room_id
            }, room=room_id)
            print(f"💾 Результаты сохранены: {room_id}")
        except Exception as e:
            print(f"Ошибка сохранения результатов: {e}")
            sorted_players = sorted(room['players'], key=lambda x: x['score'], reverse=True)
            results = [{'rank': i+1, 'name': p['name'], 'score': p['score']} for i, p in enumerate(sorted_players)]
            await sio.emit('game_over', {
                'results': results,
                'totalQuestions': len(room['questions'])
            }, room=room_id)


async def start_auto_advance(room: dict, room_id: str):
    if room.get('autoAdvanceTimer'):
        room['autoAdvanceTimer'].cancel()
    
    await sio.emit('auto_advance_warning', {'delay': AUTO_ADVANCE_DELAY}, room=room_id)
    await asyncio.sleep(AUTO_ADVANCE_DELAY)
    print("⏱️ Авто-перелистывание...")
    await advance_question(room, room_id)


async def advance_question(room: dict, room_id: str):
    if room.get('timer'):
        room['timer'].cancel()
    if room.get('autoAdvanceTimer'):
        room['autoAdvanceTimer'].cancel()
    room['autoAdvanceTimer'] = None
    
    room['questionIndex'] += 1
    
    for p in room['players']:
        p['hasAnswered'] = False
        p['textAnswer'] = ''
        p['currentAnswer'] = None
    
    if room['questionIndex'] < len(room['questions']):
        q = room['questions'][room['questionIndex']]
        await sio.emit('show_question_host', q, room=room['hostId'])
        await sio.emit('show_question_player', {
            'id': q.get('id'),
            'text': q.get('text'),
            'options': q.get('options', []),
            'type': q.get('type', 'single'),
            'image': q.get('image')
        }, room=room_id)
        
        room['timeLeft'] = QUESTION_TIME
        await sio.emit('timer_start', {'timeLeft': room['timeLeft']}, room=room_id)
        print(f"❓ Вопрос {room['questionIndex'] + 1}: {q.get('text')}")
        
        async def timer_loop():
            for i in range(QUESTION_TIME - 1, -1, -1):
                await asyncio.sleep(1)
                room['timeLeft'] = i
                await sio.emit('timer_update', {'timeLeft': i}, room=room_id)
                if i == 0:
                    break
            await sio.emit('time_up', room=room_id)
            print("⏰ Время вышло!")
            asyncio.create_task(start_auto_advance(room, room_id))
        
        room['timer'] = asyncio.create_task(timer_loop())
    else:
        print("🏁 Все вопросы пройдены - авто-завершение через 5 сек")
        await sio.emit('auto_advance_warning', {'delay': 5}, room=room_id)
        await asyncio.sleep(5)
        
        room = rooms.get(room_id)
        if room:
            host_sid = room.get('hostId')
            if host_sid:
                await end_game(host_sid, {'roomId': room_id})
