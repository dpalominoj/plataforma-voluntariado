import os
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

if not HF_API_KEY:
    print("No se pudo obtener el token de Hugging Face")
else:
    # Ejemplo de llamada a la API de Hugging Face (modelo Mistral)
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    def query(prompt: str):
        try:
            response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error en la API: {e}")
            return None

    # Probar el chatbot
    respuesta = query("¿Cómo funciona DeepSeek?")
    print(respuesta)
