from taller.routes import votes


def _loguear_como(monkeypatch, usuario_id):
    """Reemplaza el punto de integración con el login para probar solo votos."""
    monkeypatch.setattr(votes, "usuario_id_actual", lambda: usuario_id)


def test_votar_positivo_una_pregunta(client, usuario, pregunta, monkeypatch):
    _loguear_como(monkeypatch, usuario)

    respuesta = client.post(f"/votes/questions/{pregunta}", json={"valor": 1})

    assert respuesta.status_code == 200
    assert respuesta.json["accion"] == "registrado"
    assert respuesta.json["positivos"] == 1
    assert respuesta.json["negativos"] == 0
    assert respuesta.json["total"] == 1
    assert respuesta.json["mi_voto"] == 1


def test_votar_dos_veces_lo_mismo_elimina_el_voto(
    client, usuario, pregunta, monkeypatch
):
    _loguear_como(monkeypatch, usuario)

    client.post(f"/votes/questions/{pregunta}", json={"valor": 1})
    respuesta = client.post(f"/votes/questions/{pregunta}", json={"valor": 1})

    assert respuesta.status_code == 200
    assert respuesta.json["accion"] == "eliminado"
    assert respuesta.json["total"] == 0
    assert respuesta.json["mi_voto"] is None


def test_cambiar_de_positivo_a_negativo_actualiza_el_voto(
    client, usuario, pregunta, monkeypatch
):
    _loguear_como(monkeypatch, usuario)

    client.post(f"/votes/questions/{pregunta}", json={"valor": 1})
    respuesta = client.post(f"/votes/questions/{pregunta}", json={"valor": -1})

    assert respuesta.status_code == 200
    assert respuesta.json["accion"] == "actualizado"
    assert respuesta.json["positivos"] == 0
    assert respuesta.json["negativos"] == 1
    assert respuesta.json["total"] == 1
    assert respuesta.json["mi_voto"] == -1


def test_votar_negativo_una_respuesta(client, usuario, respuesta, monkeypatch):
    _loguear_como(monkeypatch, usuario)

    resultado = client.post(f"/votes/answers/{respuesta}", json={"valor": -1})

    assert resultado.status_code == 200
    assert resultado.json["accion"] == "registrado"
    assert resultado.json["negativos"] == 1
    assert resultado.json["mi_voto"] == -1


def test_valor_invalido_devuelve_400(client, usuario, pregunta, monkeypatch):
    _loguear_como(monkeypatch, usuario)

    respuesta = client.post(f"/votes/questions/{pregunta}", json={"valor": 0})

    assert respuesta.status_code == 400
    assert "error" in respuesta.json


def test_sin_usuario_logueado_devuelve_401(client, pregunta, monkeypatch):
    _loguear_como(monkeypatch, None)

    respuesta = client.post(f"/votes/questions/{pregunta}", json={"valor": 1})

    assert respuesta.status_code == 401
    assert "error" in respuesta.json


def test_usuario_inexistente_devuelve_401(client, pregunta, monkeypatch):
    _loguear_como(monkeypatch, 9999)

    respuesta = client.post(f"/votes/questions/{pregunta}", json={"valor": 1})

    assert respuesta.status_code == 401
    assert "error" in respuesta.json


def test_pregunta_inexistente_devuelve_404(client, usuario, monkeypatch):
    _loguear_como(monkeypatch, usuario)

    respuesta = client.post("/votes/questions/9999", json={"valor": 1})

    assert respuesta.status_code == 404
    assert "error" in respuesta.json


def test_dos_usuarios_pueden_votar_la_misma_pregunta(
    client, usuario, otro_usuario, pregunta, monkeypatch
):
    usuario_actual = {"id": usuario}
    monkeypatch.setattr(votes, "usuario_id_actual", lambda: usuario_actual["id"])

    client.post(f"/votes/questions/{pregunta}", json={"valor": 1})
    usuario_actual["id"] = otro_usuario
    respuesta = client.post(f"/votes/questions/{pregunta}", json={"valor": 1})

    assert respuesta.status_code == 200
    assert respuesta.json["positivos"] == 2
    assert respuesta.json["mi_voto"] == 1


def test_voto_por_formulario_redirige(client, usuario, pregunta, monkeypatch):
    _loguear_como(monkeypatch, usuario)

    respuesta = client.post(
        f"/votes/questions/{pregunta}",
        data={"valor": "1"},
        headers={"Referer": "/questions/1"},
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/questions/1"
