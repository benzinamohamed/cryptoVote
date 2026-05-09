from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from app.routes.main import main_bp
    from app.routes.commissioner import commissioner_bp
    from app.routes.administrator import administrator_bp
    from app.routes.anonymizer import anonymizer_bp
    from app.routes.counter import counter_bp
    from app.routes.voter import voter_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(commissioner_bp, url_prefix='/commissioner')
    app.register_blueprint(administrator_bp, url_prefix='/administrator')
    app.register_blueprint(anonymizer_bp, url_prefix='/anonymizer')
    app.register_blueprint(counter_bp, url_prefix='/counter')
    app.register_blueprint(voter_bp, url_prefix='/voter')

    with app.app_context():
        db.create_all()

    return app
