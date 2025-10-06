from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jur_checker  # Импортируем наш модуль
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variable configuration (Observability feature)
ALIAS_STRICTNESS = os.getenv("ALIAS_STRICTNESS", "strict")
if ALIAS_STRICTNESS not in {"strict", "balanced", "aggressive"}:
    raise ValueError(f"Invalid ALIAS_STRICTNESS={ALIAS_STRICTNESS}, must be strict|balanced|aggressive")

ENABLE_MATCH_LOGGING = os.getenv("ENABLE_MATCH_LOGGING", "false").lower() == "true"
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

logger.info(f"Configuration loaded: ALIAS_STRICTNESS={ALIAS_STRICTNESS}, ENABLE_MATCH_LOGGING={ENABLE_MATCH_LOGGING}, LOG_RETENTION_DAYS={LOG_RETENTION_DAYS}")

# --- Pydantic модели для валидации данных ---
class TextIn(BaseModel):
    text: str

class CandidateOut(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str
    found_alias: str
    context: str

class CandidatesResponse(BaseModel):
    candidates: list[CandidateOut]

# --- Инициализация FastAPI и JurChecker ---
app = FastAPI(
    title="JurChecker API",
    description="API для быстрого поиска кандидатов на упоминания из реестров РФ.",
    version="1.0.0"
)

CSV_FILE_PATH = 'registry_entities_rows.csv'
checker: jur_checker.JurChecker | None = None

@app.on_event("startup")
def load_checker():
    """
    Загружает данные в JurChecker один раз при старте сервера.
    Это гарантирует, что тяжелая операция выполняется только один раз.
    """
    global checker
    try:
        checker = jur_checker.JurChecker(csv_path=CSV_FILE_PATH)
        logger.info("JurChecker успешно инициализирован при старте приложения.")
    except FileNotFoundError:
        checker = None
        logger.critical(f"Файл реестра не найден по пути: {CSV_FILE_PATH}")

# --- API Эндпоинт ---
@app.post("/check-candidates", response_model=CandidatesResponse)
def check_text_for_candidates(request: TextIn):
    """
    Принимает текст и возвращает список ПОТЕНЦИАЛЬНЫХ упоминаний (кандидатов)
    для дальнейшей верификации через N8n и OpenRouter.
    """
    if checker is None:
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail="Сервис не готов к работе: не удалось загрузить файл реестра."
        )

    candidates_list = checker.find_raw_candidates(request.text)

    return {"candidates": candidates_list}

@app.get("/health")
def health_check():
    """Простой эндпоинт для проверки, что сервис жив."""
    if checker is None:
         raise HTTPException(status_code=503, detail="Сервис не здоров: реестр не загружен.")
    return {"status": "ok", "alias_mode": ALIAS_STRICTNESS}