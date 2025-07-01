from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired, EqualTo, Length, Optional # Email removido

class RegistrationForm(FlaskForm):
    dni = StringField('DNI',
                           validators=[DataRequired(), Length(min=8, max=8)])
    nombre = StringField('Nombre',
                        validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Contraseña',
                                     validators=[DataRequired(), EqualTo('password')])
    perfil = SelectField('Perfil',
                       choices=[('voluntario', 'Voluntario'), ('organizador', 'Organizador')],
                       validators=[DataRequired()])
    # El campo estado_usuario se manejará internamente o por administradores, no se mostrará en el formulario de registro público.
    # estado_usuario = SelectField('Estado',
    #                              choices=[('activo', 'Activo'), ('inactivo', 'Inactivo'), ('suspendido', 'Suspendido'), ('bloqueado', 'Bloqueado')],
    #                              validators=[DataRequired()], default='activo')
    discapacidades = SelectMultipleField('Discapacidades', validators=[Optional()])
    preferencias = SelectMultipleField('Preferencias', validators=[Optional()])
    acepto_politica = BooleanField('Acepto la política de privacidad', validators=[DataRequired(message="Debe aceptar la política de privacidad.")])
    submit = SubmitField('Registrarse')

class LoginForm(FlaskForm):
    dni = StringField('DNI',
                        validators=[DataRequired(), Length(min=8, max=8)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class EditProfileForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    apellido = StringField('Apellido', validators=[Optional(), Length(max=100)])
    celular = StringField('Celular', validators=[Optional(), Length(max=9)]) # Ajustar validación si es necesario
    email = StringField('Email', validators=[Optional(), Length(max=150)]) # Añadir validador de Email si se reinstala email_validator
    direccion = StringField('Dirección', validators=[Optional(), Length(max=255)])
    fecha_nacimiento = StringField('Fecha de Nacimiento (YYYY-MM-DD)', validators=[Optional()]) # Considerar DateField
    genero = SelectField('Género', choices=[('', 'Prefiero no decirlo'), ('masculino', 'Masculino'), ('femenino', 'Femenino')], validators=[Optional()])
    submit = SubmitField('Guardar Cambios')

# Necesitamos EstadoActividad para las choices del formulario de cambio de estado
from model.models import EstadoActividad

class EditProgramStateForm(FlaskForm):
    estado = SelectField('Nuevo Estado del Programa',
                         choices=[(estado.value, estado.name.replace('_', ' ').title()) for estado in EstadoActividad],
                         validators=[DataRequired()])
    submit = SubmitField('Actualizar Estado')
