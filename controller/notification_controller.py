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

    # --- Data Collection from Synthetic CSV ---
    try:
        # Assuming the CSV file is in the root directory of the project
        # In a real application, this path should be configured properly
        df_synthetic = pd.read_csv('synthetic_volunteer_data.csv')
    except FileNotFoundError:
        return jsonify({"sugerencias": [], "mensaje": "No se encontró el archivo de datos sintéticos."}), 500
    except Exception as e:
        # Log the exception e
        return jsonify({"sugerencias": [], "mensaje": f"Error al leer los datos sintéticos: {str(e)}"}), 500

    if df_synthetic.empty:
        return jsonify({"sugerencias": [], "mensaje": "El archivo de datos sintéticos está vacío."})

    # Consider only 'opened' or 'clicked' actions as positive interactions for suggestions
    df_interactions = df_synthetic[df_synthetic['action'].isin(['opened', 'clicked'])]

    if df_interactions.empty:
        return jsonify({"sugerencias": [], "mensaje": "No hay interacciones de 'apertura' o 'clic' en los datos sintéticos."})

    # Convert timestamp to datetime objects and extract hour
    try:
        df_interactions['timestamp'] = pd.to_datetime(df_interactions['timestamp'])
        df_interactions['hour'] = df_interactions['timestamp'].dt.hour
    except Exception as e:
        # Log the exception e
        return jsonify({"sugerencias": [], "mensaje": f"Error al procesar timestamps: {str(e)}"}), 500

    # --- Analysis with Pandas ---
    # Calculate activity frequency per hour based on interactions
    hourly_activity_counts = df_interactions['hour'].value_counts().sort_index()

    # Ensure all hours from 0 to 23 are present, fill missing with 0
    hourly_activity_counts = hourly_activity_counts.reindex(range(24), fill_value=0)

    # Model precision threshold (example, can be adjusted)
    # This is a simplified way to represent "model precision" for this direct analysis.
    # A more complex model would have a proper precision score.
    # Here, we can use the total number of interactions as a proxy for data reliability.
    total_interactions = hourly_activity_counts.sum()
    MIN_INTERACTIONS_THRESHOLD = 10 # Example threshold for "good enough" data

    if total_interactions < MIN_INTERACTIONS_THRESHOLD:
        # This message simulates the original "low precision" error but adapted to new logic
        return jsonify({
            "sugerencias": [],
            "mensaje": f"La cantidad de interacciones procesadas ({total_interactions}) es demasiado baja (umbral: {MIN_INTERACTIONS_THRESHOLD}). No se pueden generar sugerencias confiables."
        })

    # Apply smoothing (e.g., 3-hour rolling window, centered)
    smoothed_activity = hourly_activity_counts.rolling(window=3, center=True, min_periods=1).mean()

    # Group into 2-hour blocks based on smoothed activity
    bi_hourly_smoothed_activity = {}
    for hour_block_start in range(0, 24, 2): # 0, 2, ..., 22
        activity_in_block = smoothed_activity.get(hour_block_start, 0) + smoothed_activity.get(hour_block_start + 1, 0)
        bi_hourly_smoothed_activity[hour_block_start] = activity_in_block

    if not bi_hourly_smoothed_activity:
         return jsonify({"sugerencias": [], "mensaje": "No se pudo procesar la actividad horaria de los voluntarios tras el suavizado."})

    # Sort blocks by activity and get top 3
    sorted_blocks = sorted(bi_hourly_smoothed_activity.items(), key=lambda item: item[1], reverse=True)

    # Filter out blocks with zero smoothed activity before selecting top 3
    # This ensures that we only suggest slots with actual smoothed activity
    significant_blocks = [(hour, activity) for hour, activity in sorted_blocks if activity > 0]
    top_blocks = significant_blocks[:3]

    suggestions = []
    if top_blocks:
        for block_start_hour, count in top_blocks:
            # Format the time slot
            start_time_str = f"{str(block_start_hour).zfill(2)}:00"
            # For the block 22:00-00:00, end time is 00:00 of the next day.
            # Otherwise, it's block_start_hour + 2.
            if block_start_hour == 22:
                end_time_str = "00:00"
            else:
                end_time_str = f"{str(block_start_hour + 2).zfill(2)}:00"

            # Formatting count to 2 decimal places as it's a result of mean (smoothing)
            suggestions.append(f"{start_time_str} - {end_time_str} (Actividad Agregada Estimada: {count:.2f})")

    if not suggestions:
        # This message is more specific if top_blocks was empty or all had zero activity after filtering
        return jsonify({"sugerencias": [], "mensaje": "No se encontraron bloques horarios con actividad voluntaria significativa después del análisis y suavizado."})

    return jsonify({"suggested_slots": suggestions}) # Changed "sugerencias" to "suggested_slots" to match user expectation
