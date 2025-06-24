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
    form = EditProfileForm(obj=current_user)

    if form.validate_on_submit():
        current_user.nombre = form.nombre.data
        current_user.apellido = form.apellido.data
        current_user.celular = form.celular.data

        new_email = form.email.data
        if new_email and new_email != current_user.email: # Solo validar si el email cambia y no es vacío
            existing_email = Usuarios.query.filter(Usuarios.email == new_email, Usuarios.id_usuario != current_user.id_usuario).first()
            if existing_email:
                flash('Este correo electrónico ya está en uso por otro usuario.', 'danger')
                return render_template('edit_profile.html', title='Editar Perfil', form=form)
        current_user.email = new_email if new_email else None

        current_user.direccion = form.direccion.data

        if form.fecha_nacimiento.data:
            try:
                current_user.fecha_nacimiento = datetime.strptime(form.fecha_nacimiento.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'warning')
                return render_template('edit_profile.html', title='Editar Perfil', form=form)
        else:
            current_user.fecha_nacimiento = None

        current_user.genero = form.genero.data if form.genero.data else None

        try:
            db.session.commit()
            flash('Tu perfil ha sido actualizado exitosamente.', 'success')
            return redirect(url_for('profile.edit_profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar el perfil.', 'danger')
            print(f"Error en edit_profile: {e}")

    # Para solicitudes GET o si el formulario no valida y se re-renderiza:
    # Si current_user.fecha_nacimiento es un objeto date y el campo del formulario está vacío (GET)
    # o no contenía datos válidos (POST que falló validación de formato),
    # lo formateamos para mostrarlo correctamente en el input.
    # WTForms precarga con obj=current_user. Esta lógica es para asegurar el formato de fecha.
    if current_user.fecha_nacimiento:
        if not form.fecha_nacimiento.errors: # Si no hay error de formato específico en el campo de fecha
            form.fecha_nacimiento.data = current_user.fecha_nacimiento.strftime('%Y-%m-%d')
    else:
        form.fecha_nacimiento.data = None


    return render_template('edit_profile.html', title='Editar Perfil', form=form)
