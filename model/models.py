from flask_login import UserMixin
from database.db import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Boolean, DECIMAL, Table, func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# --- Definición de Enums ---
class TipoDiscapacidad(enum.Enum):
    AUDITIVA = "Auditiva"
    VISUAL = "Visual"
    MOTRIZ = "Motriz"

class EstadoActividad(enum.Enum):
    ABIERTO = "abierto"
    CERRADO = "cerrado"
    CANCELADA = "cancelada"
    FINALIZADA = "finalizada"

class EstadoUsuario(enum.Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    BLOQUEADO = "bloqueado"

class TipoRecomendacion(enum.Enum):
    PERSONALIZADA = "P"
    GRUPAL = "G"
    BUENAS_PRACTICAS = "BP"

# Asociación de tablas
usuario_organizacion_table = Table('usuario_organizacion', db.Model.metadata,
    Column('usuario_id', Integer, ForeignKey('usuarios.id_usuario'), primary_key=True),
    Column('organizacion_id', Integer, ForeignKey('organizaciones.id_organizacion'), primary_key=True)
)

usuarios_preferencia_table = Table('usuarios_preferencia', db.Model.metadata,
    Column('usuario_id', Integer, ForeignKey('usuarios.id_usuario'), primary_key=True),
    Column('preferencia_id', Integer, ForeignKey('preferencias.id_preferencia'), primary_key=True)
)

actividad_discapacidad_table = Table('actividad_discapacidad', db.Model.metadata,
    Column('actividad_id', Integer, ForeignKey('actividades.id_actividad'), primary_key=True),
    Column('discapacidad_id', Integer, ForeignKey('discapacidades.id_discapacidad'), primary_key=True)
)

actividad_facilidad_table = Table('actividad_facilidad', db.Model.metadata,
    Column('actividad_id', Integer, ForeignKey('actividades.id_actividad'), primary_key=True),
    Column('facilidad_id', Integer, ForeignKey('facilidad.id_facilidad'), primary_key=True)
)

# Modelos
class Usuarios(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Campos obligatorios en el registro inicial
    DNI = db.Column(db.String(8), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.Enum('voluntario', 'organizador', 'administrador', name='perfil_enum'), nullable=False)
    estado_usuario = db.Column(db.Enum(EstadoUsuario, name='estado_usuario_enum', values_callable=lambda x: [e.value for e in x]), nullable=False, default=EstadoUsuario.ACTIVO)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Campos opcionales en el registro inicial (se llenarán después)
    apellido = db.Column(db.String(100), nullable=True)
    celular = db.Column(db.String(9), unique=True, nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    genero = db.Column(db.Enum('masculino', 'femenino', name='genero_enum'))

    # Relaciones
    organizaciones = relationship("Organizaciones", secondary=usuario_organizacion_table, back_populates="usuarios")
    preferencias = relationship("Preferencias", secondary=usuarios_preferencia_table, back_populates="usuarios")
    discapacidades_pivot = relationship("UsuarioDiscapacidad", back_populates="usuario", cascade="all, delete-orphan")
    inscripciones = relationship("Inscripciones", back_populates="usuario")
    notificaciones = relationship("Notificaciones", back_populates="usuario")
    feedback = relationship("Feedback", back_populates="usuario")
    recomendaciones = relationship("Recomendaciones", back_populates="usuario")
    interacciones_chatbot = relationship("InteraccionesChatbot", back_populates="usuario")

    def set_password(self, password):
        self.contrasena_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.contrasena_hash, password)

    def get_id(self):
        return str(self.id_usuario)

class Organizaciones(db.Model):
    __tablename__ = 'organizaciones'
    id_organizacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_org = db.Column(db.String(255), unique=True, nullable=False)
    descripcion_org = db.Column(db.Text)
    direccion_fisica = db.Column(db.String(255))
    logo = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    usuarios = relationship("Usuarios", secondary=usuario_organizacion_table, back_populates="organizaciones")
    actividades = relationship("Actividades", back_populates="organizacion")


class Preferencias(db.Model):
    __tablename__ = 'preferencias'
    id_preferencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_corto = db.Column(db.String(50), unique=True)
    descripcion_detallada = db.Column(db.Text)

    usuarios = relationship("Usuarios", secondary=usuarios_preferencia_table, back_populates="preferencias")


class UsuarioDiscapacidad(db.Model):
    __tablename__ = 'usuario_discapacidad'
    id_usuario = db.Column(db.Integer, ForeignKey('usuarios.id_usuario'), primary_key=True)
    id_discapacidad = db.Column(db.Integer, ForeignKey('discapacidades.id_discapacidad'), primary_key=True)
    gravedad = db.Column(db.Enum('leve', 'moderada', 'grave', name='gravedad_enum'))
    apoyo_requerido = db.Column(db.Enum('interprete', 'otros', name='apoyo_requerido_enum'))

    usuario = relationship("Usuarios", back_populates="discapacidades_pivot")
    discapacidad = relationship("Discapacidades", back_populates="usuarios_pivot")


class Discapacidades(db.Model):
    __tablename__ = 'discapacidades'
    id_discapacidad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.Enum(TipoDiscapacidad, values_callable=lambda x: [e.value for e in x]), unique=True)
    descripcion = db.Column(db.Text)

    usuarios_pivot = relationship("UsuarioDiscapacidad", back_populates="discapacidad", cascade="all, delete-orphan")
    actividades = relationship("Actividades", secondary=actividad_discapacidad_table, back_populates="discapacidades")


class Actividades(db.Model):
    __tablename__ = 'actividades'
    id_actividad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255))
    descripcion = db.Column(db.Text)
    fecha_actividad = db.Column(db.DateTime)
    ubicacion = db.Column(db.String(255))
    tipo = db.Column(db.Enum('presencial', 'virtual', name='tipo_actividad_enum'))
    habilidades_requeridas = db.Column(db.Text)
    es_inclusiva = db.Column(db.Boolean, default=False)
    cupo_maximo = db.Column(db.Integer)
    estado = db.Column(db.Enum(EstadoActividad, name='estado_actividad_enum', values_callable=lambda x: [e.value for e in x]), default=EstadoActividad.ABIERTO)
    imagen = db.Column(db.String(255))
    compatibilidad = db.Column(db.DECIMAL(5, 2))
    etiqueta = db.Column(db.String(100))
    id_organizacion = db.Column(db.Integer, ForeignKey('organizaciones.id_organizacion'))

    # Relaciones
    organizacion = relationship("Organizaciones", back_populates="actividades")
    discapacidades = relationship("Discapacidades", secondary=actividad_discapacidad_table, back_populates="actividades")
    facilidades = relationship("Facilidad", secondary=actividad_facilidad_table, back_populates="actividades")
    auditoria_actividad = relationship("AuditoriaActividad", back_populates="actividad")
    inscripciones = relationship("Inscripciones", back_populates="actividad")


