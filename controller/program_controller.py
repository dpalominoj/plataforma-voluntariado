from flask import flash, redirect, url_for, current_app # Importar current_app para logging
from flask_login import current_user, login_required
from model.models import Actividades, Discapacidades, Inscripciones, EstadoActividad, Preferencias, actividad_discapacidad_table
from services.compatibility_service import get_compatibility_scores
from database.db import db

def get_programs_compatibility(tipo_filter=None, organizacion_filter=None, estado_filter=None, enfoque_inclusivo=None, preferencia_filter=None):
    compatibility_scores = {}
    query = Actividades.query
    # Inicializar programs como lista vacía para el caso de que no se encuentren programas
    programs = []

    apply_default_status_filter = True
    default_status_is_abierto = True

    # Aplicar filtros a la consulta
    if current_user.is_authenticated:
        if current_user.perfil == 'organizador':
            organizer_org_ids = [org.id_organizacion for org in current_user.organizaciones]
            if organizer_org_ids:
                query = query.filter(Actividades.id_organizacion.in_(organizer_org_ids))
                default_status_is_abierto = False # Organizadores ven todos sus programas por defecto, no solo abiertos
            else:
                # Si un organizador no tiene organizaciones asignadas, no debería ver programas.
                query = query.filter(Actividades.id_actividad == -1)

    if tipo_filter:
        query = query.filter(Actividades.tipo == tipo_filter)

    if organizacion_filter:
        query = query.filter(Actividades.id_organizacion == organizacion_filter)

    if enfoque_inclusivo and enfoque_inclusivo != '':
        # Filtrar programas que soportan una discapacidad específica
        query = query.join(actividad_discapacidad_table, Actividades.id_actividad == actividad_discapacidad_table.c.actividad_id) \
                     .join(Discapacidades, actividad_discapacidad_table.c.discapacidad_id == Discapacidades.id_discapacidad) \
                     .filter(Discapacidades.nombre == enfoque_inclusivo)
        query = query.with_entities(Actividades) # Asegurarse de devolver solo objetos Actividades

    if preferencia_filter and preferencia_filter.isdigit():
        pref = Preferencias.query.get(int(preferencia_filter))
        if pref and pref.nombre_corto: # Filtrar por etiqueta de preferencia
            query = query.filter(Actividades.etiqueta == pref.nombre_corto)

    if estado_filter:
        query = query.filter(Actividades.estado == estado_filter)
        apply_default_status_filter = False # El usuario especificó un estado
    elif apply_default_status_filter: # Aplicar filtro de estado por defecto si no se especificó uno
        if default_status_is_abierto:
            query = query.filter(Actividades.estado == 'abierto')
        elif current_user.is_authenticated and current_user.perfil == 'organizador':
            # Los organizadores ven todos sus programas excepto los cerrados, a menos que filtren específicamente
            query = query.filter(Actividades.estado != 'cerrado')
        else: # Por defecto, para usuarios no logueados o voluntarios, mostrar solo abiertos
            query = query.filter(Actividades.estado == 'abierto')

    programs = query.all() # Ejecutar la consulta

    # Si el usuario es voluntario y hay programas, calcular compatibilidad
    if current_user.is_authenticated and current_user.perfil == 'voluntario' and programs:
        user_disabilities = [udp.discapacidad.nombre for udp in current_user.discapacidades_pivot if udp.discapacidad and udp.discapacidad.nombre]
        user_interests = [pref.nombre_corto for pref in current_user.preferencias if pref.nombre_corto]
        # TODO: Obtener habilidades reales del usuario. Por ahora, se usa una lista placeholder.
        user_skills_placeholder = ['comunicacion', 'trabajo en equipo']

        user_profile_data = {
            'id': current_user.id_usuario,
            'username': current_user.nombre,
            'interests': user_interests,
            'skills': user_skills_placeholder,
            'disabilities': user_disabilities
        }

        program_data_for_service = []
        for p in programs:
            # Obtener nombres de discapacidades soportadas por el programa
            supported_disabilities_names = [d.nombre for d in p.discapacidades if d.nombre]

            program_data_for_service.append({
                'id': p.id_actividad,
                'name': p.nombre,
                'description': p.descripcion,
                'category': p.etiqueta if p.etiqueta else (p.nombre.lower() if p.nombre else ""),
                'es_inclusiva': p.es_inclusiva, # Añadir si el programa es inclusivo
                'discapacidades_soportadas': supported_disabilities_names # Añadir lista de nombres de discapacidades
            })

        if program_data_for_service:
            try:
                # Llamar al servicio de compatibilidad
                compatibility_scores = get_compatibility_scores(user_profile_data, program_data_for_service)

                # Si se obtuvieron puntajes y el usuario es voluntario, actualizar los objetos del programa
                if compatibility_scores and current_user.perfil == 'voluntario':
                    updated_scores_flag = False
                    for program_obj in programs:
                        score = compatibility_scores.get(program_obj.id_actividad)
                        if score is not None:
                            program_obj.compatibilidad = score # Asignar el nuevo puntaje
                            updated_scores_flag = True
                            # Registrar el puntaje (usar logger en producción)
                            current_app.logger.info(f"Compatibilidad para actividad {program_obj.id_actividad} ({program_obj.nombre}): {program_obj.compatibilidad}")

                    if updated_scores_flag:
                        try:
                            db.session.commit() # Guardar cambios en la BD
                            current_app.logger.info("Puntajes de compatibilidad actualizados en la BD.")
                        except Exception as e:
                            db.session.rollback() # Revertir en caso de error
                            current_app.logger.error(f"Error al guardar puntajes de compatibilidad en la BD: {e}")

            except Exception as e:
                # Usar logger para registrar errores del servicio de compatibilidad
                current_app.logger.error(f"Error al calcular o procesar los puntajes de compatibilidad: {e}")

    return programs, compatibility_scores

