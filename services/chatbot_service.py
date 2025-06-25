import os
from openai import OpenAI

# Read the API key from an environment variable
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable not found. Chatbot service will not function correctly.")
    # You could raise an error here, or allow the app to run with the chatbot disabled
    # For now, we'll let it proceed, but API calls will fail if the key isn't truly available.
    client = None
else:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}. Check your API key and network.")
        client = None


# A simple in-memory store for conversation history per session_id
# For a production app, you'd use a more persistent store like Redis or a database.
conversation_history = {}

def get_chatbot_response(user_message: str, session_id: str):
    """
    Gets a response from the OpenAI API for the given user message and session.
    Maintains a basic conversation history for the session.
    """
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
    # For direct testing of this service, you'd need to set the OPENAI_API_KEY environment variable
    # e.g., export OPENAI_API_KEY='your_key_here' (in bash)
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
