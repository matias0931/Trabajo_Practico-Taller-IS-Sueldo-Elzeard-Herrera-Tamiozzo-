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
@bp.post("/")
def create_answer():
    global _NEXT_ID

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "El cuerpo de la petición debe ser un JSON válido."}), 400

    question_id = data.get("question_id")
    if question_id is None or str(question_id).strip() == "":
        return jsonify({"error": "El campo 'question_id' es obligatorio."}), 400

    raw_body = data.get("body")
    if not isinstance(raw_body, str):
        return jsonify({"error": "El cuerpo de la respuesta debe ser un texto."}), 400

    body = raw_body.strip()
    if not body:
        return jsonify({"error": "El cuerpo de una respuesta no puede estar vacío."}), 400
    if len(body) < MIN_BODY_LENGTH:
        return jsonify({
            "error": f"El cuerpo de una respuesta debe contener al menos {MIN_BODY_LENGTH} caracteres."
        }), 400

    author_type = _normalize_author_type(data.get("author_type"))
    published_at = datetime.now(timezone.utc).isoformat()

    answer = {
        "id": _NEXT_ID,
        "question_id": question_id,
        "body": body,
        "published_at": published_at,
        "is_accepted": False,
        "author_id": data.get("author_id"),
        "author_type": author_type,
    }
    _NEXT_ID += 1
    _ANSWERS_DB.append(answer)

    return jsonify(_serialize_answer(answer)), 201
@bp.get("/question/<question_id>")
def list_answers_for_question(question_id):
    # Permite múltiples respuestas para una misma pregunta
    matching = [
        _serialize_answer(ans)
        for ans in _ANSWERS_DB
        if str(ans["question_id"]) == str(question_id)
    ]
    return jsonify({"question_id": question_id, "answers": matching}), 200