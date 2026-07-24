import os

basedir = os.path.abspath(os.path.dirname(__file__))

VIDEO_DIR = os.path.join(basedir, "videos")

try:
    if not os.path.exists(VIDEO_DIR):
        os.makedirs(VIDEO_DIR, exist_ok=True)
except OSError:
    VIDEO_DIR = "/tmp/videos"
    os.makedirs(VIDEO_DIR, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "gizli_anahtar"
    
    db_path = os.path.join(basedir, "sign-language-recognition.sqlite")
    if not os.path.exists(db_path):
        db_path = "/tmp/sign-language-recognition.sqlite"
        
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + db_path
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/0"
