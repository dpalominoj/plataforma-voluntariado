"""
Módulo de servicio para predecir los niveles de participación en actividades.

Este módulo proporciona funciones para:
- Extraer características para una actividad dada (`obtener_features`).
- Entrenar un modelo RandomForest y predecir la probabilidad de alta participación
  para una actividad específica (`predecir_participacion`).
"""
from flask import current_app # Para logging
from model.models import Inscripciones, Actividades, db
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import export_graphviz
from sklearn.model_selection import train_test_split

def obtener_features(actividad_id):
    """
    Obtiene y calcula características (features) de una actividad específica.

    Estas características se utilizan como entrada para el modelo de predicción
    de participación.

    Args:
        actividad_id (int): El ID de la actividad para la cual obtener características.

    Returns:
        dict or None: Un diccionario con las siguientes características:
            - "current_inscriptions" (int): Número actual de inscritos.
            - "cupo_maximo" (int): Capacidad máxima de la actividad.
            - "historico_similar" (float): Placeholder para participación histórica
                                           en actividades similares (actualmente 0.5).
            - "habilidades_voluntarios" (int): Placeholder para el nivel/cantidad
                                               de habilidades de voluntarios
                                               requeridas/disponibles (actualmente 3).
        Retorna None si la actividad no se encuentra.
    """
    actividad = Actividades.query.get(actividad_id)
    if not actividad:
        current_app.logger.warning(f"Actividad con ID {actividad_id} no encontrada.")
        return None

    cupo_maximo = actividad.cupo_maximo
    current_inscriptions = Inscripciones.query.filter_by(id_actividad=actividad_id).count()

    historico_similar = 0.5
    habilidades_voluntarios = 3

    features = {
        "current_inscriptions": current_inscriptions,
        "cupo_maximo": cupo_maximo,
        "historico_similar": historico_similar,
        "habilidades_voluntarios": habilidades_voluntarios
    }
    return features

