require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
const db = require('../models');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: true, methods: ["GET", "POST"] } });

app.use(express.static(path.join(__dirname, '../public')));
app.use(express.json());

db.sequelize.sync()
    .then(() => console.log('✅ PostgreSQL подключена и таблицы созданы'))
    .catch(err => console.error('❌ Ошибка PostgreSQL:', err.message));

const rooms = new Map();
const QUESTION_TIME = 15;
const AUTO_ADVANCE_DELAY = 5;

// 📤 API: Экспорт в CSV (БЕЗ БИБЛИОТЕКИ)
app.get('/api/export/:roomId', async (req, res) => {
    try {
        const result = await db.GameResult.findOne({
            where: { roomId: req.params.roomId },
            include: [{ model: db.PlayerResult, as: 'players' }]
        });
        if (!result) return res.status(404).json({ error: 'Игра не найдена' });

        const csvRows = [];
        csvRows.push('Место,Имя,Очки,Правильных ответов');
        
        const sortedPlayers = result.players.sort((a, b) => b.score - a.score);
        sortedPlayers.forEach((p, index) => {
            const correct = Array.isArray(p.answers) ? p.answers.filter(a => a.isCorrect).length : 0;
            csvRows.push(`${index + 1},"${p.name}",${p.score},${correct}`);
        });
        
        const csvContent = csvRows.join('\n');
        
        res.setHeader('Content-Type', 'text/csv; charset=utf-8');
        res.setHeader('Content-Disposition', `attachment; filename=results-${req.params.roomId}.csv`);
        res.send(csvContent);
    } catch (err) {
        console.error('❌ Ошибка экспорта:', err.message);
        res.status(500).json({ error: 'Ошибка экспорта: ' + err.message });
    }
});

// 📤 API: Получить вопросы
app.get('/api/questions', async (req, res) => {
    try {
        const questions = await db.Question.findAll();
        res.json(questions);
    } catch (err) {
        res.status(500).json({ error: 'Ошибка загрузки вопросов' });
    }
});

// 📥 API: Создать вопрос
app.post('/api/questions', async (req, res) => {
    try {
        const question = await db.Question.create(req.body);
        res.status(201).json(question);
    } catch (err) {
        res.status(400).json({ error: 'Ошибка создания вопроса' });
    }
});

