import requests
from typing import Dict, List

# a. datos simulados de BD
DATOS_VOLUNTARIADO = {
    "programas_activos": {
        "Lectura_inclusiva": {
            "nombre": "Taller de lectura inclusiva",
            "categoria": "Educación y Formación",
            "cupos": 20,
            "disponible": True
        },
        "Deporte_inclusivo": {
            "nombre": "Jornada deportiva inclusiva",
            "categoria": "Deporte y Recreación",
            "cupos": "ilimitados",
            "disponible": True
        },
        "Limpieza_Costera": {
            "nombre": "Campaña de Limpieza Costera",
            "categoria": "Ambiente y Sostenibilidad",
            "cupos": 15,
            "disponible": True
        }
    },
    "accesibilidad": {
        "discapacidad_visual": ["Lectura_inclusiva"],
        "discapacidad_motriz": ["Deporte_inclusivo"],
        "discapacidad_auditiva": []
    }
}

# b. contexto fijo
PLATFORM_CONTEXT = """
Eres un asistente virtual para KONECTAi, una plataforma inclusiva de voluntariado. Responde de manera amable y profesional.
Información clave:
- Categorias de Programas: Niños y Adolescentes, Educación y formación, Ambiente y sostenibilidad, Deporte y recreación.
"""

# d. Modelos válidos API de Hugging Face
# FUNCIONA aunque alucina: API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_TOKEN_URL = "https://gist.githubusercontent.com/dpalominoj/9dba92625b104eba4d093a10cf37a6cb/raw/dce732f795ae1ad64ab093800fd764e4b5f66645/token_hf.txt"

def get_hf_token():
    try:
        resp = requests.get(HF_TOKEN_URL, timeout=5)
        resp.raise_for_status()
        return resp.text.strip()
    except Exception:
        return None

# e. Historial de conversaciones
conversation_history: Dict[str, List[Dict[str, str]]] = {}

def get_chatbot_response(user_message: str, session_id: str) -> str:
    # Verifica si el cliente está configurado para HF
    hf_token = get_hf_token()
    if not hf_token:
        return "El servicio de chatbot no está disponible actualmente (API key no configurada). Por favor, contacta con soporte."

    # Inicializa el historial si es nueva sesión
    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {"role": "system", "content": "Eres un asistente útil para una plataforma de voluntariado. Sé amable y conciso."},
            {"role": "system", "content": PLATFORM_CONTEXT}
        ]

    # Añade el mensaje del usuario al historial
    conversation_history[session_id].append({"role": "user", "content": user_message})
    # Genera el prompt dinámico con datos de ejemplo
    contexto_actualizado = f"""
    [CONTEXTO ACTUALIZADO]
    **Programas Activos y Cupos**:
        - {DATOS_VOLUNTARIADO["programas_activos"]["Lectura_inclusiva"]["nombre"]} ({DATOS_VOLUNTARIADO["programas_activos"]["Lectura_inclusiva"]["categoria"]}): {'Disponible' if DATOS_VOLUNTARIADO["programas_activos"]["Lectura_inclusiva"]["disponible"] else 'Agotado'} | Cupos: {DATOS_VOLUNTARIADO["programas_activos"]["Lectura_inclusiva"]["cupos"]}.
        - {DATOS_VOLUNTARIADO["programas_activos"]["Deporte_inclusivo"]["nombre"]} ({DATOS_VOLUNTARIADO["programas_activos"]["Deporte_inclusivo"]["categoria"]}): {'Disponible' if DATOS_VOLUNTARIADO["programas_activos"]["Deporte_inclusivo"]["disponible"] else 'Agotado'} | Cupos: {DATOS_VOLUNTARIADO["programas_activos"]["Deporte_inclusivo"]["cupos"]}.
        - {DATOS_VOLUNTARIADO["programas_activos"]["Limpieza_Costera"]["nombre"]} ({DATOS_VOLUNTARIADO["programas_activos"]["Limpieza_Costera"]["categoria"]}): {'Disponible' if DATOS_VOLUNTARIADO["programas_activos"]["Limpieza_Costera"]["disponible"] else 'Agotado'} | Cupos: {DATOS_VOLUNTARIADO["programas_activos"]["Limpieza_Costera"]["cupos"]}.
    **Accesibilidad**:
        - Discapacidad Visual: {', '.join([DATOS_VOLUNTARIADO["programas_activos"][p]["nombre"] for p in DATOS_VOLUNTARIADO["accesibilidad"]["discapacidad_visual"]]) or 'Ningún programa disponible'}.
        - Discapacidad Motriz: {', '.join([DATOS_VOLUNTARIADO["programas_activos"][p]["nombre"] for p in DATOS_VOLUNTARIADO["accesibilidad"]["discapacidad_motriz"]]) or 'Ningún programa disponible'}.
        - Discapacidad Auditiva: {', '.join([DATOS_VOLUNTARIADO["programas_activos"][p]["nombre"] for p in DATOS_VOLUNTARIADO["accesibilidad"]["discapacidad_auditiva"]]) or 'Ningún programa disponible'}.
    {PLATFORM_CONTEXT}
    """   

    prompt = f"""
    [INST] {contexto_actualizado}
    
    Historial de conversación:
    {conversation_history[session_id]}

    Pregunta actual: {user_message}
    Reglas:
    1. Usa los datos proporcionados para responder.
    2. Si no sabes, ofrece los contactos.
    3. Sé breve (1-2 líneas).
    [/INST]
    """

    try:
        # Llama a la API de Hugging Face
        response = requests.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {hf_token}"},
            json={
                "inputs": prompt,
                "parameters": {"temperature": 0.2, "max_new_tokens": 150}
            }
        )
        respuesta = response.json()[0]["generated_text"]

        # Filtra el prompt, respuestas vacías o errores
        if '[/INST]' in respuesta:
            respuesta = respuesta.split('[/INST]', 1)[-1].strip()

        if "no tengo información" in respuesta.lower():
            respuesta = "No tengo datos sobre eso. Por favor contáctanos: +51 968 875 239 | ayuda@konectai.org"

        # Añade la respuesta al historial
        conversation_history[session_id].append({"role": "assistant", "content": respuesta})
        return respuesta

    except Exception as e:
        return f"Error temporal. Por favor contáctanos directamente: +51 919 168 212"
        
