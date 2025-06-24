from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from database.db import db
from model.models import Usuarios, Discapacidades, Preferencias, UsuarioDiscapacidad, Notificaciones, TipoNotificacion # Añadido Notificaciones y TipoNotificacion
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

        # Crear notificación para completar perfil
        try:
            # Asumiendo que la ruta para editar perfil será algo como 'profile.edit_profile'
            # Esto podría necesitar ajuste cuando se implemente la vista de editar perfil.
            # Si 'user_dashboard.profile' es la vista de perfil, editar_perfil podría estar ahí.
            # Por ahora, usaremos 'user_dashboard.profile' como placeholder si url_for('profile.edit_profile') no está definido aún.
            # La tarea especifica "editar_perfil"
            url_editar_perfil = url_for('profile.edit_profile') # Actualizado a la nueva ruta

            mensaje_notificacion = "¡Bienvenido/a! Completa tu perfil para mejorar tu experiencia y acceder a todas las funcionalidades."

            nueva_notificacion = Notificaciones(
                id_usuario=user.id_usuario,
                mensaje=mensaje_notificacion,
                tipo=TipoNotificacion.COMPLETAR_PERFIL,
                prioridad='alta', # Según el enum del modelo es 'alta', 'media', 'baja'
                url_destino=url_editar_perfil
            )
            db.session.add(nueva_notificacion)
            db.session.commit()
        except Exception as e:
            # Loggear el error o manejarlo discretamente para no interrumpir el flujo de registro
            # Por ejemplo, podrías usar flash('Error al crear notificación, contacte soporte.', 'warning')
            # o simplemente loggear a consola/archivo.
            print(f"Error al crear notificación de completar perfil: {e}")
            # No es crítico fallar aquí, así que no relanzamos la excepción ni hacemos rollback del usuario.

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
