from datetime import UTC, datetime, timedelta

from taller.extensions import db
from taller.models.models import Respuesta


def _login(client, usuario_id):
    with client.session_transaction() as sess:
        sess["usuario_id"] = usuario_id


# --- POST /answers/ (respuestas humanas) ---


def test_create_answer_json_o_question_id_invalido_devuelve_400(client):
    resp_sin_json = client.post(
        "/answers/",
        data="no-es-json",
        content_type="text/plain",
    )
    assert resp_sin_json.status_code == 400
    assert (
        resp_sin_json.get_json()["error"]
        == "El cuerpo de la petición debe ser un JSON válido."
    )

    resp_sin_qid = client.post("/answers/", json={"body": "Respuesta válida"})
    assert resp_sin_qid.status_code == 400
    assert resp_sin_qid.get_json()["error"] == "El campo 'question_id' es obligatorio."

    resp_qid_texto = client.post(
        "/answers/",
        json={"question_id": "abc", "body": "Respuesta válida"},
    )
    assert resp_qid_texto.status_code == 400
    assert (
        resp_qid_texto.get_json()["error"]
        == "El campo 'question_id' debe ser un número entero."
    )


def test_create_answer_pregunta_inexistente_devuelve_404(app, client):
    with app.app_context():
        response = client.post(
            "/answers/",
            json={
                "question_id": 9999,
                "body": "Respuesta para pregunta que no existe.",
            },
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "La pregunta indicada no existe."


def test_create_answer_sin_sesion_devuelve_401(app, client, pregunta):
    with app.app_context():
        response = client.post(
            "/answers/",
            json={"question_id": pregunta, "body": "Respuesta sin usuario en sesión."},
        )
        assert response.status_code == 401
        assert (
            response.get_json()["error"]
            == "Debés iniciar sesión para publicar una respuesta."
        )


def test_create_answer_cuerpo_invalido_devuelve_400(app, client, usuario, pregunta):
    _login(client, usuario)

    with app.app_context():
        resp_corto = client.post(
            "/answers/",
            json={"question_id": pregunta, "body": "1234"},
        )
        assert resp_corto.status_code == 400
        assert "al menos 5 caracteres" in resp_corto.get_json()["error"]

        resp_vacio = client.post(
            "/answers/",
            json={"question_id": pregunta, "body": "    "},
        )
        assert resp_vacio.status_code == 400
        assert (
            resp_vacio.get_json()["error"]
            == "El cuerpo de una respuesta no puede estar vacío."
        )

        resp_no_str = client.post(
            "/answers/",
            json={"question_id": pregunta, "body": 12345},
        )
        assert resp_no_str.status_code == 400
        assert (
            resp_no_str.get_json()["error"]
            == "El cuerpo de la respuesta debe ser un texto."
        )


def test_create_answer_humana_exitosa(app, client, otro_usuario, pregunta):
    _login(client, otro_usuario)

    with app.app_context():
        response = client.post(
            "/answers/",
            json={
                "question_id": pregunta,
                "body": "  Cada request pasa por el dispatcher y ejecuta la vista asociada.  ",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["question_id"] == pregunta
        assert (
            data["body"]
            == "Cada request pasa por el dispatcher y ejecuta la vista asociada."
        )
        assert data["is_accepted"] is False
        assert data["author"] == {
            "id": otro_usuario,
            "type": "human",
            "badge": "Humano",
        }
        assert "published_at" in data

        guardada = db.session.get(Respuesta, data["id"])
        assert guardada is not None
        assert guardada.es_ia is False
        assert guardada.usuario_id == otro_usuario


# --- POST /answers/ (respuestas con IA) ---


def test_create_answer_ia_exitosa(app, client, usuario, pregunta, monkeypatch):
    def fake_crear_respuesta_ia(pregunta_obj):
        resp = Respuesta(
            cuerpo=f"Sugerencia automática para: {pregunta_obj.titulo}",
            pregunta_id=pregunta_obj.id,
            usuario_id=usuario,
            es_ia=True,
            aceptada=False,
        )
        db.session.add(resp)
        db.session.commit()
        return resp

    monkeypatch.setattr(
        "taller.routes.answers.crear_respuesta_ia", fake_crear_respuesta_ia
    )

    with app.app_context():
        response = client.post(
            "/answers/",
            json={"question_id": pregunta, "author_type": "IA"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["question_id"] == pregunta
        assert data["author"]["type"] == "ai"
        assert data["author"]["badge"] == "IA"
        assert "Sugerencia automática" in data["body"]


def test_create_answer_ia_error_devuelve_502(app, client, pregunta, monkeypatch):
    def fake_error_ia(pregunta_obj):
        raise ValueError("Fallo al contactar al servicio de IA")

    monkeypatch.setattr("taller.routes.answers.crear_respuesta_ia", fake_error_ia)

    with app.app_context():
        response = client.post(
            "/answers/",
            json={"question_id": pregunta, "author_type": "ai"},
        )
        assert response.status_code == 502
        assert response.get_json()["error"] == "No se pudo generar la respuesta de IA."


# --- GET /answers/question/<int:question_id> ---


def test_list_answers_for_question_ordenadas(app, client, usuario, pregunta):
    with app.app_context():
        t0 = datetime.now(UTC) - timedelta(minutes=10)
        t1 = datetime.now(UTC) - timedelta(minutes=5)

        r1 = Respuesta(
            cuerpo="Primera respuesta más antigua.",
            pregunta_id=pregunta,
            usuario_id=usuario,
            creada_en=t0,
        )
        r2 = Respuesta(
            cuerpo="Segunda respuesta más reciente.",
            pregunta_id=pregunta,
            usuario_id=usuario,
            creada_en=t1,
        )
        db.session.add_all([r1, r2])
        db.session.commit()

        response = client.get(f"/answers/question/{pregunta}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["question_id"] == pregunta
        cuerpos = [a["body"] for a in data["answers"]]
        assert cuerpos == [
            "Primera respuesta más antigua.",
            "Segunda respuesta más reciente.",
        ]


# --- PATCH y DELETE /answers/<int:answer_id>/accept ---


def test_accept_answer_permisos_y_errores(app, client, otro_usuario, respuesta):
    # Sin sesión -> 401
    with app.app_context():
        resp_401 = client.patch(f"/answers/{respuesta}/accept")
        assert resp_401.status_code == 401

    # Usuario distinto al autor de la pregunta -> 403
    _login(client, otro_usuario)
    with app.app_context():
        resp_403 = client.patch(f"/answers/{respuesta}/accept")
        assert resp_403.status_code == 403

        # Respuesta inexistente -> 404
        resp_404 = client.patch("/answers/99999/accept")
        assert resp_404.status_code == 404


def test_marcar_y_desmarcar_respuesta_aceptada(
    app, client, usuario, pregunta, respuesta
):
    _login(client, usuario)

    with app.app_context():
        segunda = Respuesta(
            cuerpo="Otra respuesta alternativa válida.",
            pregunta_id=pregunta,
            usuario_id=usuario,
            aceptada=True,
        )
        db.session.add(segunda)
        db.session.commit()
        segunda_id = segunda.id

        # Marcar `respuesta` como aceptada debe desmarcar `segunda`
        resp_patch = client.patch(f"/answers/{respuesta}/accept")
        assert resp_patch.status_code == 200
        assert resp_patch.get_json()["is_accepted"] is True

        assert db.session.get(Respuesta, respuesta).aceptada is True
        assert db.session.get(Respuesta, segunda_id).aceptada is False

        # Desmarcar `respuesta` con DELETE
        resp_delete = client.delete(f"/answers/{respuesta}/accept")
        assert resp_delete.status_code == 200
        assert resp_delete.get_json()["is_accepted"] is False
        assert db.session.get(Respuesta, respuesta).aceptada is False
