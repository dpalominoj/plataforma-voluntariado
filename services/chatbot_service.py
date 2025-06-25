import os
import requests
from openai import OpenAI

OPENAI_API_GIST_URL = "https://gist.githubusercontent.com/dpalominoj/968d0b2c0f9e2862cefca820c6449120/raw/c527693336ad058c4d36fa91aa5dee68bda994c5/DevKey.txt"

def get_api_key_from_url(url: str) -> str | None:
    try:
        response = requests.get(url)
        response.raise_for_status() 
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error al leer la API key desde la URL ({url}): {e}")
        return None

OPENAI_API_KEY = get_api_key_from_url(OPENAI_API_GIST_URL)
client = None

if not OPENAI_API_KEY:
    print(f"Advertencia: No se pudo obtener la API Key desde {OPENAI_API_GIST_URL}. El servicio de chatbot no funcionará.")
    print("Intentando obtener API Key desde la variable de entorno OPENAI_API_KEY...")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        print("Advertencia: La variable de entorno OPENAI_API_KEY tampoco está configurada.")
    else:
        print("API Key obtenida exitosamente desde la variable de entorno.")

if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("Cliente OpenAI inicializado exitosamente.")
    except Exception as e:
        print(f"Error al inicializar el cliente OpenAI con la clave proporcionada: {e}")
        client = None
else:
    print("Error crítico: No se pudo obtener una API Key de OpenAI. El cliente no se puede inicializar.")


# Platform knowledge base for contextual responses
PLATFORM_CONTEXT = """
Eres un asistente virtual para VoluntarioPlus, una plataforma inclusiva de voluntariado.

INFORMACIÓN DE LA PLATAFORMA:
- VoluntarioPlus conecta voluntarios con organizaciones y causas sociales
- Enfoque en inclusión y accesibilidad universal
- Más de 15,000 voluntarios activos y 500+ programas disponibles
- Presencia en más de 50 ciudades

CATEGORÍAS DE PROGRAMAS DISPONIBLES:
1. Educación - Apoyo escolar, alfabetización digital, enseñanza
2. Medio Ambiente - Huertos comunitarios, conservación, sostenibilidad
3. Salud - Cuidado de adultos mayores, promoción de salud
4. Tecnología - Alfabetización digital, soporte técnico
5. Animales - Refugios, cuidado y socialización
6. Alimentación - Bancos de alimentos, distribución de comidas

FUNCIONALIDADES PRINCIPALES:
- Búsqueda inteligente de programas por categoría y ubicación
- Sistema de aplicación a programas de voluntariado
- Plataforma accesible con soporte para lectores de pantalla
- Interfaz multiidioma
- Gestión flexible de horarios
- Sistema de reconocimientos y certificados

NAVEGACIÓN DEL SITIO:
- Inicio: Información general y programas destacados
- Programas: Catálogo completo con filtros de búsqueda
- Ayuda: Centro de soporte, FAQ y formulario de contacto

PROCESO DE REGISTRO:
1. Hacer clic en "Únete Ahora"
2. Completar perfil con información básica
3. Seleccionar áreas de interés
4. Verificación de información
5. Conexión con oportunidades relevantes

CONTACTO:
- Teléfono: +52 55 1234 5678
- Email: ayuda@voluntarioplus.org
- Chatbot disponible 24/7

Responde siempre en español, sé útil y amigable. Si no sabes algo específico, dirige al usuario al centro de ayuda o sugiere contactar por teléfono/email.
"""

conversation_history = {}

def get_chatbot_response(user_message: str, session_id: str):
    if not client:
        return "El servicio de chatbot no está disponible actualmente debido a un problema de configuración (API key). Por favor, contacta con el soporte."

    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {"role": "system", "content": PLATFORM_CONTEXT}
        ]

    conversation_history[session_id].append({"role": "user", "content": user_message})

    # Keep the history to a reasonable length to manage token usage
    max_history_length = 10 # Considerar si este límite es adecuado para gpt-4o y el contexto
    if len(conversation_history[session_id]) > max_history_length:
        # Asegura que el mensaje de sistema (PLATFORM_CONTEXT) siempre esté presente
        system_message = conversation_history[session_id][0]
        recent_messages = conversation_history[session_id][-(max_history_length-1):]
        conversation_history[session_id] = [system_message] + recent_messages

    try:
        completion = client.chat.completions.create(
            model="gpt-4o", # Actualizado a gpt-4o
            messages=conversation_history[session_id]
        )
        bot_response = completion.choices[0].message.content

        if bot_response:
            conversation_history[session_id].append({"role": "assistant", "content": bot_response})
            return bot_response
        else:
            return "I'm sorry, I didn't get a response. Could you try asking differently?"

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        error_message = str(e).lower()
        if "incorrect api key" in error_message or "authentication" in error_message:
            return "There's an issue with the chatbot service configuration (API key problem). Please contact support."
        elif "rate limit" in error_message:
            return "The chatbot service is currently experiencing high demand. Please try again in a few moments."
        return "I'm having a little trouble understanding right now. Please try again in a moment."

if __name__ == '__main__':
    # Este bloque es para pruebas directas del servicio de chatbot.
    # Asegúrate de tener la variable de entorno OPENAI_API_KEY configurada si ejecutas este script directamente.
    if not OPENAI_API_KEY or not client:
        print("Prueba __main__ abortada: La variable de entorno OPENAI_API_KEY no está configurada o el cliente OpenAI no se pudo inicializar.")
    else:
        print("Intentando prueba directa de chatbot_service.py con la clave API de entorno.")
        test_session_1 = "test_session_main_001"
        
        print(f"\nUser (S1): Hola")
        response1 = get_chatbot_response('Hola', test_session_1)
        print(f"Bot (S1): {response1}")

        if "El servicio de chatbot no está disponible actualmente" not in response1 and "API key problem" not in response1 :
            print(f"\nUser (S1): Busco oportunidades de voluntariado.")
            response2 = get_chatbot_response('Busco oportunidades de voluntariado.', test_session_1)
            print(f"Bot (S1): {response2}")
        else:
            print("\nNo se pueden realizar más pruebas debido a un problema de configuración del chatbot.")

        # Limpiar historial para la próxima ejecución si es necesario
        conversation_history.clear()
