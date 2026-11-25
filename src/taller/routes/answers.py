from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models.models import Pregunta, Respuesta

bp = Blueprint("answers", __name__, url_prefix="/answers")

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


def _serialize_answer(respuesta: Respuesta) -> dict:
    author_type = "ai" if respuesta.es_ia else "human"
    return {
        "id": respuesta.id,
        "question_id": respuesta.pregunta_id,
        "body": respuesta.cuerpo,
        "published_at": respuesta.creada_en.isoformat(),
        "is_accepted": respuesta.aceptada,
        "author": {
            "id": respuesta.usuario_id,
            "type": author_type,  # "human" | "ai"
            "badge": _author_badge(author_type),  # "Humano" | "IA"
        },
    }


@bp.post("/")
def create_answer():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "El cuerpo de la petición debe ser un JSON válido."}), 400

    raw_question_id = data.get("question_id")
    if raw_question_id is None or str(raw_question_id).strip() == "":
        return jsonify({"error": "El campo 'question_id' es obligatorio."}), 400

    try:
        question_id = int(raw_question_id)
    except (TypeError, ValueError):
        return jsonify({"error": "El campo 'question_id' debe ser un número entero."}), 400

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

    # La respuesta debe apuntar a una pregunta que exista en la base de datos.
    pregunta = db.session.get(Pregunta, question_id)
    if pregunta is None:
        return jsonify({"error": "La pregunta indicada no existe."}), 404

    author_type = _normalize_author_type(data.get("author_type"))
    author_id = data.get("author_id")

    # Las respuestas de IA no tienen un usuario humano asociado.
    if author_type == "ai":
        author_id = None
    elif author_id is not None:
        try:
            author_id = int(author_id)
        except (TypeError, ValueError):
            return jsonify({"error": "El campo 'author_id' debe ser un número entero."}), 400

    respuesta = Respuesta(
        cuerpo=body,
        pregunta_id=question_id,
        usuario_id=author_id,
        es_ia=(author_type == "ai"),
        aceptada=False,
    )
    db.session.add(respuesta)
    db.session.commit()

    return jsonify(_serialize_answer(respuesta)), 201


@bp.get("/question/<int:question_id>")
def list_answers_for_question(question_id):
    # Permite múltiples respuestas para una misma pregunta
    respuestas = (
        Respuesta.query.filter_by(pregunta_id=question_id)
        .order_by(Respuesta.creada_en.asc())
        .all()
    )
    return jsonify({
        "question_id": question_id,
        "answers": [_serialize_answer(respuesta) for respuesta in respuestas],
    }), 200


@bp.patch("/<int:answer_id>/accept")
def mark_as_accepted(answer_id: int):
    respuesta = db.session.get(Respuesta, answer_id)
    if respuesta is None:
        return jsonify({"error": "Respuesta no encontrada."}), 404

    # Si solo puede haber una respuesta aceptada por pregunta, desmarcamos las demás.
    for otra in Respuesta.query.filter_by(pregunta_id=respuesta.pregunta_id).all():
        otra.aceptada = (otra.id == answer_id)

    db.session.commit()

    return jsonify(_serialize_answer(respuesta)), 200
