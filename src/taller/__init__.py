import os
from flask import Flask, render_template, session, redirect, url_for
from config import config
from .extensions import db, migrate
from .models import Pregunta


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
    
    

    @app.get("/")
    def index():
       return render_template("index.html")
       
    
    @app.get("/foro")
    def foro():
        user_id = session.get("usuario_id")  
        if not user_id:
            return redirect(url_for("auth.login_get"))

        from .models import Categoria
        if not Categoria.query.first():
            db.session.add(Categoria(nombre="General"))
            db.session.commit()

        preguntas = Pregunta.query.order_by(Pregunta.creada_en.desc()).all()
        return render_template("foro.html", preguntas=preguntas, user_id=user_id)

    return app
