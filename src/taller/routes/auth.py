from flask import Blueprint
bp = Blueprint("auth", __name__, url_prefix="/auth")
from flask import Blueprint, render_template, request
from werkzeug.security import generate_password_hash
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

    # 4. Verificar que el Gmail no esté registrado ya
    if UsuarioH.query.filter_by(email=email).first():
        return render_template("register.html", error="Ya existe una cuenta registrada con ese correo de Gmail.")

    # 5. Verificar que el nombre de usuario no esté en uso
    if UsuarioH.query.filter_by(username=username).first():
        return render_template("register.html", error="Ese nombre de usuario ya está ocupado.")

    # 6. Obtener o crear el rol 'estudiante' (porque rol_id es obligatorio en UsuarioH)
    rol_estudiante = Rol.query.filter_by(nombre="estudiante").first()
    if not rol_estudiante:
        rol_estudiante = Rol(nombre="estudiante")
        db.session.add(rol_estudiante)
        db.session.flush()  # Genera el id del rol sin cerrar todavía la transacción

    # 7. Crear el usuario con la contraseña hasheada y guardar en SQLite
    nuevo_usuario = UsuarioH(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        rol_id=rol_estudiante.id,
    )
    db.session.add(nuevo_usuario)
    db.session.commit()

    return render_template("register.html", success="¡Registro exitoso! Ya podés iniciar sesión.")
