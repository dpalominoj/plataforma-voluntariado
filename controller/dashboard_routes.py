from flask import Blueprint, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from model.models import UsuarioDiscapacidad, Discapacidades, Inscripciones, Actividades, Usuarios, EstadoActividad
from database.db import db
from services.participation_service import predecir_participacion
from services.compatibility_service import get_compatibility_scores

dashboard_bp = Blueprint('user_dashboard', __name__,
                         template_folder='../view/templates/dashboards',
                         url_prefix='/dashboard')

def _get_participation_indicator_info(prediction_output):
    indicator = '⚪' # Indicador por defecto: círculo blanco
    indicator_text = 'Predicción no disponible'

    if prediction_output:
        if 'error' not in prediction_output and 'probabilidad' in prediction_output:
            prob = prediction_output.get('probabilidad') # Usar .get() para seguridad
            if prob is None:
                indicator = '⚪' # Círculo blanco si la probabilidad no se pudo calcular
                indicator_text = 'Probabilidad no calculada (ej. datos insuficientes)'
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
        elif 'info' in prediction_output: # Usar elif para evitar sobreescribir un error con info
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

        return render_template('organizer_dashboard.html',
                               title="Panel de Organizador",
                               created_programs_con_prediccion=actividades_con_prediccion,
                               member_organizations=member_organizations)
    elif current_user.perfil == 'voluntario':
        user_enrollments = db.session.query(Inscripciones, Actividades) \
                            .join(Actividades, Inscripciones.id_actividad == Actividades.id_actividad) \
                            .filter(Inscripciones.id_usuario == current_user.id_usuario) \
                            .order_by(Inscripciones.fecha_inscripcion.desc()) \
                            .all()

     
        # 1. Obtener todas las actividades abiertas que podrían ser de interés
        actividades_abiertas = Actividades.query.filter_by(estado=EstadoActividad.ABIERTO).all()
        
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
            'skills': ['writing', 'gardening'],
            'disabilities': user_disabilities
        }

        # 3. Cálculo de compatibilidad de programas con el perfil del voluntario.
        programs_or_activities_for_compatibility = []
        for actividad in actividades_abiertas:
            item_data = {
                'id': actividad.id_actividad,
                'name': actividad.nombre,
                'description': actividad.descripcion if actividad.descripcion else '',
                'category': actividad.etiqueta if actividad.etiqueta else (actividad.nombre.lower() if actividad.nombre else "")
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
        
        # 4. Procesamiento de actividades para predicción de participación y combinación con compatibilidad.
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

    return render_template('profile.html',
                           user=current_user,
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
    return render_template('admin_manage_users.html', users=all_users, title="Gestionar Usuarios")

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
