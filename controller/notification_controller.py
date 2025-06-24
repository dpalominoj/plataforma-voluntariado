# controller/notification_controller.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from database.db import db
from model.models import Notificaciones # Asegurarse que SQLAlchemy y func están disponibles si se usan aquí
from sqlalchemy import desc, func # Importar func para counts, desc para ordenar

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
