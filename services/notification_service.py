from flask import url_for
from database.db import db
from model.models import Notificaciones, TipoNotificacion, Inscripciones, Actividades, Usuarios, EstadoActividad # Asegurarse que EstadoActividad esté importado

def crear_notificacion_cambio_estado(actividad: Actividades, nuevo_estado: EstadoActividad, antiguo_estado: EstadoActividad):
    """
    Crea notificaciones para los usuarios inscritos cuando el estado de una actividad cambia.
    Solo notifica para ciertos cambios de estado (ej. cancelada, finalizada).
    """
    if antiguo_estado == nuevo_estado:
        # print(f"Actividad {actividad.id_actividad}: Sin cambio de estado real ({antiguo_estado} -> {nuevo_estado}). No se envían notificaciones.")
        return

    mensaje_base = f"La actividad '{actividad.nombre}'"
    mensaje_especifico = ""
    notificar = False

    if nuevo_estado == EstadoActividad.CANCELADA:
        mensaje_especifico = "ha sido cancelada."
        notificar = True
    elif nuevo_estado == EstadoActividad.FINALIZADA:
        mensaje_especifico = "ha finalizado. ¡Gracias por tu interés y/o participación!"
        notificar = True
    # Podríamos añadir otros casos, como cambio de fecha/hora si tuviéramos esa info.
    # elif nuevo_estado == EstadoActividad.CERRADO and antiguo_estado == EstadoActividad.ABIERTO:
    #     mensaje_especifico = "ha cerrado sus inscripciones." # Ejemplo, decidir si esto es notificable
    #     notificar = True

    if not notificar:
        # print(f"Actividad {actividad.id_actividad}: Cambio de estado de {antiguo_estado.value} a {nuevo_estado.value} no configurado para notificación masiva.")
        return

    mensaje_completo = f"{mensaje_base} {mensaje_especifico}"

    # Obtener usuarios inscritos
    # Es importante filtrar por inscripciones activas si existiera tal concepto,
    # pero el modelo actual no lo tiene, así que notificamos a todos los que alguna vez se inscribieron.
    inscripciones = Inscripciones.query.filter_by(id_actividad=actividad.id_actividad).all()

    if not inscripciones:
        # print(f"Actividad {actividad.id_actividad}: No hay usuarios inscritos para notificar el cambio a {nuevo_estado.value}.")
        return

    # Usar un try-except block para la generación de la URL en caso de que se llame fuera de un contexto de request
    # Sin embargo, esta función se llamará desde una ruta, por lo que url_for debería funcionar.
    try:
        url_destino = url_for('program.view_program_detail', program_id=actividad.id_actividad, _external=False) # _external=True si es para emails
    except RuntimeError:
        # print("Error: No se pudo generar url_destino fuera del contexto de la aplicación o solicitud.")
        url_destino = f"/program/{actividad.id_actividad}" # Fallback URL

    notificaciones_a_crear = []
    for inscripcion in inscripciones:
        # Opcional: Verificar si el usuario ya tiene una notificación idéntica reciente para evitar duplicados.
        # Por ahora, se asume que los cambios de estado son eventos únicos que merecen su propia notificación.
        notificacion = Notificaciones(
            id_usuario=inscripcion.id_usuario,
            mensaje=mensaje_completo,
            tipo=TipoNotificacion.CAMBIO_ESTADO_ACTIVIDAD,
            prioridad='alta' if nuevo_estado == EstadoActividad.CANCELADA else 'media',
            url_destino=url_destino
        )
        notificaciones_a_crear.append(notificacion)

    if notificaciones_a_crear:
        try:
            db.session.add_all(notificaciones_a_crear)
            db.session.commit()
            # print(f"Creadas {len(notificaciones_a_crear)} notificaciones por cambio de estado de actividad {actividad.id_actividad} a {nuevo_estado.value}.")
        except Exception as e:
            db.session.rollback()
            # print(f"Error haciendo commit de notificaciones para actividad {actividad.id_actividad}: {e}")
            # Considerar loggear el error (e.g., current_app.logger.error(...))
            pass # Evitar que una falla aquí rompa el flujo principal de cambio de estado.

    return len(notificaciones_a_crear)
