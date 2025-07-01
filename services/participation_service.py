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
    # Primero, intenta obtener las características de la actividad real desde la BD
    actividad_real = Actividades.query.get(actividad_id)
    if not actividad_real:
        current_app.logger.warning(f"Actividad real con ID {actividad_id} no encontrada.")
        # Podríamos decidir si devolver None o usar valores por defecto si la actividad real no existe.
        # Por ahora, si la actividad real no existe, no podemos predecir para ella.
        return None

    # Estas son las características de la actividad para la cual queremos predecir.
    # Se obtienen de la base de datos como antes.
    cupo_maximo_real = actividad_real.cupo_maximo
    current_inscriptions_real = Inscripciones.query.filter_by(id_actividad=actividad_id).count()

    # Los placeholders se mantienen para la actividad real, ya que no tenemos datos sintéticos específicos para ella.
    # Si el modelo se entrena con datos sintéticos que tienen valores variados para estas columnas,
    # y la actividad real usa estos placeholders, el modelo podría no generalizar bien.
    # Idealmente, estas features también deberían ser realistas para la actividad objetivo.
    # Por ahora, mantenemos la lógica original para los placeholders de la actividad objetivo.
    historico_similar_real = 0.5
    habilidades_voluntarios_real = 3

    features = {
        "current_inscriptions": current_inscriptions_real,
        "cupo_maximo": cupo_maximo_real,
        "historico_similar": historico_similar_real, # Placeholder
        "habilidades_voluntarios": habilidades_voluntarios_real # Placeholder
    }
    return features

def predecir_participacion(actividad_id):
    """
    Predice la probabilidad de alta participación para una actividad específica,
    utilizando un dataset sintético para el entrenamiento del modelo.
    """
    current_app.logger.info(f"Iniciando predicción de participación para actividad_id: {actividad_id}")

    # 1. Obtener características para la actividad objetivo (desde la BD)
    target_activity_features_dict = obtener_features(actividad_id)
    if target_activity_features_dict is None:
        current_app.logger.warning(f"No se pudieron obtener features para la actividad {actividad_id} desde la BD. Abortando.")
        return {"error": "No se encontraron características de la actividad objetivo."}

    feature_names = ['current_inscriptions', 'cupo_maximo', 'historico_similar', 'habilidades_voluntarios']
    try:
        # DataFrame para la actividad objetivo que se va a predecir
        target_activity_df = pd.DataFrame([target_activity_features_dict], columns=feature_names)
    except Exception as e:
        current_app.logger.error(f"Error al crear DataFrame para actividad específica: {e}")
        return {"error": "Fallo al crear DataFrame para la actividad objetivo."}

    # 2. Preparar datos de entrenamiento desde el CSV sintético
    try:
        synthetic_data_df = pd.read_csv('database/synthetic_activity_participation_data.csv')
        current_app.logger.info(f"Cargadas {len(synthetic_data_df)} filas desde el dataset sintético.")
    except FileNotFoundError:
        current_app.logger.error("No se encontró el archivo de datos sintéticos: database/synthetic_activity_participation_data.csv")
        return {"probabilidad": 0.5, "metricas": "Dataset sintético no encontrado", "tree_dot_file": None, "info": "Predicción por defecto."}
    except Exception as e:
        current_app.logger.error(f"Error al leer el dataset sintético: {e}")
        return {"probabilidad": 0.5, "metricas": "Error al leer dataset sintético", "tree_dot_file": None, "info": "Predicción por defecto."}

    if synthetic_data_df.empty:
        current_app.logger.info("El dataset sintético está vacío.")
        return {"probabilidad": 0.5, "metricas": "Dataset sintético vacío", "tree_dot_file": None, "info": "Predicción por defecto."}

    # Asegurarse de que las columnas esperadas existan en el CSV
    if not all(col in synthetic_data_df.columns for col in feature_names):
        missing_cols = [col for col in feature_names if col not in synthetic_data_df.columns]
        current_app.logger.error(f"Columnas faltantes en el dataset sintético: {missing_cols}")
        return {"error": f"Columnas faltantes en dataset sintético: {missing_cols}"}

    X_df = synthetic_data_df[feature_names]

    # Crear la variable objetivo 'y' a partir de los datos sintéticos
    y_data = []
    for index, row in synthetic_data_df.iterrows():
        if row['cupo_maximo'] is not None and row['cupo_maximo'] > 0:
            ocupacion = row['current_inscriptions'] / row['cupo_maximo']
            y_data.append(1 if ocupacion >= 0.6 else 0)
        else:
            y_data.append(0) # Baja participación por defecto si no hay cupo o es 0

    y_series = pd.Series(y_data)

    if X_df.empty: # Debería ser redundante si synthetic_data_df.empty ya se verificó
        current_app.logger.warning("No se pudieron extraer features del dataset sintético (X_df vacío).")
        return {"probabilidad": 0.5, "metricas": "Sin datos de entrenamiento del CSV", "tree_dot_file": None, "info": "Predicción por defecto."}

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