io.on('connection', (socket) => {
    console.log('✅ Подключился клиент:', socket.id);

    // Создание комнаты
    socket.on('create_room', async (data = {}) => {
        try {
            const { quizTitle, questionIds } = data;
            const roomId = Math.random().toString(36).substring(2, 8).toUpperCase();
            
            let questions = [];
            if (questionIds && questionIds.length > 0) {
                questions = await db.Question.findAll({ where: { id: questionIds } });
            } else {
                questions = [
                    { id: 'q1', text: "Столица Франции?", options: ["Лондон", "Париж", "Берлин"], correct: [1], type: "single" },
                    { id: 'q2', text: "Введите формулу воды:", options: [], correct: "H2O", type: "text" },
                    { id: 'q3', text: "Выберите чётные числа:", options: ["1", "2", "3", "4", "5"], correct: [1, 3], type: "multiple" }
                ];
            }
            
            rooms.set(roomId, {
                hostId: socket.id,
                quizTitle: quizTitle || 'Викторина',
                players: [],
                questionIndex: -1,
                timer: null,
                autoAdvanceTimer: null,
                timeLeft: QUESTION_TIME,
                questions: questions,
                roomId: roomId
            });
            
            socket.join(roomId);
            socket.emit('room_created', { roomId });
            console.log(`🏠 Комната ${roomId} создана`);
        } catch (err) {
            console.error('Ошибка создания комнаты:', err);
            socket.emit('error', 'Не удалось создать комнату');
        }
    });

    // Вход студента
    socket.on('join_room', ({ roomId, playerName }) => {
        const room = rooms.get(roomId);
        if (room) {
            socket.join(roomId);
            room.players.push({ 
                id: socket.id, 
                name: playerName, 
                score: 0, 
                hasAnswered: false, 
                textAnswer: '', 
                currentAnswer: null 
            });
            io.to(room.hostId).emit('player_joined', { players: room.players });
            socket.emit('joined_success', { roomId });
            console.log(`👤 ${playerName} присоединился`);
        } else {
            socket.emit('error', 'Комната не найдена');
        }
    });

    // Ответ студента
    socket.on('confirm_answer', (data) => {
        if (!data) return;
        const { roomId, answerData } = data;
        const room = rooms.get(roomId);
        
        if (!room || room.timeLeft <= 0 || !answerData) {
            console.log('⚠️ Некорректный ответ:', { roomId, answerData });
            return;
        }
        
        const currentQuestion = room.questions[room.questionIndex];
        const player = room.players.find(p => p.id === socket.id);
        
        if (player && currentQuestion && !player.hasAnswered) {
            player.hasAnswered = true;
            let isCorrect = false;
            const qType = currentQuestion.type || 'single';
            
            if (qType === 'text') {
                const userAnswer = (answerData.textAnswer || '').trim().toLowerCase();
                const correctAnswer = (currentQuestion.correct || '').toString().trim().toLowerCase();
                isCorrect = userAnswer === correctAnswer;
                player.textAnswer = answerData.textAnswer;
                console.log(`📝 ${player.name}: "${userAnswer}" ${isCorrect ? '✅' : '❌'}`);
                io.to(room.hostId).emit('text_answer_received', {
                    playerName: player.name, 
                    answer: player.textAnswer, 
                    isCorrect
                });
            } else {
                const correctArr = Array.isArray(currentQuestion.correct) ? currentQuestion.correct : [currentQuestion.correct];
                const userArr = Array.isArray(answerData.answerIndices) ? answerData.answerIndices : [answerData.answerIndices].filter(v => v !== undefined);
                const sortedC = [...correctArr].sort((a,b) => a - b);
                const sortedU = [...userArr].sort((a,b) => a - b);
                isCorrect = sortedC.length === sortedU.length && sortedC.every((v, i) => v === sortedU[i]);
                console.log(`🔘 ${player.name}: [${sortedU}] ${isCorrect ? '✅' : '❌'}`);
            }
            
            if (isCorrect) {
                player.score += 100 + Math.floor(room.timeLeft * 5);
            }
            
            player.currentAnswer = {
                questionId: currentQuestion.id,
                userAnswer: qType === 'text' ? player.textAnswer : answerData.answerIndices,
                isCorrect
            };
            
            const answered = room.players.filter(p => p.hasAnswered).length;
            const total = room.players.length;
            
            console.log(`📊 Прогресс: ${answered}/${total}`);
            
            io.to(room.hostId).emit('answer_progress', { answered, total, allAnswered: answered === total });
            io.to(room.hostId).emit('update_leaderboard', { 
                players: [...room.players].sort((a, b) => b.score - a.score) 
            });
            
            if (answered === total && total > 0 && !room.autoAdvanceTimer) {
                console.log(`✅ Все ответили! Авто-перелистывание через ${AUTO_ADVANCE_DELAY} сек`);
                startAutoAdvance(room, roomId);
            }
            
            socket.emit('answer_confirmed', { isCorrect });
        }
    });

    // Следующий вопрос
    socket.on('next_question', ({ roomId }) => {
        const room = rooms.get(roomId);
        if (room && room.hostId === socket.id) {
            advanceQuestion(room, roomId);
        }
    });

    // Завершение игры
    socket.on('end_game', async ({ roomId }) => {
        const room = rooms.get(roomId);
        if (room && room.hostId === socket.id) {
            try {
                const sorted = [...room.players].sort((a, b) => b.score - a.score);
                const results = sorted.map((p, i) => ({
                    rank: i + 1, 
                    name: p.name, 
                    score: p.score,
                    medal: i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : null
                }));
                
                const gameResult = await db.GameResult.create({
                    roomId, 
                    quizTitle: room.quizTitle, 
                    totalQuestions: room.questions.length
                });
                
                await db.PlayerResult.bulkCreate(sorted.map(p => ({
                    gameResultId: gameResult.id, 
                    name: p.name, 
                    score: p.score,
                    answers: p.currentAnswer ? [p.currentAnswer] : []
                })));
                
                io.to(roomId).emit('game_over', { 
                    results, 
                    totalQuestions: room.questions.length, 
                    canExport: true, 
                    roomId 
                });
                console.log(`💾 Результаты сохранены: ${roomId}`);
            } catch (err) {
                console.error('Ошибка сохранения:', err);
                io.to(roomId).emit('game_over', { 
                    results: [...room.players].sort((a,b) => b.score - a.score).map((p,i) => ({ rank: i+1, name: p.name, score: p.score })),
                    totalQuestions: room.questions.length 
                });
            }
        }
    });

    socket.on('disconnect', () => {
        console.log('❌ Клиент отключился:', socket.id);
    });
});

