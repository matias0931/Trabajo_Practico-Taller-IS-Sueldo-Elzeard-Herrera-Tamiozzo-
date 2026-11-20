from datetime import datetime, timezone
from ..extensions import db

# Tabla intermedia muchos-a-muchos entre Pregunta y Tag
pregunta_tags = db.Table(
    "pregunta_tags",
    db.Column("pregunta_id", db.Integer, db.ForeignKey("preguntas.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)

class Rol(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)  # ej. 'estudiante', 'admin'
    usuarios = db.relationship("UsuarioH", backref="rol", lazy=True)

class UsuarioH(db.Model):
    __tablename__ = "usuarios_h"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    preguntas = db.relationship("Pregunta", backref="autor", lazy=True)
    respuestas = db.relationship("Respuesta", backref="autor", lazy=True)
    votos = db.relationship("Voto", backref="usuario", lazy=True)

class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    preguntas = db.relationship("Pregunta", backref="categoria", lazy=True)

class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

class Pregunta(db.Model):
    __tablename__ = "preguntas"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    cuerpo = db.Column(db.Text, nullable=False)
    creada_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios_h.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)

    respuestas = db.relationship("Respuesta", backref="pregunta", lazy=True, cascade="all, delete-orphan")
    votos = db.relationship("Voto", backref="pregunta", lazy=True, cascade="all, delete-orphan")
    tags = db.relationship("Tag", secondary=pregunta_tags, lazy="subquery", backref=db.backref("preguntas", lazy=True))

class Respuesta(db.Model):
    __tablename__ = "respuestas"
    id = db.Column(db.Integer, primary_key=True)
    cuerpo = db.Column(db.Text, nullable=False)
    es_ia = db.Column(db.Boolean, default=False, nullable=False)
    aceptada = db.Column(db.Boolean, default=False, nullable=False)
    creada_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    pregunta_id = db.Column(db.Integer, db.ForeignKey("preguntas.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios_h.id"), nullable=True)  # Nullable si es respuesta de IA

    votos = db.relationship("Voto", backref="respuesta", lazy=True, cascade="all, delete-orphan")

class Voto(db.Model):
    __tablename__ = "votos"
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Integer, nullable=False)  # +1 o -1
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios_h.id"), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("preguntas.id"), nullable=True)
    respuesta_id = db.Column(db.Integer, db.ForeignKey("respuestas.id"), nullable=True)
