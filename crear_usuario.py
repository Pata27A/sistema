# crear_usuario.py

from app import db, create_app
from app.models import User, Role

app = create_app()

with app.app_context():
    # Crear roles si no existen
    rol_admin = Role.query.filter_by(name='admin').first()
    if not rol_admin:
        rol_admin = Role(name='admin', description='Administrador del sistema')
        db.session.add(rol_admin)
        db.session.commit()
        print("Rol 'admin' creado.")

    # Verificar si ya existe el usuario
    user = User.query.filter_by(username='admin').first()
    if user:
        print("El usuario 'admin' ya existe.")
    else:
        # Crear el usuario
        user = User(
            username='admin',
            email='admin@example.com',
            first_name='Administrador',
            last_name='Sistema',
            role=rol_admin
        )
        user.set_password('123456')  # Podés cambiar la contraseña
        db.session.add(user)
        db.session.commit()
        print("Usuario 'admin' creado correctamente.")