// 🔥 Авто-перелистывание
function startAutoAdvance(room, roomId) {
    if (room.autoAdvanceTimer) clearTimeout(room.autoAdvanceTimer);
    io.to(roomId).emit('auto_advance_warning', { delay: AUTO_ADVANCE_DELAY });
    room.autoAdvanceTimer = setTimeout(() => {
        console.log('⏱️ Авто-перелистывание...');
        advanceQuestion(room, roomId);
    }, AUTO_ADVANCE_DELAY * 1000);
}

// 🔥 Переход к вопросу
function advanceQuestion(room, roomId) {
    if (room.timer) clearInterval(room.timer);
    if (room.autoAdvanceTimer) clearTimeout(room.autoAdvanceTimer);
    room.autoAdvanceTimer = null;
    
    room.questionIndex++;
    room.players.forEach(p => { 
        p.hasAnswered = false; 
        p.textAnswer = ''; 
        p.currentAnswer = null; 
    });
    
    if (room.questionIndex < room.questions.length) {
        const q = room.questions[room.questionIndex];
        io.to(room.hostId).emit('show_question_host', q);
        io.to(roomId).emit('show_question_player', { 
            id: q.id, 
            text: q.text, 
            options: q.options, 
            type: q.type || 'single', 
            image: q.image 
        });
        
        room.timeLeft = QUESTION_TIME;
        io.to(roomId).emit('timer_start', { timeLeft: room.timeLeft });
        console.log(`❓ Вопрос ${room.questionIndex + 1}: ${q.text}`);
        
        room.timer = setInterval(() => {
            room.timeLeft--;
            io.to(roomId).emit('timer_update', { timeLeft: room.timeLeft });
            if (room.timeLeft <= 0) {
                clearInterval(room.timer);
                io.to(roomId).emit('time_up');
                console.log('⏰ Время вышло!');
                startAutoAdvance(room, roomId);
            }
        }, 1000);
    } else {
        // 🔥 ВСЕ ВОПРОСЫ ПРОЙДЕНЫ - АВТО-ЗАВЕРШЕНИЕ
        console.log('🏁 Все вопросы пройдены - авто-завершение через 5 сек');
        io.to(roomId).emit('auto_advance_warning', { delay: 5 });
        
        setTimeout(() => {
            // Находим сокет учителя и вызываем end_game
            const room = rooms.get(roomId);
            if (room) {
                const hostSocket = io.sockets.sockets.get(room.hostId);
                if (hostSocket) {
                    hostSocket.emit('end_game', { roomId });
                }
            }
        }, 5000);
    }
}

const PORT = process.env.PORT || 3000;
const HOST = '0.0.0.0';
server.listen(PORT, HOST, () => {
    console.log(`✅ Сервер запущен: http://${HOST}:${PORT}`);
});