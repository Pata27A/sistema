import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_migrate import Migrate

logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Configuración
    app.secret_key = os.environ.get("SESSION_SECRET", "clave-super-secreta")
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = None
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:123456@localhost/ferreteria_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Importar modelos y rutas para que se registren
    from app import models
    from app.routes import main_bp  # Ajustar según el nombre de tu blueprint

    app.register_blueprint(main_bp)

    # Configuración login_manager
    login_manager.login_view = 'main.login'  # nombre del endpoint con blueprint
    login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

# Filtro personalizado para mostrar números como guaraníes
    def formato_guaranies(value):
        try:
            return 'Gs. {:,.0f}'.format(value).replace(',', '.')
        except:
            return value

    app.jinja_env.filters['guaranies'] = formato_guaranies

    return app


def initialize_data():
    """Inicializa roles y admin si no existen."""
    from app import db, models
    from werkzeug.security import generate_password_hash

    with db.session.begin():
        admin_role = models.Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = models.Role(name='admin', description='Administrador del sistema')
            db.session.add(admin_role)

        vendedor_role = models.Role.query.filter_by(name='vendedor').first()
        if not vendedor_role:
            vendedor_role = models.Role(name='vendedor', description='Vendedor')
            db.session.add(vendedor_role)

        cajero_role = models.Role.query.filter_by(name='cajero').first()
        if not cajero_role:
            cajero_role = models.Role(name='cajero', description='Cajero')
            db.session.add(cajero_role)

        admin_user = models.User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = models.User(
                username='admin',
                email='admin@ferreteria.py',
                password_hash=generate_password_hash('admin123'),
                first_name='Administrador',
                last_name='Sistema',
                is_active=True,
                role=admin_role
            )
            db.session.add(admin_user)

    logging.info("Roles y usuario admin inicializados correctamente")


# Crear instancia de app para run.py
app = create_app()
