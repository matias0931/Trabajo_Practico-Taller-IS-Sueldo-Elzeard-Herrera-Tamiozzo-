import pytest

from taller import create_app
from taller.extensions import db
from taller.models.models import Categoria, Pregunta, Respuesta, Rol, UsuarioH


@pytest.fixture
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _crear_usuario(nombre, email):
    rol = Rol(nombre=f"rol-{nombre}")
    db.session.add(rol)
    db.session.flush()

    usuario = UsuarioH(
        username=nombre,
        email=email,
        password_hash="hash-de-prueba",
        rol_id=rol.id,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario.id


@pytest.fixture
def usuario(app):
    with app.app_context():
        return _crear_usuario("matias", "matias@example.com")


@pytest.fixture
def otro_usuario(app):
    with app.app_context():
        return _crear_usuario("sofia", "sofia@example.com")


@pytest.fixture
def pregunta(app, usuario):
    with app.app_context():
        categoria = Categoria(nombre="Programación")
        db.session.add(categoria)
        db.session.flush()

        pregunta = Pregunta(
            titulo="¿Cómo funciona Flask?",
            cuerpo="Quiero entender el ciclo de un request.",
            usuario_id=usuario,
            categoria_id=categoria.id,
        )
        db.session.add(pregunta)
        db.session.commit()
        return pregunta.id


@pytest.fixture
def respuesta(app, usuario, pregunta):
    with app.app_context():
        respuesta = Respuesta(
            cuerpo="Flask recibe el request y busca una ruta.",
            pregunta_id=pregunta,
            usuario_id=usuario,
        )
        db.session.add(respuesta)
        db.session.commit()
        return respuesta.id
