from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

bp = Blueprint("answers", __name__, url_prefix="/answers")

# Estructura temporal en memoria para probar rápido.
# Cuando integren con el modelo/BD del proyecto, reemplazá esto por el repositorio/ORM.
_ANSWERS_DB: list[dict] = []
_NEXT_ID = 1

MIN_BODY_LENGTH = 5
VALID_AUTHOR_TYPES = {"human", "ai"}


def _normalize_author_type(raw_type: str | None) -> str:
    """
    Identifica al autor como 'ai' o 'human'.
    Por defecto se trata como 'human' si no se especifica o no coincide con 'ai'.
    """
    if not raw_type:
        return "human"
    normalized = raw_type.strip().lower()
    if normalized in {"ai", "ia", "artificial_intelligence", "bot"}:
        return "ai"
    return "human"


def _author_badge(author_type: str) -> str:
    return "IA" if author_type == "ai" else "Humano"


def _serialize_answer(answer: dict) -> dict:
    return {
        "id": answer["id"],
        "question_id": answer["question_id"],
        "body": answer["body"],
        "published_at": answer["published_at"],
        "is_accepted": answer["is_accepted"],
        "author": {
            "id": answer["author_id"],
            "type": answer["author_type"],  # "human" | "ai"
            "badge": _author_badge(answer["author_type"]),  # "Humano" | "IA"
        },
    }