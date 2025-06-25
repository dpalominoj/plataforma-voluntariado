import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from sklearn.ensemble import RandomForestClassifier # Importar RandomForestClassifier
from datetime import datetime
from services.prediction_service import PredictionService
from model.models import Usuarios, Inscripciones, Notificaciones, InteraccionesChatbot, Actividades, Organizaciones
from database.db import db # Necesario para el contexto de la app

# Importar la aplicación Flask para el contexto
from main import app # Asegúrate de que 'main' es el nombre de tu archivo principal de Flask app

class TestPredictionService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        self.organizer_id = 1
        self.prediction_service = PredictionService(threshold=0.5)

        self.mock_user_patch = patch('services.prediction_service.Usuarios', autospec=True)
        self.mock_inscription_patch = patch('services.prediction_service.Inscripciones', autospec=True)
        self.mock_notification_patch = patch('services.prediction_service.Notificaciones', autospec=True)
        self.mock_interaction_patch = patch('services.prediction_service.InteraccionesChatbot', autospec=True)
        self.mock_activity_patch = patch('services.prediction_service.Actividades', autospec=True)
        self.mock_db_session_patch = patch('services.prediction_service.db.session', autospec=True)

        self.MockUser = self.mock_user_patch.start()
        self.MockInscription = self.mock_inscription_patch.start()
        self.MockNotification = self.mock_notification_patch.start()
        self.MockInteraction = self.mock_interaction_patch.start()
        self.MockActivity = self.mock_activity_patch.start()
        self.mock_db_session = self.mock_db_session_patch.start()

        self.mock_db_session.query.return_value.filter.return_value.all.return_value = []
        self.mock_db_session.query.return_value.filter_by.return_value.all.return_value = []
        self.mock_db_session.query.return_value.all.return_value = []


    def tearDown(self):
        self.mock_user_patch.stop()
        self.mock_inscription_patch.stop()
        self.mock_notification_patch.stop()
        self.mock_interaction_patch.stop()
        self.mock_activity_patch.stop()
        self.mock_db_session_patch.stop()

    def _mock_query_results(self, activity_ids_result=None, registrations_result=None,
                            inscriptions_result=None, notifications_result=None, interactions_result=None):

        def query_side_effect(*args, **kwargs):
            mock_query = MagicMock()
            if args == (self.MockActivity.id_actividad,):
                mock_query.filter.return_value.all.return_value = activity_ids_result if activity_ids_result is not None else []
            elif args == (self.MockUser.id_usuario, self.MockUser.fecha_registro):
                mock_query.all.return_value = registrations_result if registrations_result is not None else []
            elif args == (self.MockInscription.id_usuario, self.MockInscription.fecha_inscripcion):
                mock_query.filter.return_value.all.return_value = inscriptions_result if inscriptions_result is not None else []
            elif args == (self.MockNotification.id_usuario, self.MockNotification.fecha_envio):
                mock_query.filter.return_value.all.return_value = notifications_result if notifications_result is not None else []
            elif args == (self.MockInteraction.id_usuario, self.MockInteraction.fecha):
                mock_query.all.return_value = interactions_result if interactions_result is not None else []
            else:
                mock_query.filter.return_value.all.return_value = []
                mock_query.all.return_value = []
            return mock_query
        self.mock_db_session.query.side_effect = query_side_effect

    def test_get_data_empty(self):
        self._mock_query_results(activity_ids_result=[(1,)])
        df = self.prediction_service._get_data(self.organizer_id)
        self.assertTrue(df.empty)

    def test_get_data_with_sample_data(self):
        activity_ids = [(101,)]
        user_regs = [(1, datetime(2023, 1, 1, 10, 0, 0))]
        inscriptions = [(1, datetime(2023, 1, 2, 12, 0, 0))]
        notifications = [(1, datetime(2023, 1, 3, 9, 0, 0))]
        interactions = [(1, datetime(2023, 1, 4, 15, 0, 0))]

        self._mock_query_results(
            activity_ids_result=activity_ids,
            registrations_result=user_regs,
            inscriptions_result=inscriptions,
            notifications_result=notifications,
            interactions_result=interactions
        )

        df = self.prediction_service._get_data(self.organizer_id)
        self.assertEqual(len(df), 4)
        self.assertIn('event_type', df.columns)
        self.assertIn('timestamp', df.columns)

    def test_preprocess_data_empty(self):
        features, target = self.prediction_service._preprocess_data(pd.DataFrame(), self.organizer_id)
        self.assertTrue(features.empty)
        self.assertTrue(target.empty)

    def test_preprocess_data_with_sample_data(self):
        data = {
            'user_id': [1, 1, 2, 2],
            'timestamp': [datetime(2023, 1, 1, 10, 30, 0), datetime(2023, 1, 1, 18, 0, 0),
                          datetime(2023, 1, 2, 9, 0, 0), datetime(2023, 1, 2, 22, 0, 0)],
            'event_type': ['registration', 'inscription', 'notification_read', 'chatbot_interaction']
        }
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        features, target = self.prediction_service._preprocess_data(df, self.organizer_id)

        self.assertEqual(len(features), 4)
        self.assertEqual(len(target), 4)
        self.assertListEqual(list(features.columns), self.prediction_service.feature_names)
        self.assertTrue(all(target == 1))

    @patch('services.prediction_service.PredictionService._get_data')
    @patch('services.prediction_service.PredictionService._preprocess_data')
    @patch('services.prediction_service.RandomForestClassifier')
    @patch('services.prediction_service.accuracy_score')
    def test_train_model_sufficient_data(self, mock_accuracy_score, MockRandomForestClassifier,
                                         mock_preprocess_data, mock_get_data):
        mock_model_instance = MagicMock()
        MockRandomForestClassifier.return_value = mock_model_instance
        mock_get_data.return_value = pd.DataFrame({'col1': range(20)})
        mock_features = pd.DataFrame({
            'hour_of_day': [10, 14, 9, 18] * 5,
            'day_of_week': [0, 0, 1, 1] * 5,
            'is_weekend': [0, 0, 0, 0] * 5,
            'recent_notification_read': [1,0,0,0] * 5,
            'recent_interaction': [0,1,0,0] * 5,
            'recent_registration': [0,0,1,0] * 5,
            'recent_inscription': [0,0,0,1] * 5
        })
        mock_target = pd.Series([1, 0, 1, 0] * 5)
        mock_preprocess_data.return_value = (mock_features, mock_target)
        mock_model_instance.predict.return_value = [1, 0, 1, 0]
        mock_accuracy_score.return_value = 0.85

        service_instance = PredictionService(threshold=0.5)
        service_instance.train_model(self.organizer_id)

        mock_get_data.assert_called_once_with(self.organizer_id)
        mock_preprocess_data.assert_called_once()
        MockRandomForestClassifier.assert_called_once_with(n_estimators=100, random_state=42)
        mock_model_instance.fit.assert_called_once()
        mock_model_instance.predict.assert_called_once()
        mock_accuracy_score.assert_called_once()
        self.assertEqual(service_instance.accuracy, 0.85)

    @patch('services.prediction_service.PredictionService._get_data')
    def test_train_model_insufficient_data(self, mock_get_data):
        mock_get_data.return_value = pd.DataFrame({'col1': [1, 2]})
        self.prediction_service.train_model(self.organizer_id)
        self.assertEqual(self.prediction_service.accuracy, 0.0)

    @patch('services.prediction_service.PredictionService.train_model')
    @patch('sklearn.ensemble.RandomForestClassifier.predict_proba')
    def test_get_optimal_time_slots_success(self, mock_predict_proba, mock_train_model):
        self.prediction_service.accuracy = 0.7

        mock_model_instance = MagicMock(spec=RandomForestClassifier)
        mock_model_instance.classes_ = [0, 1]
        self.prediction_service.model = mock_model_instance

        num_hours = 24
        num_days = 7
        mock_probas = []
        for day in range(num_days):
            for hour in range(num_hours):
                if hour == 10:
                    mock_probas.append([0.1, 0.9])
                elif hour == 14:
                    mock_probas.append([0.4, 0.6])
                else:
                    mock_probas.append([0.8, 0.2])

        self.prediction_service.model.predict_proba.return_value = pd.DataFrame(mock_probas).values

        slots = self.prediction_service.get_optimal_time_slots(self.organizer_id, num_slots=2)

        mock_train_model.assert_called_once_with(self.organizer_id)
        self.prediction_service.model.predict_proba.assert_called_once()
        self.assertIsInstance(slots, list)
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]['start_time'], "10:00")
        self.assertEqual(slots[1]['start_time'], "14:00")

    @patch('services.prediction_service.PredictionService.train_model')
    def test_get_optimal_time_slots_low_accuracy(self, mock_train_model):
        self.prediction_service.accuracy = 0.4

        result = self.prediction_service.get_optimal_time_slots(self.organizer_id)

        mock_train_model.assert_called_once_with(self.organizer_id)
        self.assertIsInstance(result, str)
        self.assertIn("La precisión del modelo", result)

    @patch('services.prediction_service.PredictionService.train_model')
    def test_get_optimal_time_slots_model_not_trained(self, mock_train_model):
        self.prediction_service.accuracy = 0.0

        result = self.prediction_service.get_optimal_time_slots(self.organizer_id)

        mock_train_model.assert_called_once_with(self.organizer_id)
        if self.prediction_service.threshold > 0:
            self.assertIn("La precisión del modelo", result)
        else:
            self.assertIn("El modelo no ha sido entrenado", result)

if __name__ == '__main__':
    unittest.main()