from flask import Blueprint, render_template, redirect, url_for, flash, abort
from sqlalchemy.orm import joinedload # Importar joinedload

# Importar el nuevo formulario y el servicio de notificación
from controller.forms import EditProgramStateForm
from services.notification_service import crear_notificacion_cambio_estado
# model.models.EstadoActividad ya está importado arriba

# Definición del Blueprint
program_bp = Blueprint('program', __name__,
                           template_folder='../view/templates', # Ruta a las plantillas
                           url_prefix='/program') # Prefijo URL para estas rutas

# Ruta para ver el detalle de un programa
@program_bp.route('/<int:program_id>')
def view_program_detail(program_id):
    # Cargar programa con relaciones de discapacidades y facilidades
    program = Actividades.query.options(
        joinedload(Actividades.discapacidades),
        joinedload(Actividades.facilidades),
        joinedload(Actividades.organizacion) # Asegurar que la organización también se carga si es necesario
    ).get(program_id)

    if not program:
        flash('Programa no encontrado.', 'danger')
        return redirect(url_for('main.programs')) # Redirigir si no se encuentra

    # Renderizar la plantilla de detalle del programa
    return render_template('program_detail.html', program=program, title=program.nombre)

# Ruta para inscribirse en un programa (requiere login)
@program_bp.route('/<int:program_id>/enroll', methods=['POST'])
@login_required
def enroll_program(program_id):
    program = Actividades.query.get_or_404(program_id) # Obtener programa o error 404

    # Verificar que el usuario sea un voluntario
    if current_user.perfil != 'voluntario':
        flash("Solo los voluntarios pueden inscribirse.", "danger")
        return redirect(url_for('main.programs'))

    # Verificar que el programa esté abierto para inscripciones
    if program.estado != EstadoActividad.ABIERTO:
        flash("Este programa no está abierto para inscripciones.", "danger")
        return redirect(url_for('program.view_program_detail', program_id=program_id))

    # Verificar si ya está inscrito
    existing_inscription = Inscripciones.query.filter_by(
        id_usuario=current_user.id_usuario,
        id_actividad=program_id
    ).first()
    if existing_inscription:
        flash("Ya estás inscrito en este programa.", "info")
        return redirect(url_for('program.view_program_detail', program_id=program_id))

    # Verificar cupo máximo
    if program.cupo_maximo is not None:
        if len(program.inscripciones) >= program.cupo_maximo:
            flash("El programa ha alcanzado su cupo máximo.", "danger")
            return redirect(url_for('program.view_program_detail', program_id=program_id))

    try:
        # Crear nueva inscripción
        new_inscription = Inscripciones(
            id_usuario=current_user.id_usuario,
            id_actividad=program_id
        )
        db.session.add(new_inscription)
        db.session.commit() # Guardar en la BD
        flash("¡Inscripción exitosa!", "success")

    except Exception as e:
        db.session.rollback() # Revertir en caso de error
        flash(f"Error al procesar la inscripción: {str(e)}", "danger")
        current_app.logger.error(f"Error en inscripción para programa {program_id} por usuario {current_user.id_usuario}: {e}")


    return redirect(url_for('program.view_program_detail', program_id=program_id))


