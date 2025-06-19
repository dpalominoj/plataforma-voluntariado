from flask import current_app # Para logging
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# random y numpy ya no son necesarios

# TODO: Si se implementa una llamada real a una API, podría ser necesaria la biblioteca 'requests'.

def get_compatibility_scores(user_profile, programs_or_activities):
    """
    Calcula los puntajes de compatibilidad entre un perfil de usuario y una lista de programas o actividades.

    Args:
        user_profile (dict): Diccionario con el perfil del usuario.
                             Ejemplo: {'id': 1, 'interests': ['medio ambiente', 'educación'], 'skills': ['python', 'gestión de proyectos'], 'disabilities': ['visual']}
        programs_or_activities (list): Lista de diccionarios, donde cada diccionario representa un programa o actividad.
                                       Ejemplo: [{'id': 101, 'name': 'Limpieza de Playa', 'description': 'Ayuda a limpiar la playa X', 'category': 'medio ambiente', 'es_inclusiva': True, 'discapacidades_soportadas': ['visual', 'motriz']}]

    Returns:
        dict: Un diccionario que mapea item_id a un puntaje de compatibilidad (0.0 a 100.0).
              Retorna un diccionario vacío si la entrada no es válida.
    """
    scores = {}
    # Validar entradas
    if not user_profile or not isinstance(user_profile, dict) or \
       not programs_or_activities or not isinstance(programs_or_activities, list):
        current_app.logger.warning("Entrada inválida para get_compatibility_scores.")
        return scores

    current_app.logger.info(f"Calculando compatibilidad para el usuario: {user_profile.get('id', 'Usuario Desconocido')}")

    # Recopilar intereses y habilidades del perfil del usuario
    user_interests = user_profile.get('interests', [])
    user_skills = user_profile.get('skills', [])
    # Asegurarse de que sean listas de strings antes de unir
    user_interests_text = ' '.join(user_interests) if isinstance(user_interests, list) else ''
    user_skills_text = ' '.join(user_skills) if isinstance(user_skills, list) else ''
    user_text = user_interests_text + ' ' + user_skills_text
    user_text = user_text.strip()

    if not user_text: # Si no hay texto de usuario, no se puede comparar
        current_app.logger.warning("Perfil de usuario no contiene texto para comparar (intereses/habilidades).")
        return scores

    vectorizer = CountVectorizer()

    for program in programs_or_activities:
        if not isinstance(program, dict) or 'id' not in program:
            current_app.logger.warning(f"Omitiendo item inválido (no es dict o falta 'id'): {program}")
            continue

        item_id = program.get('id')
        program_description = program.get('description', '')
        program_category = program.get('category', '')

        # Asegurarse de que la descripción y categoría sean strings
        program_description = program_description if isinstance(program_description, str) else ''
        program_category = program_category if isinstance(program_category, str) else ''

        program_text = program_description + ' ' + program_category
        program_text = program_text.strip()

        if not program_text: # Si no hay texto de programa, no se puede comparar
            current_app.logger.warning(f"Programa {item_id} no contiene texto para comparar (descripción/categoría).")
            scores[item_id] = 0.0 # Asignar puntaje 0 si no hay con qué comparar
            continue

        try:
            # Crear vectores de conteo de palabras
            corpus = [user_text, program_text]
            X = vectorizer.fit_transform(corpus)

            # Calcular similitud del coseno
            # X[0] es el vector del usuario, X[1] es el vector del programa
            similarity_matrix = cosine_similarity(X[0:1], X[1:2])
            cosine_sim = similarity_matrix[0][0]

            # Normalizar puntaje a 0-100
            normalized_score = round(cosine_sim * 100, 1)

            # Ajustar puntaje basado en información de discapacidad
            user_disabilities = user_profile.get('disabilities', []) # Lista de discapacidades del usuario
            user_has_disability = bool(user_disabilities) # True si el usuario tiene alguna discapacidad

            program_is_inclusive = program.get('es_inclusiva', False) # Booleano
            program_supports_disabilities = program.get('discapacidades_soportadas', []) # Lista de discapacidades que soporta el programa

            # Asegurarse de que program_supports_disabilities sea una lista
            if not isinstance(program_supports_disabilities, list):
                program_supports_disabilities = []


            # Lógica de ajuste de puntaje por inclusión:
            # Aumentar si el programa es inclusivo y el usuario tiene discapacidades,
            # especialmente si alguna discapacidad del usuario está en la lista de soportadas.
            if program_is_inclusive and user_has_disability:
                # Aumento base por ser inclusivo y el usuario tener discapacidad
                normalized_score = min(100.0, normalized_score + 5.0)

                # Aumento adicional si hay coincidencia específica de discapacidad
                if any(disability in program_supports_disabilities for disability in user_disabilities):
                    normalized_score = min(100.0, normalized_score + 10.0) # Aumento mayor por coincidencia

            # (Opcional) Penalización si el programa NO es inclusivo pero el usuario SÍ tiene discapacidad
            # elif not program_is_inclusive and user_has_disability:
            #     normalized_score = max(0.0, normalized_score - 10.0)


            scores[item_id] = normalized_score
        except Exception as e:
            current_app.logger.error(f"Error al procesar programa {item_id}: {e}")
            scores[item_id] = 0.0 # Puntaje por defecto en caso de error

    current_app.logger.info(f"Puntajes de compatibilidad calculados: {scores}")
    return scores
