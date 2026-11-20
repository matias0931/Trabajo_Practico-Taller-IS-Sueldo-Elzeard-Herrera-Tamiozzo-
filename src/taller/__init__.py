import os
from flask import Flask 
from config import config
from .extensions import db, migrate


def create_app(environment="development"):
    app=Flask (__name__, instance_relative_config=True)

    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_object(config[environment])

    db.init_app(app)
    migrate.init_app(app, db)
    from .import models
    #Routes 
    from .routes.auth import bp as auth_bp
    from .routes.questions import bp as questions_bp
    from .routes.answers import bp as answers_bp
    from .routes.votes import bp as votes_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(answers_bp)
    app.register_blueprint(votes_bp)

    return app