class AuditoriaActividad(db.Model):
    __tablename__ = 'auditoria_actividad'
    id_auditoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_actividad = db.Column(db.Integer, ForeignKey('actividades.id_actividad'), nullable=False)
    id_usuario = db.Column(db.Integer, ForeignKey('usuarios.id_usuario'))
    IP_usuario = db.Column(db.String(45))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    actividad = relationship("Actividades", back_populates="auditoria_actividad")
    usuario = relationship("Usuarios")


class Facilidad(db.Model):
    __tablename__ = 'facilidad'
    id_facilidad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_facilidad = db.Column(db.String(255), unique=True, nullable=False)
    descripcion = db.Column(db.String(255))

    actividades = relationship("Actividades", secondary=actividad_facilidad_table, back_populates="facilidades")


class Inscripciones(db.Model):
    __tablename__ = 'inscripciones'
    id_inscripcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    id_actividad = db.Column(db.Integer, ForeignKey('actividades.id_actividad'), nullable=False)
    estado_inscripcion = db.Column(db.String(50), default='confirmada')
    fecha_inscripcion = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = relationship("Usuarios", back_populates="inscripciones")
    actividad = relationship("Actividades", back_populates="inscripciones")


class Notificaciones(db.Model):
    __tablename__ = 'notificaciones'
    id_notificacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    leida = db.Column(db.Boolean, default=False)
    prioridad = db.Column(db.Enum('alta', 'media', 'baja', name='prioridad_enum'))

    usuario = relationship("Usuarios", back_populates="notificaciones")


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id_feedback = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    id_actividad = db.Column(db.Integer, ForeignKey('actividades.id_actividad'))
    puntuacion = db.Column(db.Integer)
    comentario = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = relationship("Usuarios", back_populates="feedback")
    actividad = relationship("Actividades")


class Recomendaciones(db.Model):
    __tablename__ = 'recomendaciones'
    id_recomendacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    id_actividad = db.Column(db.Integer, ForeignKey('actividades.id_actividad'), nullable=False)
    tipo_recomendacion = db.Column(db.Enum(TipoRecomendacion, name='tipo_recomendacion_enum', values_callable=lambda x: [e.value for e in x]))
    score = db.Column(db.DECIMAL(5, 4), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = relationship("Usuarios", back_populates="recomendaciones")
    actividad = relationship("Actividades")


class Tendencias(db.Model):
    __tablename__ = 'tendencias'
    id_tendencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_actividad = db.Column(db.Integer, ForeignKey('actividades.id_actividad'))
    cantidad_participantes = db.Column(db.Integer)
    puntuacion_promedio = db.Column(db.DECIMAL(3,2))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class InteraccionesChatbot(db.Model):
    __tablename__ = 'interacciones_chatbot'
    id_interaccion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, ForeignKey('usuarios.id_usuario'))
    pregunta_usuario = db.Column(db.Text)
    respuesta_chatbot = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = relationship("Usuarios", back_populates="interacciones_chatbot")
