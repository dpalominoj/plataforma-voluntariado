from flask import Blueprint, render_template, flash, redirect, url_for, current_app, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from model.models import UsuarioDiscapacidad, Discapacidades, Inscripciones, Actividades, Usuarios, EstadoActividad, EstadoUsuario, Organizaciones
from database.db import db
from services.participation_service import predecir_participacion
from services.compatibility_service import get_compatibility_scores
from services.rangohorario_service import PredictionService

dashboard_bp = Blueprint('user_dashboard', __name__,
                         template_folder='../view/templates/dashboards',
                         url_prefix='/dashboard')

def _get_participation_indicator_info(prediction_output):
    indicator = '⚪' # Indicador por defecto: círculo blanco
    indicator_text = 'Predicción no disponible'

    if prediction_output:
        if 'error' not in prediction_output and 'probabilidad' in prediction_output:
            prob = prediction_output.get('probabilidad')
            if prob is None:
                indicator = 'No se pudo calcular probabilidad'
                indicator_text = 'Probabilidad no calculada (datos insuficientes)'
            elif prob < 0.3:
                indicator = '🔴' # Círculo rojo para baja participación
                indicator_text = f"Baja participación (Prob: {prob:.2f})"
            elif prob < 0.7:
                indicator = '🟠' # Círculo naranja para participación moderada
                indicator_text = f"Participación moderada (Prob: {prob:.2f})"
            else:
                indicator = '🟢' # Círculo verde para alta participación
                indicator_text = f"Alta participación (Prob: {prob:.2f})"
        elif 'error' in prediction_output:
            indicator_text = prediction_output['error']
        elif 'info' in prediction_output:
            indicator_text = prediction_output['info']
    
    return indicator, indicator_text