@program_bp.route('/<int:program_id>/edit_state', methods=['GET', 'POST'])
@login_required
def edit_program_state(program_id):
    program = Actividades.query.get_or_404(program_id)

    # Verificar perfil de organizador
    if current_user.perfil != 'organizador':
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for('main.home')) # O a donde corresponda

    # Verificar que el organizador gestiona este programa
    # Un organizador puede pertenecer a múltiples organizaciones.
    # El programa pertenece a una organización.
    # Si el id_organizacion del programa está en las organizaciones del current_user, tiene permiso.
    organizer_org_ids = [org.id_organizacion for org in current_user.organizaciones]
    if program.id_organizacion not in organizer_org_ids:
        flash("No tienes permiso para editar el estado de este programa.", "danger")
        return redirect(url_for('program.view_program_detail', program_id=program_id))

    form = EditProgramStateForm(obj=program) # obj=program precargará el estado actual si el nombre del campo coincide

    if form.validate_on_submit():
        nuevo_estado_str = form.estado.data
        nuevo_estado_enum = EstadoActividad(nuevo_estado_str) # Convertir string a Enum

        antiguo_estado_enum = program.estado # Guardar estado anterior para notificación

        if antiguo_estado_enum == nuevo_estado_enum:
            flash(f"El programa ya se encuentra en estado '{nuevo_estado_enum.name.replace('_', ' ').title()}'. No se realizaron cambios.", "info")
        else:
            program.estado = nuevo_estado_enum
            try:
                db.session.commit()
                flash(f"El estado del programa '{program.nombre}' ha sido actualizado a '{nuevo_estado_enum.name.replace('_', ' ').title()}'.", "success")

                # Enviar notificaciones si el cambio de estado es relevante
                # La función crear_notificacion_cambio_estado decide si notificar o no
                if current_app: # Asegurarse de que current_app está disponible (debería estarlo en una ruta)
                    with current_app.app_context(): # Asegurar contexto para url_for en el servicio
                         crear_notificacion_cambio_estado(program, nuevo_estado_enum, antiguo_estado_enum)
                else: # Fallback si no hay current_app (menos probable en este contexto)
                    print("Advertencia: current_app no disponible, no se pudo llamar a crear_notificacion_cambio_estado con contexto.")


            except Exception as e:
                db.session.rollback()
                flash(f"Error al actualizar el estado del programa: {str(e)}", "danger")
                current_app.logger.error(f"Error actualizando estado de programa {program_id} por {current_user.id_usuario}: {e}")

        return redirect(url_for('program.view_program_detail', program_id=program_id))

    # Para GET, pre-rellenar el formulario con el estado actual
    form.estado.data = program.estado.value if program.estado else None

    # Usar una plantilla específica o una sección en program_detail o en el dashboard del organizador
    # Por ahora, crearé una plantilla dedicada: 'edit_program_state.html'
    return render_template('dashboards/edit_program_state.html', title="Editar Estado del Programa", form=form, program=program)
