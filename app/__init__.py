import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
from app.celery_utils import make_celery

celery = make_celery()


# Flask app instance
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
    )

    # Import parts of the app and create database tables
    with app.app_context():
        from app import routes, models, forms
        db.create_all()
        print("Database tables initialized successfully.")

    return app


db = SQLAlchemy()