@dashboard_bp.route('/')
@login_required
def dashboard():
    # Redirige al panel de control según perfil.
    if current_user.perfil == 'administrador':
        total_users = Usuarios.query.count()
        total_programs = Actividades.query.count()
        return render_template('admin_dashboard.html', title="Panel de Administrador", total_users=total_users, total_programs=total_programs)
    elif current_user.perfil == 'organizador':
        organizer_org_ids = [org.id_organizacion for org in current_user.organizaciones]
        created_programs_query = []
        if organizer_org_ids:
            created_programs_query = Actividades.query.filter(Actividades.id_organizacion.in_(organizer_org_ids)) \
                                               .order_by(Actividades.fecha_actividad.desc()) \
                                               .all()
        
        # Procesamiento de actividades creadas por el organizador para mostrar predicción de participación
        actividades_con_prediccion = []
        for actividad in created_programs_query:
            prediction_output = predecir_participacion(actividad.id_actividad)
            # Utilizar la función auxiliar para obtener el indicador y el texto
            indicator, indicator_text = _get_participation_indicator_info(prediction_output)

            actividades_con_prediccion.append({
                'actividad': actividad,
                'indicador': indicator,
                'texto_indicador': indicator_text,
                'metricas': prediction_output.get('metricas') if prediction_output else None,
                'tree_dot_file': prediction_output.get('tree_dot_file') if prediction_output else None
            })

        member_organizations = current_user.organizaciones

        organizer_primary_org_id = None
        if current_user.organizaciones:
            first_org = current_user.organizaciones[0]
            organizer_primary_org_id = first_org.id_organizacion


        suggested_notification_times = "No hay sugerencias de horarios disponibles en este momento." # Default message
        if organizer_primary_org_id is not None: # Asegurarse de que hay una organización
            try:
                # El constructor de PredictionService ya no toma 'threshold'
                prediction_service = PredictionService()
                # Pasamos organizer_primary_org_id aunque el servicio actualmente no lo usa
                # para la lógica del CSV, pero podría ser útil para futuras mejoras o logging.
                suggested_times_result = prediction_service.get_optimal_time_slots(
                    organizer_id=organizer_primary_org_id
                )

                # suggested_times_result ahora es una lista de diccionarios (si tiene éxito)
                # o un string (si hay error o mensaje informativo).
                if isinstance(suggested_times_result, str):
                    # Es un mensaje de error/info del servicio (e.g., datos insuficientes, error de archivo)
                    suggested_notification_times = suggested_times_result
                elif isinstance(suggested_times_result, list) and suggested_times_result:
                    # Es una lista de slots, la pasamos directamente
                    suggested_notification_times = suggested_times_result
                # Si suggested_times_result es una lista vacía, el mensaje por defecto
                # "No hay sugerencias de horarios disponibles en este momento." se mantendrá,
                # lo cual es un comportamiento aceptable.
                # Opcionalmente, podríamos poner un mensaje más específico si la lista está vacía:
                # elif isinstance(suggested_times_result, list) and not suggested_times_result:
                #     suggested_notification_times = "No se encontraron bloques horarios con actividad significativa."

            except Exception as e:
                current_app.logger.error(f"Excepción crítica al obtener horarios sugeridos para organizador {current_user.id_usuario} (org_id {organizer_primary_org_id}): {e}")
                # Mantener el mensaje por defecto en caso de excepción no controlada por el servicio
                # o asignar uno específico de error si se prefiere.
                suggested_notification_times = "Error al calcular las sugerencias de horarios."

        return render_template('organizer_dashboard.html',
                               title="Panel de Organizador",
                               created_programs_con_prediccion=actividades_con_prediccion,
                               member_organizations=member_organizations,
                               suggested_notification_times=suggested_notification_times)
    elif current_user.perfil == 'voluntario':
        user_enrollments = db.session.query(Inscripciones, Actividades) \
                            .join(Actividades, Inscripciones.id_actividad == Actividades.id_actividad) \
                            .filter(Inscripciones.id_usuario == current_user.id_usuario) \
                            .order_by(Inscripciones.fecha_inscripcion.desc()) \
                            .all()

     
        actividades_abiertas = Actividades.query.options(
                                    joinedload(Actividades.discapacidades), # Carga la colección de objetos Discapacidad asociados a la Actividad
                                    joinedload(Actividades.organizacion)   # Carga la Organización de la Actividad
                                 ).filter_by(estado=EstadoActividad.ABIERTO).all()
        
        # Lista para almacenar las actividades abiertas junto con su información combinada (compatibilidad y participación)
        actividades_abiertas_con_prediccion = [] 

        # 2. Preparar datos del perfil del voluntario para el servicio de compatibilidad
        user_disabilities = []
        if hasattr(current_user, 'discapacidades_pivot'):
            user_disabilities = [
                udp.discapacidad.nombre.value
                for udp in current_user.discapacidades_pivot
                if udp.discapacidad and udp.discapacidad.nombre
            ]

        user_profile = {
            'id': current_user.id_usuario,
            'username': current_user.nombre,
            'interests': [p.nombre_corto for p in current_user.preferencias],
            # TODO: Implementar campo de habilidades en el modelo Usuarios y usarlo aquí.
            'skills': [], # Usar lista vacía hasta que se implementen habilidades de usuario.
            'disabilities': user_disabilities
        }

        # Cálculo de compatibilidad de programas con el perfil del voluntario.
        programs_or_activities_for_compatibility = []
        for actividad in actividades_abiertas:
            # Obtener nombres de discapacidades soportadas por la actividad
            supported_disabilities_names = [discapacidad.nombre.value for discapacidad in actividad.discapacidades if discapacidad.nombre]

            item_data = {
                'id': actividad.id_actividad,
                'name': actividad.nombre,
                'description': actividad.descripcion if actividad.descripcion else '',
                'category': actividad.etiqueta if actividad.etiqueta else (actividad.nombre.lower() if actividad.nombre else ""),
                'es_inclusiva': actividad.es_inclusiva,  # Añadir campo es_inclusiva
                'discapacidades_soportadas': supported_disabilities_names  # Añadir discapacidades soportadas
            }
            programs_or_activities_for_compatibility.append(item_data)

        compatibility_scores = {}
        if user_profile and programs_or_activities_for_compatibility:
            try:
                # Obtener los puntajes de compatibilidad
                compatibility_scores = get_compatibility_scores(user_profile, programs_or_activities_for_compatibility)
            except Exception as e:
                current_app.logger.error(f"Error al llamar a get_compatibility_scores para el usuario {user_profile.get('id')}: {e}")
                flash("Error al calcular la compatibilidad de actividades. Intente más tarde.", "danger")
        
        # Procesamiento de actividades para predicción de participación y combinación con compatibilidad.
        for actividad in actividades_abiertas:
            # Obtener predicción de participación para la actividad
            prediction_output = predecir_participacion(actividad.id_actividad)
            # Utilizar la función auxiliar para obtener el indicador y el texto de participación
            indicator, indicator_text = _get_participation_indicator_info(prediction_output)

            activity_score = 0
            if isinstance(compatibility_scores, dict):
                 activity_score_value = compatibility_scores.get(actividad.id_actividad)
                 if activity_score_value is not None:
                     activity_score = activity_score_value

            actividades_abiertas_con_prediccion.append({
                'actividad': actividad,
                'indicador': indicator,
                'texto_indicador': indicator_text,
                'compatibility_score': activity_score
            })

        actividades_compatibles_filtradas = [
            actividad_info for actividad_info in actividades_abiertas_con_prediccion
            if actividad_info.get('compatibility_score', 0) > 35
        ]

        return render_template('volunteer_dashboard.html',
                               title="Panel de Voluntario",
                               user_enrollments=user_enrollments,
                               actividades_compatibles=actividades_compatibles_filtradas)
    else:
        flash("Perfil de usuario no reconocido.", "warning")
        return redirect(url_for('main.home'))

