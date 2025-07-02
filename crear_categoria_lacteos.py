# crear_categoria_lacteos.py

from app import create_app, db
from app.models import Category

# Inicializa la app de Flask
app = create_app()

# Ejecutar en contexto de la app
with app.app_context():
    # Verificar si ya existe
    existente = Category.query.filter_by(name='Lácteos').first()
    
    if existente:
        print("⚠️ La categoría 'Lácteos' ya existe con ID:", existente.id)
    else:
        # Crear nueva categoría
        nueva_categoria = Category(
            name='Lácteos',
            description='Productos derivados de la leche como queso, leche, yogur, etc.'
        )

        db.session.add(nueva_categoria)
        db.session.commit()
        print("✅ Categoría 'Lácteos' creada exitosamente con ID:", nueva_categoria.id)
