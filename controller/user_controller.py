from flask import Blueprint, render_template, redirect, url_for, flash, request
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
    form = EditProfileForm(obj=current_user)

    if form.validate_on_submit():
        # Actualizar datos del usuario
        current_user.nombre = form.nombre.data
        current_user.apellido = form.apellido.data
        current_user.celular = form.celular.data

        new_email = form.email.data
        if new_email and new_email != current_user.email:
            existing_email = Usuarios.query.filter(Usuarios.email == new_email, Usuarios.id_usuario != current_user.id_usuario).first()
            if existing_email:
                flash('Este correo electrónico ya está en uso por otro usuario.', 'danger')
                return redirect(url_for('user_dashboard.profile'))
        current_user.email = new_email if new_email else None # Permite email vacío

        current_user.direccion = form.direccion.data

        # Manejo de fecha_nacimiento
        if form.fecha_nacimiento.data:
            if isinstance(form.fecha_nacimiento.data, str):
                try:
                    current_user.fecha_nacimiento = datetime.strptime(form.fecha_nacimiento.data, '%Y-%m-%d').date()
                except ValueError:
                    flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'warning')
                    return redirect(url_for('user_dashboard.profile'))
            else:
                 current_user.fecha_nacimiento = form.fecha_nacimiento.data

        else:
            current_user.fecha_nacimiento = None

        current_user.genero = form.genero.data if form.genero.data else None

        try:
            db.session.commit()
            flash('Tu perfil ha sido actualizado exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el perfil: {str(e)}', 'danger')

        return redirect(url_for('user_dashboard.profile')) 

    # Si hay errores de validación después de un POST y form.validate_on_submit() falla:
    if request.method == 'POST' and form.errors:
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field.replace('_', ' ').capitalize()}: {error}")
        flash("Errores al actualizar el perfil: " + "; ".join(error_messages), "danger")

    return redirect(url_for('user_dashboard.profile'))
