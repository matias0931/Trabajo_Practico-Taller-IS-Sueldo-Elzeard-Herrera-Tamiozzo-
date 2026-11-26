from types import SimpleNamespace

from taller.extensions import db
from taller.models.models import Categoria, Pregunta, Tag


def _login(client, usuario_id):
    """Carga usuario_id en la sesión de Flask para el test client."""
    with client.session_transaction() as sess:
        sess["usuario_id"] = usuario_id


def _crear_categoria(nombre="General"):
    categoria = Categoria(nombre=nombre)
    db.session.add(categoria)
    db.session.commit()
    return categoria.id


def test_create_question_sin_sesion_devuelve_401(client):
    response = client.post(
        "/questions/",
        json={
            "titulo": "Título de prueba",
            "cuerpo": "Cuerpo descriptivo de prueba.",
            "categoria_id": 1,
        },
    )

    assert response.status_code == 401
    assert response.get_json() == {
        "error": "Debés iniciar sesión para publicar una pregunta."
    }


def test_create_question_validaciones_devuelve_400(app, client, usuario):
    _login(client, usuario)

    with app.app_context():
        response = client.post(
            "/questions/",
            json={
                "titulo": "abc",
                "cuerpo": "12345",
                "categoria_id": 999,
            },
        )

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert (
        "El título es obligatorio y debe tener más de 5 caracteres." in data["errors"]
    )
    assert (
        "El cuerpo descriptivo es obligatorio y debe tener más de 5 caracteres."
        in data["errors"]
    )
    assert "La categoría con ID 999 no existe en la base de datos." in data["errors"]


def test_create_question_sin_categoria_devuelve_400(app, client, usuario):
    _login(client, usuario)

    with app.app_context():
        response = client.post(
            "/questions/",
            json={
                "title": "Pregunta con title en inglés",
                "body": "Cuerpo con body en inglés y longitud válida.",
            },
        )

    assert response.status_code == 400
    data = response.get_json()
    assert "La pregunta debe estar asociada a una categoría." in data["errors"]


def test_create_question_exitosa_y_crea_tags(app, client, usuario):
    _login(client, usuario)

    with app.app_context():
        cat_id = _crear_categoria("Testing")
        tag_existente = Tag(nombre="pytest")
        db.session.add(tag_existente)
        db.session.commit()
        tag_existente_id = tag_existente.id

        response = client.post(
            "/questions/",
            json={
                "titulo": "¿Cómo probar endpoints en Flask?",
                "cuerpo": "Quiero verificar códigos HTTP, JSON y sesión en tests.",
                "categoria_id": cat_id,
                "tags": [tag_existente_id, "flask", "  "],
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["titulo"] == "¿Cómo probar endpoints en Flask?"
        assert (
            data["cuerpo"] == "Quiero verificar códigos HTTP, JSON y sesión en tests."
        )
        assert data["categoria_id"] == cat_id
        assert data["usuario_id"] == usuario
        assert set(data["tags"]) == {"pytest", "flask"}
        assert data["respuesta_ia"] is None
        assert "creada_en" in data

        pregunta_db = db.session.get(Pregunta, data["id"])
        assert pregunta_db is not None
        assert pregunta_db.usuario_id == usuario


def test_create_question_dispara_ia_con_tag_ia(app, client, usuario, monkeypatch):
    def fake_crear_respuesta_ia(pregunta_obj):
        return SimpleNamespace(cuerpo=f"IA responde a: {pregunta_obj.titulo}")

    monkeypatch.setattr(
        "taller.routes.questions.crear_respuesta_ia",
        fake_crear_respuesta_ia,
    )

    _login(client, usuario)

    with app.app_context():
        cat_id = _crear_categoria("Asistente IA")

        response = client.post(
            "/questions/",
            json={
                "titulo": "Duda con disparador automático",
                "cuerpo": "Probando que se genere respuesta automática al usar #ia.",
                "categoria_id": cat_id,
                "tags": ["  #IA  "],
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "#IA" in data["tags"]
        assert data["respuesta_ia"] == "IA responde a: Duda con disparador automático"


def test_procesar_pendientes_ia_devuelve_200(client, monkeypatch):
    respuestas_simulada = [
        SimpleNamespace(pregunta_id=1),
        SimpleNamespace(pregunta_id=2),
    ]

    monkeypatch.setattr(
        "taller.routes.questions.responder_preguntas_sin_respuesta",
        lambda horas=24: respuestas_simulada,
    )

    response = client.post("/questions/ia/pendientes")

    assert response.status_code == 200
    assert response.get_json() == {
        "respuestas_generadas": 2,
        "preguntas_respondidas": [1, 2],
    }
