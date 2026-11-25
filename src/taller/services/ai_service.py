import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from ..extensions import db
from ..models import Pregunta, Respuesta


def generar_texto_ia(titulo: str, cuerpo: str) -> str:
    """Genera una respuesta coherente usando Gemini API o un fallback local."""
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={api_key}"
        )
        prompt = (
            "Respondé de forma clara, breve y útil a la siguiente pregunta de un "
            f"estudiante universitario.\nTítulo: {titulo}\nDetalle: {cuerpo}"
        )
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if len(texto) >= 5:
                    return texto
        except Exception:
            pass  # Si falla la red o la API, cae al respaldo

    return (
        f"Respuesta automática de IA sobre '{titulo}': "
        f"revisá los conceptos principales relacionados con tu consulta ({cuerpo[:120]})."
    )


def crear_respuesta_ia(pregunta: Pregunta) -> Respuesta:
    """Genera, valida y guarda una respuesta de IA para una pregunta."""
    texto = generar_texto_ia(pregunta.titulo, pregunta.cuerpo).strip()

    if not texto or len(texto) < 5:
        raise ValueError("La respuesta generada por la IA debe tener al menos 5 caracteres.")

    respuesta = Respuesta(
        cuerpo=texto,
        es_ia=True,
        pregunta_id=pregunta.id,
        usuario_id=None,
    )
    db.session.add(respuesta)
    db.session.commit()
    return respuesta


def responder_preguntas_sin_respuesta(horas: int = 24) -> list[Respuesta]:
    """Busca preguntas sin respuestas con más de `horas` de antigüedad y las responde."""
    # SQLite guarda datetimes sin tzinfo; quitamos tzinfo para comparar seguro
    limite = (datetime.now(timezone.utc) - timedelta(hours=horas)).replace(tzinfo=None)

    pendientes = (
        Pregunta.query
        .filter(Pregunta.creada_en <= limite)
        .filter(~Pregunta.respuestas.any())
        .all()
    )

    generadas = []
    for pregunta in pendientes:
        generadas.append(crear_respuesta_ia(pregunta))
    return generadas