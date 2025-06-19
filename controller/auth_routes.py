from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from database.db import db
from model.models import Usuarios, Discapacidades, Preferencias, UsuarioDiscapacidad
from controller.forms import RegistrationForm, LoginForm

auth_bp = Blueprint('auth', __name__,
                    template_folder='../view/templates/auth',
                    static_folder='../view/static',
                    url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    form.discapacidades.choices = [(d.id_discapacidad, d.nombre.value if hasattr(d.nombre, 'value') else d.nombre) for d in Discapacidades.query.all()]
    form.preferencias.choices = [(p.id_preferencia, p.nombre_corto) for p in Preferencias.query.all()]
    if form.validate_on_submit():
        existing_user = Usuarios.query.filter_by(DNI=form.dni.data).first()
        if existing_user:
            flash('El DNI ingresado ya está registrado. Por favor, intente con otro.', 'danger')
            return render_template('register.html', title='Registro', form=form)
        user = Usuarios(
            DNI=form.dni.data,
            nombre=form.nombre.data,
            perfil=form.perfil.data,
            estado_usuario=form.estado_usuario.data
        )
        user.set_password(form.password.data)

        if form.discapacidades.data:
            for discapacidad_id_str in form.discapacidades.data:
                discapacidad_id = int(discapacidad_id_str)
                user_discapacidad_assoc = UsuarioDiscapacidad(id_discapacidad=discapacidad_id)
                user.discapacidades_pivot.append(user_discapacidad_assoc)

        if form.preferencias.data:
            for preferencia_id_str in form.preferencias.data:
                preferencia_id = int(preferencia_id_str)
                preferencia = Preferencias.query.get(preferencia_id)
                if preferencia:
                    user.preferencias.append(preferencia)

        db.session.add(user)
        db.session.commit()
        flash('¡Felicidades, ahora eres un usuario registrado! Por favor Inicia Sesión.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='Registro', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuarios.query.filter_by(DNI=form.dni.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('user_dashboard.dashboard'))
        else:
            flash('Inicio de sesión fallido. Por favor, verifica tu DNI y contraseña.', 'danger')
    return render_template('login.html', title='Iniciar Sesión', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('main.home'))
