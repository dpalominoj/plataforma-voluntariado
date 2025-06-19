from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_app(app):
    """Initializes the database with the Flask app."""
    db.init_app(app)
