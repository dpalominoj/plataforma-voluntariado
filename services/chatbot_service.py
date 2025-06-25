import os
import requests
from openai import OpenAI

def get_api_link(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"Error al obtener la API key desde la URL: {e}")
        return None

OPENAI_API_URL = "https://gist.githubusercontent.com/dpalominoj/968d0b2c0f9e2862cefca820c6449120/raw/a279a3b50f4a719aa1de5aee73c7eaeb25a2bff0/DevKey.txt"
OPENAI_API_KEY = get_api_link(OPENAI_API_URL)

if not OPENAI_API_KEY:
    print("Error al inicializar el cliente OpenAI con la clave proporcionada: {e}")
    client = None
else:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Advertencia: No se pudo obtener la clave de API {e}.")
        client = None

conversation_history = {}

def get_chatbot_response(user_message: str, session_id: str):
    if not client:
        return "The chatbot service is currently unavailable due to a configuration issue (API key missing or invalid). Please contact support."

    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {"role": "system", "content": "You are a helpful assistant for a volunteer platform. Help users find volunteer opportunities and get support. Be friendly and concise."}
        ]

    conversation_history[session_id].append({"role": "user", "content": user_message})

    # Keep the history to a reasonable length to manage token usage
    max_history_length = 10
    if len(conversation_history[session_id]) > max_history_length:
        conversation_history[session_id] = [conversation_history[session_id][0]] + conversation_history[session_id][-(max_history_length-1):]

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
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
    if not OPENAI_API_KEY:
        print("Cannot run __main__ test: OPENAI_API_KEY environment variable is not set.")
    else:
        print("Attempting direct test of chatbot_service.py with environment API key.")
        test_session_1 = "test_session_main_001"
        print(f"User (S1): Hola")
        print(f"Bot (S1): {get_chatbot_response('Hola', test_session_1)}")

        print(f"User (S1): Busco oportunidades de voluntariado.")
        print(f"Bot (S1): {get_chatbot_response('Busco oportunidades de voluntariado.', test_session_1)}")

        # Clear history for next run if needed
        conversation_history.clear()
