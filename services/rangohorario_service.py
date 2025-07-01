import pandas as pd
# Imports de scikit-learn eliminados ya que no se entrena un modelo aquí, se usa análisis directo.
# from sklearn.model_selection import train_test_split
# from sklearn.ensemble import RandomForestClassifier
# from sklearn.metrics import accuracy_score
from model.models import Actividades # Organizaciones, Usuarios, Inscripciones, Notificaciones, InteraccionesChatbot ya no son necesarias aquí
from database.db import db
# from sqlalchemy import func, cast, Date, Time # Ya no son necesarios aquí
# from datetime import datetime, timedelta # Ya no son necesarios aquí

class PredictionService:
    # El constructor ya no necesita el umbral de precisión del modelo.
    # El MIN_INTERACTIONS_THRESHOLD se define directamente en get_optimal_time_slots.
    def __init__(self):
        # Ya no se entrena un modelo RandomForestClassifier aquí.
        # self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        # self.accuracy = 0.0
        # self.feature_names = [...] # Ya no son necesarios
        pass

    # El organizer_id ya no es necesario si los datos son globales del CSV.
    # Si se quisiera filtrar por organización en el futuro, se podría reintroducir.
    def get_optimal_time_slots(self, organizer_id=None, num_slots=3):
        # --- Data Collection from Synthetic CSV ---
        try:
            df_synthetic = pd.read_csv('database/synthetic_volunteer_data.csv')
        except FileNotFoundError:
            return "No se encontró el archivo de datos sintéticos en database/."
        except Exception as e:
            return f"Error al leer los datos sintéticos: {str(e)}"

        if df_synthetic.empty:
            return "El archivo de datos sintéticos está vacío."

        # Consider only 'opened' or 'clicked' actions as positive interactions
        df_interactions = df_synthetic[df_synthetic['action'].isin(['opened', 'clicked'])]

        if df_interactions.empty:
            return "No hay interacciones de 'apertura' o 'clic' en los datos sintéticos."

        try:
            df_interactions['timestamp'] = pd.to_datetime(df_interactions['timestamp'])
            df_interactions['hour'] = df_interactions['timestamp'].dt.hour
        except Exception as e:
            return f"Error al procesar timestamps: {str(e)}"

        # --- Analysis with Pandas ---
        hourly_activity_counts = df_interactions['hour'].value_counts().sort_index()
        hourly_activity_counts = hourly_activity_counts.reindex(range(24), fill_value=0)

        total_interactions = hourly_activity_counts.sum()
        MIN_INTERACTIONS_THRESHOLD = 10 # Umbral de interacciones mínimas

        if total_interactions < MIN_INTERACTIONS_THRESHOLD:
            return (f"La cantidad de interacciones procesadas ({total_interactions}) es demasiado baja "
                    f"(umbral: {MIN_INTERACTIONS_THRESHOLD}). No se pueden generar sugerencias confiables.")

        # Apply smoothing (3-hour rolling window, centered)
        smoothed_activity = hourly_activity_counts.rolling(window=3, center=True, min_periods=1).mean()

        # Group into 2-hour blocks
        bi_hourly_smoothed_activity = {}
        for hour_block_start in range(0, 24, 2): # 0, 2, ..., 22
            activity_in_block = smoothed_activity.get(hour_block_start, 0) + smoothed_activity.get(hour_block_start + 1, 0)
            bi_hourly_smoothed_activity[hour_block_start] = activity_in_block

        if not bi_hourly_smoothed_activity:
            return "No se pudo procesar la actividad horaria tras el suavizado."

        # Sort blocks by activity
        sorted_blocks = sorted(bi_hourly_smoothed_activity.items(), key=lambda item: item[1], reverse=True)

        significant_blocks = [(hour, activity) for hour, activity in sorted_blocks if activity > 0]
        top_blocks = significant_blocks[:num_slots] # Usar num_slots

        suggested_slots_list = [] # Cambiado a suggested_slots_list para evitar confusión con la variable de dashboard_routes
        if top_blocks:
            for block_start_hour, count in top_blocks:
                start_time_str = f"{str(block_start_hour).zfill(2)}:00"
                end_time_str = "00:00" if block_start_hour == 22 else f"{str(block_start_hour + 2).zfill(2)}:00"

                # En lugar de 'probability', usamos el 'count' que es la actividad agregada estimada.
                # Y el formato de salida debe ser una lista de diccionarios como antes,
                # o una lista de strings si la plantilla espera eso.
                # La plantilla organizer_dashboard.html espera una lista de objetos con .start_time y .end_time
                # o un string. Devolveremos la lista de diccionarios.
                suggested_slots_list.append({
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "estimated_activity": f"{count:.2f}" # Cambiado de 'probability' a 'estimated_activity'
                })

        if not suggested_slots_list:
            return "No se encontraron bloques horarios con actividad voluntaria significativa después del análisis y suavizado."

        return suggested_slots_list


if __name__ == '__main__':
    # Ejemplo de uso (opcional, para pruebas locales si es necesario)
    # service = PredictionService()
    # organizer_test_id = 1 # Simular un ID de organizador si fuera necesario para alguna lógica futura
    # results = service.get_optimal_time_slots(organizer_id=organizer_test_id)
    # print(results)
    pass
