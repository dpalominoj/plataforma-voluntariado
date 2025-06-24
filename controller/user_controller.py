# controller/user_controller.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from database.db import db
from model.models import Usuarios
from controller.forms import EditProfileForm
from datetime import datetime

profile_bp = Blueprint('profile', __name__,
                       template_folder='../view/templates/dashboards',
                       url_prefix='/profile')

@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user) # Carga datos del usuario en el form para GET

    if form.validate_on_submit(): # Esto solo se cumple en POST y si la data es válida
        # Actualizar datos del usuario
        current_user.nombre = form.nombre.data
        current_user.apellido = form.apellido.data
        current_user.celular = form.celular.data

        new_email = form.email.data
        if new_email and new_email != current_user.email:
            existing_email = Usuarios.query.filter(Usuarios.email == new_email, Usuarios.id_usuario != current_user.id_usuario).first()
            if existing_email:
                flash('Este correo electrónico ya está en uso por otro usuario.', 'danger')
                # Idealmente, querríamos mostrar el formulario de nuevo con el error.
                # Por ahora, redirigimos y el usuario tendrá que reabrir el formulario.
                return redirect(url_for('user_dashboard.profile'))
        current_user.email = new_email if new_email else None # Permite email vacío

        current_user.direccion = form.direccion.data

        # Manejo de fecha_nacimiento
        if form.fecha_nacimiento.data: # WTForms convierte el campo StringField a objeto date si es válido
            if isinstance(form.fecha_nacimiento.data, str): # Si sigue siendo string, hubo un error de conversión o es inválida
                try:
                    # Intenta convertir manualmente, aunque WTForms DateField haría esto mejor
                    current_user.fecha_nacimiento = datetime.strptime(form.fecha_nacimiento.data, '%Y-%m-%d').date()
                except ValueError:
                    flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'warning')
                    # No asignar current_user.fecha_nacimiento si es inválido para no borrar un valor bueno previo
                    # Opcionalmente, podrías establecerlo a None si el campo vacío es aceptable
                    # current_user.fecha_nacimiento = None
                    return redirect(url_for('user_dashboard.profile')) # Redirige y el usuario debe reabrir
            else: # Si ya es un objeto date (convertido por WTForms o porque no cambió)
                 current_user.fecha_nacimiento = form.fecha_nacimiento.data

        else: # Si el campo de fecha está vacío en el formulario
            current_user.fecha_nacimiento = None

        current_user.genero = form.genero.data if form.genero.data else None

        try:
            db.session.commit()
            flash('Tu perfil ha sido actualizado exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el perfil: {str(e)}', 'danger')
            # Considerar loggear el error: current_app.logger.error(f"Error en edit_profile: {e}")

        return redirect(url_for('user_dashboard.profile')) # Redirigir siempre a la página de perfil

    # Si es una solicitud GET, o si form.validate_on_submit() es falso en un POST (error de validación)
    # En el nuevo flujo, GET a esta URL no debería ocurrir si todo es en profile.html.
    # Si ocurre un error de validación en POST, los errores se flashearán y se redirigirá.
    # El estado del formulario (visible/oculto) se reiniciará en profile.html.
    # Si quisiéramos mantener el formulario abierto y con errores, necesitaríamos una lógica más compleja.

    # Si hay errores de validación después de un POST y form.validate_on_submit() falla:
    if request.method == 'POST' and form.errors:
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field.replace('_', ' ').capitalize()}: {error}")
        flash("Errores al actualizar el perfil: " + "; ".join(error_messages), "danger")

    # La plantilla 'edit_profile.html' ya no se usa directamente para renderizar la página completa.
    # Redirigimos a la página de perfil donde el formulario está integrado.
    return redirect(url_for('user_dashboard.profile'))