def predecir_participacion(actividad_id):
    """
    Predice la probabilidad de alta participación para una actividad específica.

    El proceso incluye:
    1. Obtener características para la actividad objetivo.
    2. Preparar datos de entrenamiento:
        - Obtener características para todas las actividades históricas.
        - Crear una variable objetivo ('y') basada en un proxy:
          Se considera 'alta participación' (1) si la ocupación actual
          (inscripciones / cupo_maximo) es >= 60%, de lo contrario 'baja' (0).
          Esta es una simplificación y podría necesitar ajustes.
    3. Manejar datos insuficientes (si hay menos de 10 muestras o solo una clase,
       devuelve una predicción por defecto).
    4. Entrenar un modelo RandomForestClassifier con los datos históricos.
       El modelo se re-entrena con cada llamada a esta función.
    5. Generar una predicción de probabilidad para la actividad objetivo.
    6. Opcionalmente, exportar una visualización del primer árbol del modelo
       a un archivo .dot (si Graphviz está disponible).
    7. Calcular métricas básicas (precisión) sobre un conjunto de prueba.

    Args:
        actividad_id (int): El ID de la actividad para la cual predecir la participación.

    Returns:
        dict: Un diccionario conteniendo:
            - 'probabilidad' (float): La probabilidad predicha de alta participación (clase 1).
                                     Puede ser una probabilidad por defecto si el modelo no se entrena.
            - 'metricas' (dict or str): Un diccionario con métricas como 'accuracy' (precisión),
                                        o un string indicando por qué no se calcularon
                                        (ej., "Sin datos de entrenamiento", "Datos insuficientes para entrenar").
            - 'tree_dot_file' (str or None): Nombre del archivo .dot generado para la visualización
                                             del árbol (ej., "tree.dot"), o None si no se generó.
            - 'error' (str, opcional): Un mensaje de error si ocurrió un problema crítico.
            - 'info' (str, opcional): Un mensaje informativo, especialmente si se devuelve
                                     una predicción por defecto debido a datos insuficientes.
    """
    current_app.logger.info(f"Iniciando predicción de participación para actividad_id: {actividad_id}")

    target_activity_features_dict = obtener_features(actividad_id)
    if target_activity_features_dict is None:
        current_app.logger.warning(f"No se pudieron obtener features para la actividad {actividad_id}. Abortando.")
        return {"error": "No se encontraron características de la actividad."}

    feature_names = ['current_inscriptions', 'cupo_maximo', 'historico_similar', 'habilidades_voluntarios']
    try:
        target_activity_df = pd.DataFrame([target_activity_features_dict], columns=feature_names)
    except Exception as e:
        current_app.logger.error(f"Error al crear DataFrame para actividad específica: {e}")
        return {"error": "Fallo al crear DataFrame para la actividad objetivo."}

    all_activities = Actividades.query.all()
    if not all_activities:
        current_app.logger.info("No hay actividades en la base de datos para entrenar el modelo.")
        return {"probabilidad": 0.5, "metricas": "Sin datos de entrenamiento", "tree_dot_file": None, "info": "Predicción por defecto debido a falta de actividades."}

    X_data = []
    y_data = []

    current_app.logger.info(f"Procesando {len(all_activities)} actividades para datos de entrenamiento.")
    for activity in all_activities:
        features_dict = obtener_features(activity.id_actividad)
        if features_dict:
            X_data.append(features_dict)
            if features_dict['cupo_maximo'] is not None and features_dict['cupo_maximo'] > 0:
                ocupacion = features_dict['current_inscriptions'] / features_dict['cupo_maximo']
                y_data.append(1 if ocupacion >= 0.6 else 0)
            else: # Si no hay cupo máximo o es 0, se considera baja participación por defecto para y_data
                y_data.append(0)

    if not X_data:
        current_app.logger.warning("No se pudieron extraer features para ninguna actividad de entrenamiento.")
        return {"probabilidad": 0.5, "metricas": "Sin datos de entrenamiento", "tree_dot_file": None, "info": "Predicción por defecto debido a falta de datos de características."}

    X_df = pd.DataFrame(X_data, columns=feature_names)
    y_series = pd.Series(y_data)

    MIN_SAMPLES_FOR_TRAINING = 10
    if len(X_df) < MIN_SAMPLES_FOR_TRAINING or len(y_series.unique()) < 2:
        current_app.logger.info(f"Datos insuficientes para entrenar el modelo. Muestras: {len(X_df)}, Clases: {len(y_series.unique()) if X_data else 0}.")
        default_proba = y_series.mean() if len(y_series) > 0 and len(y_series.unique()) == 1 else 0.5
        return {"probabilidad": default_proba,
                "metricas": "Datos insuficientes para entrenar",
                "tree_dot_file": None,
                "info": f"Predicción por defecto. Muestras: {len(X_df)}, Clases: {len(y_series.unique()) if X_data else 0}"}

    current_app.logger.info(f"Datos de entrenamiento preparados: {X_df.shape[0]} muestras.")

    try:
        X_train, X_test, y_train, y_test = train_test_split(X_df, y_series, test_size=0.2, random_state=42, stratify=y_series if len(y_series.unique()) > 1 else None)
        modelo = RandomForestClassifier(random_state=42, class_weight='balanced')
        modelo.fit(X_train, y_train)
        current_app.logger.info("Modelo RandomForestClassifier entrenado exitosamente.")
    except Exception as e:
        current_app.logger.error(f"Error durante el entrenamiento del modelo: {e}")
        return {"probabilidad": y_series.mean() if len(y_series) > 0 else 0.5, "metricas": f"Error de entrenamiento: {e}", "tree_dot_file": None, "info": "Predicción por defecto debido a error de entrenamiento."}

    try:
        # Asegurar que el DataFrame de la actividad objetivo tenga las mismas columnas que X_df (datos de entrenamiento)
        # Esto es importante si la actividad objetivo tiene valores nulos que resultaron en menos columnas al crear target_activity_df inicialmente
        target_activity_df = pd.DataFrame([target_activity_features_dict], columns=feature_names)[X_df.columns]
        proba = modelo.predict_proba(target_activity_df)[0][1]
        current_app.logger.info(f"Predicción de probabilidad para actividad {actividad_id}: {proba}")
    except Exception as e:
        current_app.logger.error(f"Error durante la predicción para la actividad {actividad_id}: {e}")
        return {"error": f"Error de predicción: {e}"}

    tree_dot_file_path = 'tree.dot'
    try:
        estimator = modelo.estimators_[0]
        export_graphviz(estimator, out_file=tree_dot_file_path,
                        feature_names=X_df.columns,
                        class_names=['Baja', 'Alta'], # Clases deben estar en español si es posible
                        rounded=True, proportion=False, precision=2, filled=True)
        current_app.logger.info(f"Visualización del árbol de decisión guardada en: {tree_dot_file_path}")
    except Exception as e:
        current_app.logger.warning(f"Error al exportar el árbol de decisión: {e}. Graphviz podría no estar instalado.")
        tree_dot_file_path = None

    try:
        accuracy = modelo.score(X_test, y_test)
        metricas = {"accuracy": accuracy} # 'accuracy' es un término común, se puede mantener o traducir a 'precision_global'
        current_app.logger.info(f"Métricas del modelo: {metricas}")
    except Exception as e:
        current_app.logger.error(f"Error al calcular métricas: {e}")
        metricas = {"accuracy": "Error al calcular métricas"}

    return {
        'probabilidad': proba,
        'metricas': metricas,
        'tree_dot_file': tree_dot_file_path
    }