@dashboard_bp.route('/profile')
@login_required
def profile():
    """
    Muestra la página de perfil del usuario.
    """
    user_disabilities_data = []
    if current_user.is_authenticated and hasattr(current_user, 'discapacidades_pivot'):
        user_general_preferences = list(current_user.preferencias)
        for disc_assoc in current_user.discapacidades_pivot:
            user_disabilities_data.append({
                'nombre': disc_assoc.discapacidad.nombre.value if disc_assoc.discapacidad and disc_assoc.discapacidad.nombre else "No especificada",
                'gravedad': disc_assoc.gravedad if disc_assoc.gravedad else "No especificada",
                'preferencias': user_general_preferences
            })

    user_preferences = current_user.preferencias

    user_enrollments = []
    if current_user.perfil == 'voluntario':
        user_enrollments = db.session.query(Inscripciones, Actividades) \
                                .join(Actividades, Inscripciones.id_actividad == Actividades.id_actividad) \
                                .filter(Inscripciones.id_usuario == current_user.id_usuario) \
                                .order_by(Inscripciones.fecha_inscripcion.desc()) \
                                .all()

    # Importar el formulario de edición de perfil
    from controller.forms import EditProfileForm
    form = EditProfileForm(obj=current_user)

    if current_user.fecha_nacimiento and not form.fecha_nacimiento.errors:
        form.fecha_nacimiento.data = current_user.fecha_nacimiento
      
    return render_template('profile.html',
                           user=current_user,
                           form=form,
                           user_disabilities_data=user_disabilities_data,
                           user_preferences=user_preferences,
                           user_enrollments=user_enrollments,
                           title="Mi Perfil")

@dashboard_bp.route('/admin/manage_users')
@login_required
def admin_manage_users():
    if current_user.perfil != 'administrador':
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for('user_dashboard.dashboard'))

    all_users = Usuarios.query.order_by(Usuarios.id_usuario).all()
    estados_posibles = [estado.value for estado in EstadoUsuario]
    return render_template('admin_manage_users.html', users=all_users, title="Gestionar Usuarios", estados_posibles=estados_posibles)

@dashboard_bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.perfil != 'administrador':
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for('user_dashboard.dashboard'))

    user_to_delete = Usuarios.query.get_or_404(user_id)
    if user_to_delete.id_usuario == current_user.id_usuario:
        flash("No puedes eliminar tu propia cuenta.", "danger")
        return redirect(url_for('user_dashboard.admin_manage_users'))

    try:
        # Considerar la eliminación en cascada o el manejo de dependencias aquí
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"Usuario {user_to_delete.nombre} eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el usuario: {str(e)}", "danger")
        current_app.logger.error(f"Error deleting user {user_id}: {e}")
    return redirect(url_for('user_dashboard.admin_manage_users'))

@dashboard_bp.route('/admin/change_user_status/<int:user_id>', methods=['POST'])
@login_required
def admin_change_user_status(user_id):
    if current_user.perfil != 'administrador':
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for('user_dashboard.dashboard'))

    user_to_update = Usuarios.query.get_or_404(user_id)
    new_status_str = request.form.get('estado_usuario')

    if not new_status_str:
        flash("No se proporcionó un nuevo estado.", "warning")
        return redirect(url_for('user_dashboard.admin_manage_users'))

    try:
        new_status_enum = EstadoUsuario(new_status_str)
        user_to_update.estado_usuario = new_status_enum
        db.session.commit()
        flash(f"Estado del usuario {user_to_update.nombre} actualizado a {new_status_str}.", "success")
    except ValueError:
        flash(f"Estado '{new_status_str}' no válido.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al cambiar el estado del usuario: {str(e)}", "danger")
        current_app.logger.error(f"Error changing status for user {user_id}: {e}")
    return redirect(url_for('user_dashboard.admin_manage_users'))

@dashboard_bp.route('/organizer/trigger-recommendations', methods=['POST'])
@login_required
def trigger_organizer_recommendations():
    if current_user.perfil != 'organizador':
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for('main.home'))

    try:
        # Esta función está actualmente deshabilitada.
        current_app.logger.info(f"Organizador {current_user.id_usuario} activó manualmente la generación de recomendaciones (actualmente deshabilitada).")
        flash("La generación manual de recomendaciones está actualmente deshabilitada.", "info")
    except Exception as e:
        current_app.logger.error(f"Error durante la activación manual (deshabilitada) de generación de recomendaciones: {e}")
        flash(f"Ocurrió un error: {str(e)}", "danger")

    return redirect(url_for('user_dashboard.dashboard'))
