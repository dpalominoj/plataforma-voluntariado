# controller/notification_controller.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from database.db import db
from model.models import Notificaciones, Usuarios, Inscripciones, InteraccionesChatbot # Asegurarse que SQLAlchemy y func están disponibles si se usan aquí
from sqlalchemy import desc, func # Importar func para counts, desc para ordenar
from sqlalchemy.sql.expression import extract
from collections import Counter

notifications_bp = Blueprint('notifications', __name__,
                             template_folder='../view/templates/notifications',
                             url_prefix='/notifications')

@notifications_bp.route('/redirect/<int:notification_id>')
@login_required
def redirect_and_mark_read(notification_id):
    notification = Notificaciones.query.filter_by(id_notificacion=notification_id, id_usuario=current_user.id_usuario).first_or_404()

    if not notification.leida:
        notification.leida = True
        db.session.commit()

    # Priorizar url_destino de la notificación. Si no existe, ir a un default.
    target_url = notification.url_destino
    if not target_url: # Si url_destino es None o vacío
        flash("Notificación marcada como leída. No había un destino específico.", "info")
        target_url = url_for('notifications.list_all') # O 'user_dashboard.dashboard'

    return redirect(target_url)


@notifications_bp.route('/mark_read/<int:notification_id>')
@login_required
def mark_as_read(notification_id):
    notification = Notificaciones.query.filter_by(id_notificacion=notification_id, id_usuario=current_user.id_usuario).first_or_404()

    if not notification.leida:
        notification.leida = True
        db.session.commit()
        flash("Notificación marcada como leída.", "success")
    else:
        flash("La notificación ya estaba marcada como leída.", "info")

    # Redirigir a 'next' si está presente, sino a la lista de notificaciones.
    next_url = request.args.get('next', url_for('notifications.list_all'))
    return redirect(next_url)


@notifications_bp.route('/')
@login_required
def list_all():
    page = request.args.get('page', 1, type=int)

    # Paginar todas las notificaciones del usuario, más recientes primero.
    notifications_page = Notificaciones.query.filter_by(id_usuario=current_user.id_usuario)\
                                        .order_by(Notificaciones.leida.asc(), Notificaciones.fecha_envio.desc())\
                                        .paginate(page=page, per_page=10, error_out=False)

    # Contar no leídas para mostrar en la página si es necesario
    unread_count = Notificaciones.query.filter_by(id_usuario=current_user.id_usuario, leida=False).count()

    return render_template('list_notifications.html',
                           title="Centro de Notificaciones",
                           notifications_page=notifications_page,
                           unread_count=unread_count)


@notifications_bp.route('/mark_all_read', methods=['POST']) # Usar POST para acciones que cambian estado
@login_required
def mark_all_as_read():
    # Verificar que la solicitud sea POST, aunque @notifications_bp.route ya lo hace
    if request.method == 'POST':
        try:
            updated_count = Notificaciones.query.filter_by(id_usuario=current_user.id_usuario, leida=False)\
                                .update({Notificaciones.leida: True}, synchronize_session='fetch')
            db.session.commit()
            if updated_count > 0:
                flash(f"{updated_count} notificaciones han sido marcadas como leídas.", "success")
            else:
                flash("No había notificaciones nuevas para marcar como leídas.", "info")
        except Exception as e:
            db.session.rollback()
            flash("Error al marcar todas las notificaciones como leídas.", "danger")
            # Considerar loggear (e.g. current_app.logger.error(str(e)))
            print(f"Error en mark_all_as_read: {str(e)}")
    else:
        # Si alguien intenta acceder vía GET, redirigir o abortar
        return redirect(url_for('notifications.list_all'))

    return redirect(url_for('notifications.list_all'))

@notifications_bp.route('/api/sugerir_horario', methods=['GET'])
@login_required
def api_sugerir_horario():
    if current_user.perfil != 'organizador':
        # Aunque un voluntario podría llamar a esta API, la sugerencia es para el organizador.
        # Podríamos devolver un error o simplemente datos vacíos/genéricos si no es organizador.
        # Por ahora, restrinjamos al organizador ya que la funcionalidad está pensada para ellos.
        return jsonify({"error": "Acceso no autorizado"}), 403

    hourly_activity = Counter()

    # 1. Registros de Usuarios
    user_registration_hours = db.session.query(extract('hour', Usuarios.fecha_registro)).all()
    for hour_tuple in user_registration_hours:
        if hour_tuple[0] is not None:
            hourly_activity[hour_tuple[0]] += 1

    # 2. Inscripciones a Actividades
    inscription_hours = db.session.query(extract('hour', Inscripciones.fecha_inscripcion)).all()
    for hour_tuple in inscription_hours:
        if hour_tuple[0] is not None:
            hourly_activity[hour_tuple[0]] += 1

    # 3. Notificaciones Leídas (usando fecha_envio de notificaciones leídas como proxy)
    #    Esto asume que la lectura ocurre relativamente cerca del envío.
    #    Si hubiera una `fecha_leida`, sería más preciso.
    read_notification_hours = db.session.query(extract('hour', Notificaciones.fecha_envio))\
                                      .filter(Notificaciones.leida == True).all()
    for hour_tuple in read_notification_hours:
        if hour_tuple[0] is not None:
            hourly_activity[hour_tuple[0]] += 1

    # 4. Interacciones con Chatbot
    chatbot_interaction_hours = db.session.query(extract('hour', InteraccionesChatbot.fecha)).all()
    for hour_tuple in chatbot_interaction_hours:
        if hour_tuple[0] is not None:
            hourly_activity[hour_tuple[0]] += 1

    if not hourly_activity:
        return jsonify({"sugerencias": [], "mensaje": "No hay suficientes datos para generar sugerencias."})

    # Obtener las 3 horas más activas
    # Counter.most_common(n) devuelve una lista de tuplas (elemento, conteo)
    top_hours = hourly_activity.most_common(3)

    suggestions = []
    for hour, count in top_hours:
        # Formatear como rango de una hora, ej: "08:00 - 09:00"
        suggestions.append(f"{str(hour).zfill(2)}:00 - {str(hour+1 if hour < 23 else 0).zfill(2)}:00 (Actividad: {count})")

    # Considerar agrupar en bloques de 2 horas si es más útil
    # Ejemplo de lógica para agrupar en bloques de 2 horas (más complejo):
    # bi_hourly_activity = Counter()
    # for hour, count in hourly_activity.items():
    #    block_start_hour = (hour // 2) * 2 # 0, 2, 4...
    #    bi_hourly_activity[block_start_hour] += count
    # top_bi_hourly = bi_hourly_activity.most_common(3)
    # suggestions_bi_hourly = []
    # for block_start, count in top_bi_hourly:
    #    suggestions_bi_hourly.append(f"{str(block_start).zfill(2)}:00 - {str(block_start+2).zfill(2)}:00 (Actividad: {count})")
    # return jsonify({"sugerencias": suggestions_bi_hourly})


    return jsonify({"sugerencias": suggestions})
