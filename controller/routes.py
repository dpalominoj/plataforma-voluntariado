from flask import Blueprint, render_template, request, jsonify
from model.models import Organizaciones, Discapacidades, Actividades, EstadoActividad, Preferencias
from database.db import db
from controller.program_controller import get_programs_compatibility
from services.chatbot_service import get_chatbot_response as get_openai_chatbot_response

main_bp = Blueprint('main', __name__, template_folder='../view/templates')

@main_bp.route('/')
def home():
    """Sirve la página de inicio."""
    return render_template('home.html')

@main_bp.route('/programs')
def programs():
    """Sirve la página que lista todos los programas, con capacidades de filtrado."""
    tipo_filter = request.args.get('tipo', None)
    organizacion_filter = request.args.get('organizacion', None)
    estado_filter = request.args.get('estado', None)
    enfoque_inclusivo_filter = request.args.get('enfoque_inclusivo', None)

    tipos = [r[0] for r in db.session.query(Actividades.tipo).distinct().all() if r[0]]
    organizaciones = Organizaciones.query.order_by(Organizaciones.nombre_org).all()
    discapacidades = Discapacidades.query.order_by(Discapacidades.nombre).all()
    estados = [e.value for e in EstadoActividad]
    preferencias_filter_options = Preferencias.query.order_by(Preferencias.nombre_corto).all()

    all_programs, compatibility_scores = get_programs_compatibility(
        tipo_filter=tipo_filter,
        organizacion_filter=organizacion_filter,
        estado_filter=estado_filter,
        enfoque_inclusivo=enfoque_inclusivo_filter,
        preferencia_filter=request.args.get('preferencia', None)
    )

    return render_template('programs.html',
                           programs=all_programs,
                           compatibility_scores=compatibility_scores,
                           tipos=tipos,
                           organizaciones=organizaciones,
                           discapacidades_filter_options=discapacidades,
                           preferencias_filter_options=preferencias_filter_options,
                           estados=estados,
                           current_filters=request.args)

@main_bp.route('/help')
def help_page():
    """Sirve la página de ayuda."""
    return render_template('help.html')

@main_bp.route('/api/chatbot/conversation', methods=['POST'])
def chatbot_conversation():
    """
    Endpoint para manejar las conversaciones del chatbot.
    Recibe un mensaje del usuario y devuelve la respuesta del chatbot.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request, no JSON payload."}), 400

    user_message = data.get('userMessage')
    session_id = data.get('sessionId')
    # message_type = data.get('messageType') # 'text' or 'voice' - useful for analytics or specific handling

    if not user_message:
        return jsonify({"error": "Missing 'userMessage' in request."}), 400
    if not session_id:
        return jsonify({"error": "Missing 'sessionId' in request."}), 400

    try:
        # Utiliza el alias importado para llamar al servicio de chatbot
        bot_response_text = get_openai_chatbot_response(user_message, session_id)
        return jsonify({"response": bot_response_text})
    except Exception as e:
        # Log the exception for server-side review
        print(f"Error in chatbot_conversation endpoint: {e}")
        # Return a generic error to the client
        return jsonify({"error": "An error occurred while processing your message."}), 500
