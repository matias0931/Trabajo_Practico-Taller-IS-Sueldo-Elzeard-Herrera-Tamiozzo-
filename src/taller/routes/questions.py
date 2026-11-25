from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

# Importa db y los modelos según la estructura de tu proyecto
# (Por ejemplo: from taller.models import db, Pregunta, Categoria, Tag)
from ..extensions import db
from ..models import Categoria, Pregunta, Tag

bp = Blueprint("questions", __name__, url_prefix="/questions")


@bp.post("/")
def create_question():
  data = request.get_json(silent=True) or {}

  # 1. Obtener y limpiar datos de la petición
  titulo = data.get("title") or data.get("titulo")
  cuerpo = data.get("body") or data.get("cuerpo")
  categoria_id = data.get("category_id") or data.get("categoria_id")
  tag_ids_o_nombres = data.get("tags", [])
  usuario_id = data.get("user_id") or data.get(
      "usuario_id"
  )  # O desde la sesión/token JWT del estudiante

  errors = []

  # 2. Validaciones según Criterios de Aceptación del Issue #2
  if not titulo or not isinstance(titulo, str) or len(titulo.strip()) <= 5:
    errors.append("El título es obligatorio y debe tener más de 5 caracteres.")

  if not cuerpo or not isinstance(cuerpo, str) or len(cuerpo.strip()) <= 5:
    errors.append(
        "El cuerpo descriptivo es obligatorio y debe tener más de 5"
        " caracteres."
    )

  if not categoria_id:
    errors.append("La pregunta debe estar asociada a una categoría.")
  else:
    # Verificar existencia de la categoría
    categoria_existente = Categoria.query.get(categoria_id)
    if not categoria_existente:
      errors.append(
          f"La categoría con ID {categoria_id} no existe en la base de datos."
      )

  if not usuario_id:
    errors.append("Debe indicarse el ID del usuario/estudiante que publica.")

  if errors:
    return jsonify({"errors": errors}), 400

  # 3. Procesar las etiquetas (Tags)
  tags_asociados = []
  if isinstance(tag_ids_o_nombres, list):
    for item in tag_ids_o_nombres:
      if isinstance(item, int):
        tag_obj = Tag.query.get(item)
        if tag_obj:
          tags_asociados.append(tag_obj)
      elif isinstance(item, str) and item.strip():
        # Si envían nombres de tags, se busca o se crea
        nombre_tag = item.strip()
        tag_obj = Tag.query.filter_by(nombre=nombre_tag).first()
        if not tag_obj:
          tag_obj = Tag(nombre=nombre_tag)
          db.session.add(tag_obj)
        tags_asociados.append(tag_obj)

  # 4. Crear la entidad Pregunta y guardar en DB
  nueva_pregunta = Pregunta(
      titulo=titulo.strip(),
      cuerpo=cuerpo.strip(),
      categoria_id=categoria_id,
      usuario_id=usuario_id,
      tags=tags_asociados,
      # creada_en toma el valor default definido en el modelo
  )

  try:
    db.session.add(nueva_pregunta)
    db.session.commit()
  except Exception as e:
    db.session.rollback()
    return (
        jsonify({
            "error": "Error interno al guardar la pregunta.",
            "details": str(e),
        }),
        500,
    )

  # 5. Respuesta JSON formateada
  return (
      jsonify({
          "id": nueva_pregunta.id,
          "titulo": nueva_pregunta.titulo,
          "cuerpo": nueva_pregunta.cuerpo,
          "creada_en": nueva_pregunta.creada_en.isoformat(),
          "categoria_id": nueva_pregunta.categoria_id,
          "usuario_id": nueva_pregunta.usuario_id,
          "tags": [t.nombre for t in nueva_pregunta.tags],
      }),
      201,
  )
