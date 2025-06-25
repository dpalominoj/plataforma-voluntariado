import requests

# URL de tu Gist con el token de Hugging Face
HF_API_GIST_URL = "https://gist.githubusercontent.com/dpalominoj/9dba92625b104eba4d093a10cf37a6cb/raw/dce732f795ae1ad64ab093800fd764e4b5f66645/token_hf.txt"

def get_api_link(url: str) -> str | None:
    try:
        response = requests.get(url)
        response.raise_for_status() 
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error al leer la API key desde la URL ({url}): {e}")
        return None

# Obtener el token de Hugging Face
HF_API_KEY = get_api_link(HF_API_GIST_URL)

# Modelos válidos:
# FUNCIONA aunque alucina: API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"

def query(prompt: str):
    try:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": f"[INST] {prompt} Responde solo si tienes información precisa. [/INST]", "parameters": {"max_new_tokens": 200}}
        )
        response.raise_for_status()  # Lanza error si hay 404/500
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error en la API: {e}\nRevisa: 1) Token válido, 2) Modelo disponible, 3) URL correcta")
        return None

# Ejemplo de uso
if HF_API_KEY:
    respuesta = query("¿Cómo funciona DeepSeek?")
    print(respuesta[0]["generated_text"] if respuesta else "Falló la consulta")
else:
    print("No se encontró el token de Hugging Face")
