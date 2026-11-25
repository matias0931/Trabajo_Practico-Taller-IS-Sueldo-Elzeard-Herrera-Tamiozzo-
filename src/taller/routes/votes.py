from flask import Blueprint, flash, jsonify, redirect, request, session

from ..extensions import db
from ..models.models import Pregunta, Respuesta, UsuarioH, Voto

bp = Blueprint("votes", __name__, url_prefix="/votes")


def usuario_id_actual():
    """Devuelve el id del usuario logueado o None.

    El login guarda el id en session["usuario_id"]. Si más adelante se cambia
    el mecanismo de autenticación, este es el único lugar que hay que tocar.
    """
    return session.get("usuario_id")


def _usuario_actual():
    """Busca al usuario de la sesión y devuelve None si no existe."""
    usuario_id = usuario_id_actual()
    if usuario_id is None:
        return None

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return None

    return db.session.get(UsuarioH, usuario_id)


def _quiere_json():
    """Indica si la respuesta debe ser JSON en lugar de un redirect HTML."""
    return request.is_json or request.accept_mimetypes.best == "application/json"


def _error(mensaje, codigo):
    """Devuelve el error en JSON o redirige con un mensaje flash."""
    if _quiere_json() or not request.referrer:
        return jsonify({"error": mensaje}), codigo

    flash(mensaje, "error")
    return redirect(request.referrer)


def _valor_recibido():
    """Lee el valor del voto desde JSON o desde un formulario HTML."""
    datos = request.get_json(silent=True) if request.is_json else request.form
    if not datos:
        return None

    try:
        return int(datos.get("valor"))
    except (TypeError, ValueError):
        return None


def _aplicar_voto(usuario_id, valor, pregunta=None, respuesta=None):
    """Crea, actualiza o elimina el voto de un usuario sobre un elemento."""
    filtro = {"usuario_id": usuario_id}
    if pregunta is not None:
        filtro["pregunta_id"] = pregunta.id
    else:
        filtro["respuesta_id"] = respuesta.id

    voto = Voto.query.filter_by(**filtro).first()

    if voto is None:
        # 1. Todavía no votó: se crea el voto.
        voto = Voto(
            usuario_id=usuario_id,
            valor=valor,
            pregunta_id=pregunta.id if pregunta is not None else None,
            respuesta_id=respuesta.id if respuesta is not None else None,
        )
        db.session.add(voto)
        accion = "registrado"
    elif voto.valor == valor:
        # 2. Ya votó lo mismo: se elimina el voto (toggle).
        db.session.delete(voto)
        voto = None
        accion = "eliminado"
    else:
        # 3. Ya votó lo contrario: se actualiza el voto.
        voto.valor = valor
        accion = "actualizado"

    db.session.commit()
    return voto, accion


def _resumen_votos(usuario_id, pregunta=None, respuesta=None):
    """Cuenta los votos de una pregunta o respuesta."""
    if pregunta is not None:
        filtro = {"pregunta_id": pregunta.id}
    else:
        filtro = {"respuesta_id": respuesta.id}

    positivos = Voto.query.filter_by(**filtro, valor=1).count()
    negativos = Voto.query.filter_by(**filtro, valor=-1).count()
    mi_voto = Voto.query.filter_by(**filtro, usuario_id=usuario_id).first()

    return {
        "positivos": positivos,
        "negativos": negativos,
        "total": positivos + negativos,
        "puntaje": positivos - negativos,
        "mi_voto": mi_voto.valor if mi_voto is not None else None,
    }


def _responder_voto(voto, accion, usuario_id, pregunta=None, respuesta=None):
    """Devuelve el resultado en JSON o redirige al formulario HTML."""
    resumen = _resumen_votos(usuario_id, pregunta=pregunta, respuesta=respuesta)
    datos = {
        "ok": True,
        "accion": accion,
        "voto": {"id": voto.id, "valor": voto.valor} if voto is not None else None,
        **resumen,
    }

    if _quiere_json() or not request.referrer:
        return jsonify(datos)

    mensajes = {
        "registrado": "Voto registrado.",
        "actualizado": "Voto actualizado.",
        "eliminado": "Voto eliminado.",
    }
    flash(mensajes[accion], "success")
    return redirect(request.referrer)


@bp.post("/questions/<int:pregunta_id>")
def votar_pregunta(pregunta_id):
    # 1. Verificar que haya un usuario logueado.
    usuario = _usuario_actual()
    if usuario is None:
        return _error("Debés iniciar sesión para votar.", 401)

    # 2. Validar el valor del voto.
    valor = _valor_recibido()
    if valor not in (-1, 1):
        return _error("El voto debe ser 1 o -1.", 400)

    # 3. Verificar que la pregunta exista.
    pregunta = db.session.get(Pregunta, pregunta_id)
    if pregunta is None:
        return _error("La pregunta no existe.", 404)

    # 4. Registrar, actualizar o eliminar el voto.
    voto, accion = _aplicar_voto(usuario.id, valor, pregunta=pregunta)
    return _responder_voto(voto, accion, usuario.id, pregunta=pregunta)


@bp.post("/answers/<int:respuesta_id>")
def votar_respuesta(respuesta_id):
    # 1. Verificar que haya un usuario logueado.
    usuario = _usuario_actual()
    if usuario is None:
        return _error("Debés iniciar sesión para votar.", 401)

    # 2. Validar el valor del voto.
    valor = _valor_recibido()
    if valor not in (-1, 1):
        return _error("El voto debe ser 1 o -1.", 400)

    # 3. Verificar que la respuesta exista.
    respuesta = db.session.get(Respuesta, respuesta_id)
    if respuesta is None:
        return _error("La respuesta no existe.", 404)

    # 4. Registrar, actualizar o eliminar el voto.
    voto, accion = _aplicar_voto(usuario.id, valor, respuesta=respuesta)
    return _responder_voto(voto, accion, usuario.id, respuesta=respuesta)
