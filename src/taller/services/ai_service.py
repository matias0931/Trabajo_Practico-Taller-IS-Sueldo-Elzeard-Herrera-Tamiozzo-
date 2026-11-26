import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google import genai

from ..extensions import db
from ..models import Pregunta, Respuesta

load_dotenv()

def generar_texto_ia(titulo: str, cuerpo: str) -> str:
    """Genera una respuesta coherente usando Gemini API o un fallback local."""
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        prompt = (
            "Respondé de forma clara, breve y útil a la siguiente pregunta de un "
            "estudiante universitario.\n"
            "IMPORTANTE: Respondé únicamente en texto plano. NO uses Markdown "
            "(nada de asteriscos **, numerales ###, ni guiones largos), ni formato "
            "LaTeX (nada de signos $, \\rightarrow, \\text{}, etc.). "
            "Usá flechas normales como '->' y separá las ideas con saltos de línea.\n"
            f"Título: {titulo}\nDetalle: {cuerpo}"
        )
        client = genai.Client(api_key=api_key)
        modelos = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
        ]
        for modelo in modelos:
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                texto = (response.text or "").strip()
                if len(texto) >= 5:
                    return texto
            except Exception as e:
                print(f"Error con {modelo}: {e}")

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
