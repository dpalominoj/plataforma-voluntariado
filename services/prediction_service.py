import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from model.models import Usuarios, Inscripciones, Notificaciones, InteraccionesChatbot, Actividades, Organizaciones
from database.db import db
from sqlalchemy import func, cast, Date, Time
from datetime import datetime, timedelta

class PredictionService:
    def __init__(self, threshold=0.6):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.threshold = threshold
        self.accuracy = 0.0
        self.feature_names = [
            'hour_of_day', 'day_of_week', 'is_weekend',
            'recent_notification_read', 'recent_interaction',
            'recent_registration', 'recent_inscription'
        ]

    def _get_data(self, organizer_id):
        activity_ids = db.session.query(Actividades.id_actividad)\
            .filter(Actividades.id_organizacion == organizer_id)\
            .all()
        activity_ids = [a_id[0] for a_id in activity_ids]

        if not activity_ids:
            return pd.DataFrame()

        user_registrations = db.session.query(
            Usuarios.id_usuario,
            Usuarios.fecha_registro
        ).all()
        df_registrations = pd.DataFrame(user_registrations, columns=['user_id', 'timestamp'])
        df_registrations['event_type'] = 'registration'

        inscriptions = db.session.query(
            Inscripciones.id_usuario,
            Inscripciones.fecha_inscripcion
        ).filter(Inscripciones.id_actividad.in_(activity_ids)).all()
        df_inscriptions = pd.DataFrame(inscriptions, columns=['user_id', 'timestamp'])
        df_inscriptions['event_type'] = 'inscription'

        notifications_read = db.session.query(
            Notificaciones.id_usuario,
            Notificaciones.fecha_envio
        ).filter(Notificaciones.leida == True).all()
        df_notifications = pd.DataFrame(notifications_read, columns=['user_id', 'timestamp'])
        df_notifications['event_type'] = 'notification_read'

        chatbot_interactions = db.session.query(
            InteraccionesChatbot.id_usuario,
            InteraccionesChatbot.fecha
        ).all()
        df_chatbot = pd.DataFrame(chatbot_interactions, columns=['user_id', 'timestamp'])
        df_chatbot['event_type'] = 'chatbot_interaction'

        df = pd.concat([df_registrations, df_inscriptions, df_notifications, df_chatbot], ignore_index=True)

        if df.empty:
            return pd.DataFrame()

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def _preprocess_data(self, df, organizer_id):
        if df.empty:
            return pd.DataFrame(), pd.Series(dtype='int')

        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_good_time'] = 1

        df['recent_notification_read'] = df['event_type'].apply(lambda x: 1 if x == 'notification_read' else 0)
        df['recent_interaction'] = df['event_type'].apply(lambda x: 1 if x == 'chatbot_interaction' else 0)
        df['recent_registration'] = df['event_type'].apply(lambda x: 1 if x == 'registration' else 0)
        df['recent_inscription'] = df['event_type'].apply(lambda x: 1 if x == 'inscription' else 0)

        features = df[self.feature_names]
        target = df['is_good_time']

        return features, target

    def train_model(self, organizer_id):
        data_df = self._get_data(organizer_id)
        if data_df.empty or len(data_df) < 10:
            self.accuracy = 0.0
            print(f"No hay suficientes datos para entrenar el modelo para el organizador {organizer_id}.")
            return

        features, target = self._preprocess_data(data_df, organizer_id)

        if features.empty or target.empty:
            self.accuracy = 0.0
            print(f"Características o target vacíos tras preprocesamiento para el organizador {organizer_id}.")
            return

        if len(target.unique()) < 2:
            print(f"Solo se encontró una clase en los datos de target para el organizador {organizer_id}. No se puede entrenar el modelo.")
            self.accuracy = 0.0
            return

        X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42, stratify=target if len(target.unique()) > 1 else None)

        self.model.fit(X_train, y_train)
        predictions = self.model.predict(X_test)
        self.accuracy = accuracy_score(y_test, predictions)
        print(f"Modelo entrenado para organizador {organizer_id}. Precisión: {self.accuracy:.2f}")


    def get_optimal_time_slots(self, organizer_id, num_slots=3):
        self.train_model(organizer_id)

        if self.accuracy < self.threshold:
            return f"La precisión del modelo ({self.accuracy:.2f}) es demasiado baja (umbral: {self.threshold:.2f}). No se pueden generar sugerencias confiables."

        if not hasattr(self.model, 'classes_'):
             return "El modelo no ha sido entrenado o no hay suficientes datos."

        possible_hours = range(24)
        possible_days = range(7)

        test_data = []
        for day in possible_days:
            for hour in possible_hours:
                test_data.append({
                    'hour_of_day': hour,
                    'day_of_week': day,
                    'is_weekend': 1 if day in [5, 6] else 0,
                    'recent_notification_read': 0,
                    'recent_interaction': 0,
                    'recent_registration': 0,
                    'recent_inscription': 0
                })

        df_test = pd.DataFrame(test_data)
        df_test = df_test[self.feature_names]

        try:
            probabilities = self.model.predict_proba(df_test)[:, 1]
        except Exception as e:
            return f"Error al predecir probabilidades: {e}"

        df_test['probability'] = probabilities
        hourly_avg_prob = df_test.groupby('hour_of_day')['probability'].mean().sort_values(ascending=False)

        suggested_slots = []
        for hour, prob in hourly_avg_prob.head(num_slots).items():
            suggested_slots.append({
                "start_time": f"{hour:02d}:00",
                "end_time": f"{(hour + 1) % 24:02d}:00",
                "probability": f"{prob:.2f}"
            })

        if not suggested_slots:
            return "No se pudieron generar sugerencias horarias."

        return suggested_slots

if __name__ == '__main__':
    # Bloque de prueba local eliminado para limpieza, ya que las pruebas unitarias son el enfoque principal.
    pass
