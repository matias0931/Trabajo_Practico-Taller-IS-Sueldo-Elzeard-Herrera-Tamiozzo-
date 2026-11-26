from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import re
from ..extensions import db
from ..models.models import Rol, UsuarioH

bp = Blueprint("auth", __name__, url_prefix="/auth")


def validar_password(password: str) -> str | None:
    """Devuelve un mensaje de error si la contraseña no cumple las reglas, o None si es válida."""
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not any(c.isdigit() for c in password):
        return "La contraseña debe incluir al menos un dígito."
    if not any(c.isupper() for c in password):
        return "La contraseña debe incluir al menos una letra mayúscula."
    return None


@bp.get("/register")
def register_get():
    return render_template("register.html")


@bp.post("/register")
def register_post():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    # 1. Validar que vengan todos los campos
    if not username or not email or not password:
        return render_template("register.html", error="Todos los campos son obligatorios.")

    # 2. Validar correo (sin caracteres especiales, con al menos una letra y dominios permitidos)
    patron_email = r"^(?=.*[a-z])[a-z0-9.]{6,30}@(gmail\.com|hotmail\.com|outlook\.com|outlook\.es)$"
    if not re.match(patron_email, email):
        return render_template(
            "register.html",
            error="Correo inválido. No uses caracteres especiales y elegí un dominio permitido (@gmail.com, @hotmail.com, @outlook.com o @outlook.es)."
        )

    # 3. Validar seguridad de la contraseña
    error_pass = validar_password(password)
    if error_pass:
        return render_template("register.html", error=error_pass)

    # 4. Verificar que el correo no esté registrado ya
    if UsuarioH.query.filter_by(email=email).first():
        return render_template("register.html", error="Ya existe una cuenta registrada con ese correo.")

    # 5. Verificar que el nombre de usuario no esté en uso
    if UsuarioH.query.filter_by(username=username).first():
        return render_template("register.html", error="Ese nombre de usuario ya está ocupado.")

    # 6. Obtener o crear el rol 'estudiante'
    rol_estudiante = Rol.query.filter_by(nombre="estudiante").first()
    if not rol_estudiante:
        rol_estudiante = Rol(nombre="estudiante")
        db.session.add(rol_estudiante)
        db.session.flush()

    # 7. Crear el usuario con la contraseña hasheada y guardar en SQLite
    nuevo_usuario = UsuarioH(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        rol_id=rol_estudiante.id,
    )
    db.session.add(nuevo_usuario)
    db.session.commit()

    return redirect(url_for("auth.login_get"))


@bp.get("/login")
def login_get():
    return render_template("login.html")


@bp.post("/login")
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Completá el correo y la contraseña.")

    usuario = UsuarioH.query.filter_by(email=email).first()

    if not usuario or not check_password_hash(usuario.password_hash, password):
        return render_template("login.html", error="Correo o contraseña incorrectos.")

    session["usuario_id"] = usuario.id
    session["username"] = usuario.username

    return redirect(url_for("foro"))


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
    
@bp.route("/")
def index():
    return render_template("index.html")
    
  
