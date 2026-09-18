import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify, request
from backend.config import Config
from backend.database import db
from backend.routes.customer import customer_bp
from backend.routes.transactions import transactions_bp
from backend.routes.bank import bank_bp
from backend.services.seed_service import seed_bank_user

def create_app(config_class=Config):
    """Application factory for TrustGuard AI."""
    # Compute frontend folder paths
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'))

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config_class)

    # Ensure database folder exists
    os.makedirs(Config.DATABASE_DIR, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(customer_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(bank_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('base.html', error_message="Page Not Found (404)"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'An internal server error occurred.'}), 500
        return render_template('base.html', error_message="Internal Server Error (500)"), 500

    # Auto-create SQLite database tables and seed demo users on startup
    with app.app_context():
        # Import models so SQLAlchemy metadata is aware of tables
        import backend.models
        db.create_all()
        seed_bank_user()

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"==================================================")
    print(f" TrustGuard AI - Intelligent Financial Platform   ")
    print(f" Server running at: http://127.0.0.1:{port}      ")
    print(f" Database: {Config.DATABASE_DIR}/trustguard.db   ")
    print(f" Dataset:  {Config.DATASET_PATH}                ")
    print(f"==================================================")
    app.run(host='0.0.0.0', port=port, debug=True)
