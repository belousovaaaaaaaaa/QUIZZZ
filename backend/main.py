from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os
from contextlib import asynccontextmanager

from app.database import init_db
from app.api.questions import router as questions_router
from app.api.results import router as results_router
from app.socket_handler import app as socket_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("✅ База данных инициализирована")
    yield
    # Shutdown


app = FastAPI(
    title="Quiz API",
    description="API для образовательной викторины",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(questions_router)
app.include_router(results_router)

# Монтирование Socket.IO
app.mount("/ws", socket_app)


# Статические файлы (для frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend/src")
if os.path.exists(frontend_path):
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "host.html"))
    
    @app.get("/host.html")
    async def serve_host():
        return FileResponse(os.path.join(frontend_path, "host.html"))
    
    @app.get("/player.html")
    async def serve_player():
        return FileResponse(os.path.join(frontend_path, "player.html"))
    
    @app.get("/editor.html")
    async def serve_editor():
        return FileResponse(os.path.join(frontend_path, "editor.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Quiz API v2.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
