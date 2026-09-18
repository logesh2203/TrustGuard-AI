import os

# Base directory: root of the project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trustguard-ai-secure-secret-key-2026')
    
    # Database Configuration
    DATABASE_DIR = os.path.join(BASE_DIR, 'database')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(DATABASE_DIR, 'trustguard.db').replace('\\', '/')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Dataset Configuration
    DATASET_PATH = os.path.join(BASE_DIR, 'data', 'creditcard.csv')
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestConfig(Config):
    """Testing configuration with isolated test database."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'TEST_DATABASE_URL',
        f"sqlite:///{os.path.join(Config.DATABASE_DIR, 'test_trustguard.db').replace('\\', '/')}"
    )

