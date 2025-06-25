import os
from flask import Flask, send_from_directory
# from flask_socketio import SocketIO, emit # No longer needed for chat
import openai # Importar OpenAI
from sqlalchemy import inspect, func # Añadir func
from database.db import db, init_app
from controller.routes import main_bp
from controller.auth_routes import auth_bp
from controller.dashboard_routes import dashboard_bp
from controller.program_controller import program_bp
from controller.user_controller import profile_bp
from controller.notification_controller import notifications_bp # <--- Añadir import
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from model.models import Usuarios, Notificaciones # Añadir Notificaciones
from database.datos_iniciales import seed_data


app = Flask(__name__, instance_relative_config=True, template_folder='view/templates')
app.static_folder = 'view/assets'
app.static_url_path = '/assets'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key968')
default_sqlite_uri = f"sqlite:///{os.path.join(app.instance_path, 'konectai.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_sqlite_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# socketio = SocketIO(app) # No longer needed for chat

try:
    os.makedirs(app.instance_path)
except OSError:
    pass

init_app(app)
migrate = Migrate(app, db)

def create_tables_if_not_exist(flask_app, db_instance):
    with flask_app.app_context():
        inspector = inspect(db_instance.engine)
        if not inspector.has_table(Usuarios.__tablename__):
            db_instance.create_all()
            app.logger.info("Tablas de la base de datos creadas.")
            return True
        else:
            app.logger.info("Tablas de la base de datos ya existen.")
            return False

tables_created = create_tables_if_not_exist(app, db)

if tables_created:
    with app.app_context():
        seed_data()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuarios, int(user_id))

@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        # Contar directamente en la DB es más eficiente si solo se necesita el número
        unread_count = db.session.query(func.count(Notificaciones.id_notificacion)).filter_by(id_usuario=current_user.id_usuario, leida=False).scalar()
        # Obtener las N más recientes para el dropdown
        recent_unread_notifications = Notificaciones.query.filter_by(id_usuario=current_user.id_usuario, leida=False).order_by(Notificaciones.fecha_envio.desc()).limit(5).all()
        return dict(unread_notifications_count=unread_count, recent_unread_notifications=recent_unread_notifications)
    return dict(unread_notifications_count=0, recent_unread_notifications=[])

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(program_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(notifications_bp) # <--- Registrar el blueprint de notificaciones

@app.route('/services/<path:filename>')
def serve_service_file(filename):
    return send_from_directory(os.path.join(app.root_path, 'services'), filename)

@app.cli.command('seed-db')
def seed_db_command():
    """Puebla la base de datos con datos iniciales."""
    with app.app_context():
        seed_data()

# Socket.IO Event Handlers are removed as they are no longer used for the chat.
# The chat functionality is now handled by the /api/chatbot/conversation endpoint.

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # TODO: DEBUG debe ser False en un entorno de producción
    app.run(host='0.0.0.0', port=port, debug=True) # Use standard Flask dev server
    # socketio.run(app, host='0.0.0.0', port=port, debug=True) # SocketIO server no longer needed for chat
