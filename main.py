import os
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from sqlalchemy import inspect
from database.db import db, init_app
from controller.routes import main_bp
from controller.auth_routes import auth_bp
from controller.dashboard_routes import dashboard_bp
from controller.program_controller import program_bp
from flask_login import LoginManager
from flask_migrate import Migrate
from model.models import Usuarios
from database.datos_iniciales import seed_data


app = Flask(__name__, instance_relative_config=True, template_folder='view/templates')
app.static_folder = 'view/assets'
app.static_url_path = '/assets'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key968')
default_sqlite_uri = f"sqlite:///{os.path.join(app.instance_path, 'konectai.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_sqlite_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app)

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

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(program_bp)

@app.route('/services/<path:filename>')
def serve_service_file(filename):
    return send_from_directory(os.path.join(app.root_path, 'services'), filename)

@app.cli.command('seed-db')
def seed_db_command():
    """Puebla la base de datos con datos iniciales."""
    with app.app_context():
        seed_data()

# Socket.IO Event Handlers
@socketio.on('connect')
def handle_connect():
    app.logger.info('Client connected to chat')
    # emit('chat_response', {'response': 'Bienvenido al chat de KonectaAI.', 'requires_auth': False}) # Optional welcome message

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info('Client disconnected from chat')

@socketio.on('chat_message')
def handle_chat_message(data):
    user_message = data.get('query', '').strip()
    app.logger.info(f"Received chat message: '{user_message}'")

    bot_response = f"KonectaAI ha recibido tu mensaje: '{user_message}'. Pronto te responderé con más inteligencia."
    user_message_lower = user_message.lower()

    if "hola" in user_message_lower:
        bot_response = "¡Hola! ¿Cómo puedo ayudarte hoy?"
    elif "adiós" in user_message_lower or "chao" in user_message_lower:
        bot_response = "¡Hasta luego! Que tengas un buen día."
    elif "ayuda" in user_message_lower:
        bot_response = "Puedes preguntar sobre nuestros programas de voluntariado, cómo registrarte o sobre la accesibilidad."
    elif "gracias" in user_message_lower:
        bot_response = "¡De nada! Estoy aquí para ayudar."

    app.logger.info(f"Sending bot response: '{bot_response}'")
    emit('chat_response', {'response': bot_response, 'requires_auth': False})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # TODO: DEBUG debe ser False en un entorno de producción
    # app.run(host='0.0.0.0', port=port, debug=True) # Original Flask dev server
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
