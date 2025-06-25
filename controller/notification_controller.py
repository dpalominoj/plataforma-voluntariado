# controller/notification_controller.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from database.db import db
from model.models import Notificaciones, Usuarios, Inscripciones, InteraccionesChatbot # Asegurarse que SQLAlchemy y func están disponibles si se usan aquí
from sqlalchemy import desc, func # Importar func para counts, desc para ordenar
from sqlalchemy.sql.expression import extract
from collections import Counter
import pandas as pd # Import pandas

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
                           unread_count=unread_count,
                           request=request)


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
        return jsonify({"error": "Acceso no autorizado"}), 403

    # --- Data Collection for Volunteers ---
    volunteer_activity_timestamps = []

    # 1. Registros de Usuarios Voluntarios
    # Assuming 'voluntario' is the string identifier for the volunteer profile in the Usuarios model
    volunteer_registrations = db.session.query(Usuarios.fecha_registro)\
                                      .filter(Usuarios.perfil == 'voluntario').all()
    for reg_time, in volunteer_registrations:
        if reg_time:
            volunteer_activity_timestamps.append(reg_time)

    # 2. Inscripciones a Actividades por Voluntarios
    # Join Inscripciones with Usuarios to filter by volunteer profile
    volunteer_inscriptions = db.session.query(Inscripciones.fecha_inscripcion)\
                                     .join(Usuarios, Inscripciones.id_usuario == Usuarios.id_usuario)\
                                     .filter(Usuarios.perfil == 'voluntario').all()
    for insc_time, in volunteer_inscriptions:
        if insc_time:
            volunteer_activity_timestamps.append(insc_time)

    # 3. Notificaciones Leídas por Voluntarios
    # Join Notificaciones with Usuarios to filter by volunteer profile
    read_notifications_by_volunteers = db.session.query(Notificaciones.fecha_envio)\
                                                 .join(Usuarios, Notificaciones.id_usuario == Usuarios.id_usuario)\
                                                 .filter(Usuarios.perfil == 'voluntario', Notificaciones.leida == True).all()
    for notif_time, in read_notifications_by_volunteers:
        if notif_time: # Using fecha_envio as proxy for read time
            volunteer_activity_timestamps.append(notif_time)

    # 4. Interacciones con Chatbot por Voluntarios
    # Join InteraccionesChatbot with Usuarios to filter by volunteer profile
    chatbot_interactions_by_volunteers = db.session.query(InteraccionesChatbot.fecha)\
                                                  .join(Usuarios, InteraccionesChatbot.id_usuario == Usuarios.id_usuario)\
                                                  .filter(Usuarios.perfil == 'voluntario').all()
    for chat_time, in chatbot_interactions_by_volunteers:
        if chat_time:
            volunteer_activity_timestamps.append(chat_time)

    if not volunteer_activity_timestamps:
        return jsonify({"sugerencias": [], "mensaje": "No hay suficientes datos de actividad de voluntarios para generar sugerencias."})

    # --- Analysis with Pandas ---
    df = pd.DataFrame(volunteer_activity_timestamps, columns=['timestamp'])
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour

    # Calculate activity frequency per hour
    hourly_activity_counts = df['hour'].value_counts().sort_index()

    # Ensure all hours from 0 to 23 are present for smoothing, fill missing with 0
    hourly_activity_counts = hourly_activity_counts.reindex(range(24), fill_value=0)

    if hourly_activity_counts.sum() == 0: # Should be caught by the earlier check, but as a safeguard
        return jsonify({"sugerencias": [], "mensaje": "No hay actividad de voluntarios registrada para generar sugerencias."})

    # Apply smoothing (e.g., 3-hour rolling window, centered)
    # The window size can be adjusted. min_periods=1 ensures edges are not all NaN.
    smoothed_activity = hourly_activity_counts.rolling(window=3, center=True, min_periods=1).mean()

    # Group into 2-hour blocks based on smoothed activity
    # We'll sum the smoothed activity for each 2-hour block
    bi_hourly_smoothed_activity = {}
    for hour in range(0, 24, 2): # 0, 2, ..., 22
        # Sum smoothed activity for the two hours in the block
        # e.g., for block 0 (00:00-02:00), sum smoothed_activity[0] and smoothed_activity[1]
        block_activity = smoothed_activity.get(hour, 0) + smoothed_activity.get(hour + 1, 0)
        bi_hourly_smoothed_activity[hour] = block_activity

    if not bi_hourly_smoothed_activity:
         return jsonify({"sugerencias": [], "mensaje": "No se pudo procesar la actividad horaria de los voluntarios."})

    # Sort blocks by activity and get top 3
    # Convert to list of tuples (hour, count) for sorting
    sorted_blocks = sorted(bi_hourly_smoothed_activity.items(), key=lambda item: item[1], reverse=True)
    top_blocks = sorted_blocks[:3]

    suggestions = []
    if top_blocks:
        for block_start_hour, count in top_blocks:
            if count > 0: # Only suggest if there's some smoothed activity
                start_time = f"{str(block_start_hour).zfill(2)}:00"
                if block_start_hour == 22:
                    end_time = "00:00"
                else:
                    end_time = f"{str(block_start_hour + 2).zfill(2)}:00"
                # Formatting count to 2 decimal places as it's a result of mean
                suggestions.append(f"{start_time} - {end_time} (Actividad Voluntaria Agregada: {count:.2f})")

    if not suggestions:
        return jsonify({"sugerencias": [], "mensaje": "No se encontraron bloques horarios con actividad voluntaria significativa después del análisis."})

    return jsonify({"sugerencias": suggestions})
