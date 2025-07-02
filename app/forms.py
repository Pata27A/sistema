from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SelectField, BooleanField, PasswordField, DateTimeField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, ValidationError
from app.models import User, Customer, Supplier, Product, Category
import re

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Contraseña', validators=[DataRequired()])

class CustomerForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(), Length(max=200)])
    ruc = StringField('RUC', validators=[Optional(), Length(max=20)])
    phone = StringField('Teléfono', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Dirección')
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    is_active = BooleanField('Activo', default=True)
    
    def validate_ruc(self, field):
        if field.data:
            # Basic RUC validation for Paraguay
            ruc = field.data.replace('-', '').replace('.', '')
            if not re.match(r'^\d{6,8}-\d{1}$', field.data) and not ruc.isdigit():
                raise ValidationError('RUC debe tener formato válido (ej: 12345678-9)')

class SupplierForm(FlaskForm):
    name = StringField('Nombre/Razón Social', validators=[DataRequired(), Length(max=200)])
    ruc = StringField('RUC', validators=[DataRequired(), Length(max=20)])
    phone = StringField('Teléfono', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Dirección')
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    contact_person = StringField('Persona de Contacto', validators=[Optional(), Length(max=200)])
    is_active = BooleanField('Activo', default=True)
    
    def validate_ruc(self, field):
        if field.data:
            ruc = field.data.replace('-', '').replace('.', '')
            if not re.match(r'^\d{6,8}-\d{1}$', field.data) and not ruc.isdigit():
                raise ValidationError('RUC debe tener formato válido')

class CategoryForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descripción')
    is_active = BooleanField('Activo', default=True)

class ProductForm(FlaskForm):
    code = StringField('Código', validators=[DataRequired(), Length(max=50)])
    name = StringField('Nombre', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Descripción')
    category_id = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    unit = SelectField('Unidad', choices=[
        ('unidad', 'Unidad'),
        ('kg', 'Kilogramo'),
        ('litros', 'Litros'),
        ('metros', 'Metros'),
        ('cajas', 'Cajas'),
        ('paquetes', 'Paquetes')
    ], default='unidad')
    cost_price = DecimalField('Precio Costo', validators=[Optional(), NumberRange(min=0)], places=2)
    sale_price = DecimalField('Precio Venta', validators=[DataRequired(), NumberRange(min=0)], places=2)
    iva_type = SelectField('Tipo IVA', choices=[
        ('10', '10%'),
        ('5', '5%'),
        ('exento', 'Exento')
    ], default='10')
    stock_current = IntegerField('Stock Actual', validators=[Optional(), NumberRange(min=0)], default=0)
    stock_min = IntegerField('Stock Mínimo', validators=[Optional(), NumberRange(min=0)], default=0)
    stock_max = IntegerField('Stock Máximo', validators=[Optional(), NumberRange(min=0)], default=100)
    is_active = BooleanField('Activo', default=True)
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(is_active=True).all()]

class SaleDetailForm(FlaskForm):
    product_id = SelectField('Producto', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)])
    unit_price = DecimalField('Precio Unitario', validators=[DataRequired(), NumberRange(min=0)], places=2)
    
    def __init__(self, *args, **kwargs):
        super(SaleDetailForm, self).__init__(*args, **kwargs)
        self.product_id.choices = [(p.id, f"{p.code} - {p.name}") for p in Product.query.filter_by(is_active=True).all()]

class SaleForm(FlaskForm):
    invoice_number = StringField('Número de Factura', validators=[DataRequired(), Length(max=50)])
    customer_id = SelectField('Cliente', coerce=int, validators=[Optional()])
    payment_method = SelectField('Método de Pago', choices=[
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia')
    ], default='efectivo')
    notes = TextAreaField('Observaciones')
    
    def __init__(self, *args, **kwargs):
        super(SaleForm, self).__init__(*args, **kwargs)
        customers = [(0, 'Cliente Ocasional')] + [(c.id, c.name) for c in Customer.query.filter_by(is_active=True).all()]
        self.customer_id.choices = customers

class PurchaseForm(FlaskForm):
    invoice_number = StringField('Número de Factura', validators=[DataRequired(), Length(max=50)])
    supplier_id = SelectField('Proveedor', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Observaciones')
    
    def __init__(self, *args, **kwargs):
        super(PurchaseForm, self).__init__(*args, **kwargs)
        self.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.filter_by(is_active=True).all()]

class UserForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('Nombre', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Apellido', validators=[DataRequired(), Length(max=80)])
    password = PasswordField('Contraseña', validators=[Optional(), Length(min=6)])
    role_id = SelectField('Rol', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Activo', default=True)
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        from models import Role
        self.role_id.choices = [(r.id, r.description) for r in Role.query.all()]

class CashMovementForm(FlaskForm):
    type = SelectField('Tipo', choices=[
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso')
    ], validators=[DataRequired()])
    amount = DecimalField('Monto', validators=[DataRequired(), NumberRange(min=0)], places=2)
    description = StringField('Descripción', validators=[DataRequired(), Length(max=200)])
