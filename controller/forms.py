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
                       choices=[('voluntario', 'Voluntario'), ('organizador', 'Organizador'), ('administrador', 'Administrador')],
                       validators=[DataRequired()])
    estado_usuario = SelectField('Estado',
                                 choices=[('activo', 'Activo'), ('inactivo', 'Inactivo'), ('suspendido', 'Suspendido'), ('bloqueado', 'Bloqueado')],
                                 validators=[DataRequired()], default='activo')
    discapacidades = SelectMultipleField('Discapacidades', validators=[Optional()])
    preferencias = SelectMultipleField('Preferencias', validators=[Optional()])
    acepto_politica = BooleanField('Acepto la política de privacidad', validators=[DataRequired(message="Debe aceptar la política de privacidad.")])
    submit = SubmitField('Registrarse')

class LoginForm(FlaskForm):
    dni = StringField('DNI',
                        validators=[DataRequired(), Length(min=8, max=8)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')
