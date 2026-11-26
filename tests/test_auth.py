from werkzeug.security import check_password_hash, generate_password_hash

from taller.extensions import db
from taller.models.models import Rol, UsuarioH
from taller.routes.auth import validar_password


def _crear_usuario_con_password(username, email, password_plana, rol_nombre="estudiante"):
    rol = Rol.query.filter_by(nombre=rol_nombre).first()
    if not rol:
        rol = Rol(nombre=rol_nombre)
        db.session.add(rol)
        db.session.flush()

    usuario = UsuarioH(
        username=username,
        email=email.lower(),
        password_hash=generate_password_hash(password_plana),
        rol_id=rol.id,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


# --- Tests unitarios de validar_password ---


def test_validar_password_casos():
    assert validar_password("Abc1") == "La contraseña debe tener al menos 8 caracteres."
    assert validar_password("PasswordSinNumero") == "La contraseña debe incluir al menos un dígito."
    assert validar_password("password123") == "La contraseña debe incluir al menos una letra mayúscula."
    assert validar_password("Password1") is None


# --- Tests de registro ---


def test_register_get_renderiza_formulario(client):
    response = client.get("/auth/register")
    assert response.status_code == 200


def test_register_post_campos_faltantes(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            data={"username": "sofia", "email": "", "password": "Password1"},
        )
        assert response.status_code == 200
        assert "Todos los campos son obligatorios." in response.get_data(as_text=True)
        assert UsuarioH.query.count() == 0


def test_register_post_correo_invalido(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            data={
                "username": "sofia",
                "email": "sofia@dominioinvalido.com",
                "password": "Password1",
            },
        )
        assert response.status_code == 200
        assert "Correo inválido." in response.get_data(as_text=True)
        assert UsuarioH.query.count() == 0


def test_register_post_password_invalida(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            data={
                "username": "sofia",
                "email": "sofia.test@gmail.com",
                "password": "corta",
            },
        )
        assert response.status_code == 200
        assert "La contraseña debe tener al menos 8 caracteres." in response.get_data(as_text=True)
        assert UsuarioH.query.count() == 0


def test_register_post_email_o_username_duplicado(app, client):
    with app.app_context():
        _crear_usuario_con_password("sofia_dev", "sofia.test@gmail.com", "Password1")

        resp_email = client.post(
            "/auth/register",
            data={
                "username": "otro_usuario",
                "email": "SOFIA.TEST@gmail.com",
                "password": "Password1",
            },
        )
        assert resp_email.status_code == 200
        assert "Ya existe una cuenta registrada con ese correo." in resp_email.get_data(as_text=True)

        resp_user = client.post(
            "/auth/register",
            data={
                "username": "sofia_dev",
                "email": "nuevo.usuario@gmail.com",
                "password": "Password1",
            },
        )
        assert resp_user.status_code == 200
        assert "Ese nombre de usuario ya está ocupado." in resp_user.get_data(as_text=True)

def test_register_post_exitoso_crea_usuario_y_rol_estudiante(app, client):
    with app.app_context():
        response = client.post(
            "/auth/register",
            data={
                "username": "sofia_ok",
                "email": "Sofi.123@gmail.com",
                "password": "Password1",
            },
        )
        assert response.status_code == 200
        assert "¡Registro exitoso! Ya podés iniciar sesión." in response.get_data(as_text=True)

        usuario_creado = UsuarioH.query.filter_by(email="sofi.123@gmail.com").first()
        assert usuario_creado is not None
        assert usuario_creado.username == "sofia_ok"
        assert usuario_creado.password_hash != "Password1"
        assert check_password_hash(usuario_creado.password_hash, "Password1")

        rol_estudiante = Rol.query.filter_by(nombre="estudiante").first()
        assert rol_estudiante is not None
        assert usuario_creado.rol_id == rol_estudiante.id


# --- Tests de login y logout ---


def test_login_get_renderiza_formulario(client):
    response = client.get("/auth/login")
    assert response.status_code == 200


def test_login_post_credenciales_invalidas(app, client):
    with app.app_context():
        _crear_usuario_con_password("sofia_ok", "sofia@gmail.com", "Password1")

        resp_vacio = client.post("/auth/login", data={"email": "", "password": ""})
        assert resp_vacio.status_code == 200
        assert "Completá el correo y la contraseña." in resp_vacio.get_data(as_text=True)

        resp_mal_pass = client.post(
            "/auth/login",
            data={"email": "sofia@gmail.com", "password": "Incorrecta1"},
        )
        assert resp_mal_pass.status_code == 200
        assert "Correo o contraseña incorrectos." in resp_mal_pass.get_data(as_text=True)


def test_login_post_exitoso_guarda_sesion(app, client):
    with app.app_context():
        user = _crear_usuario_con_password("sofia_ok", "sofia@gmail.com", "Password1")
        user_id = user.id

        response = client.post(
            "/auth/login",
            data={"email": "SOFIA@gmail.com", "password": "Password1"},
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/foro")

    with client.session_transaction() as sess:
        assert sess.get("usuario_id") == user_id
        assert sess.get("username") == "sofia_ok"


def test_logout_limpia_sesion(app, client):
    with app.app_context():
        user = _crear_usuario_con_password("sofia_ok", "sofia@gmail.com", "Password1")
        user_id = user.id

    with client.session_transaction() as sess:
        sess["usuario_id"] = user_id
        sess["username"] = "sofia_ok"

    response = client.get("/auth/logout")
    assert response.status_code == 200
    assert "Cerraste sesión correctamente." in response.get_data(as_text=True)

    with client.session_transaction() as sess:
        assert "usuario_id" not in sess
        assert "username" not in sess
