import csv
from tracemalloc import start
from flask import Blueprint, render_template, request, redirect, send_from_directory, url_for, flash, jsonify, make_response, abort
from flask_login import login_user, logout_user, login_required, current_user
import pdfkit
from sqlalchemy import and_, func
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from decimal import Decimal
import json
from app import db
from app.models import *
from app.forms import *
from app.script.rg90_validacion_compras import validar_linea
from app.script.rg90_validacion_ventas import validar_lineav
from app.utils import *
from flask import send_file
from io import BytesIO
import pandas as pd
from app.pdf_utils import render_pdf_from_template
from app.utils_pdf_reportes import render_pdf_template
from generar_archivo_rg90_ventas import generar_archivo_rg90_ventas
from generar_archivo_rg90_compras import generar_archivo_rg90_compras


main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Bienvenido, {user.first_name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    return render_template('login.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('main.index'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()
    today_sales = Sale.query.filter(
        Sale.sale_date >= today,
        Sale.status == 'completed'
    ).all()
    today_revenue = sum(sale.total for sale in today_sales)

    low_stock_products = Product.query.filter(
        Product.stock_current <= Product.stock_min,
        Product.is_active == True
    ).limit(5).all()

    recent_sales = Sale.query.filter_by(status='completed').order_by(
        Sale.created_at.desc()
    ).limit(10).all()

    return render_template('dashboard.html',
                           today_sales_count=len(today_sales),
                           today_revenue=today_revenue,
                           low_stock_products=low_stock_products,
                           recent_sales=recent_sales,
                           moment=datetime.now())

# Customers
@main_bp.route('/customers')
@login_required
def customers_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = Customer.query
    if search:
        query = query.filter(Customer.name.contains(search))
    customers = query.order_by(Customer.name).paginate(page=page, per_page=20, error_out=False)
    return render_template('customers/list.html', customers=customers, search=search)

@main_bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
def customers_new():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            ruc=form.ruc.data,
            phone=form.phone.data,
            address=form.address.data,
            email=form.email.data,
            is_active=form.is_active.data
        )
        db.session.add(customer)
        db.session.commit()
        flash('Cliente creado exitosamente', 'success')
        return redirect(url_for('main.customers_list'))
    return render_template('customers/form.html', form=form, title='Nuevo Cliente')

@main_bp.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def customers_edit(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        form.populate_obj(customer)
        db.session.commit()
        flash('Cliente actualizado exitosamente', 'success')
        return redirect(url_for('main.customers_list'))
    return render_template('customers/form.html', form=form, title='Editar Cliente')

# Suppliers
@main_bp.route('/suppliers')
@login_required
def suppliers_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = Supplier.query
    if search:
        query = query.filter(Supplier.name.contains(search))
    suppliers = query.order_by(Supplier.name).paginate(page=page, per_page=20, error_out=False)
    return render_template('suppliers/list.html', suppliers=suppliers, search=search)

@main_bp.route('/suppliers/new', methods=['GET', 'POST'])
@login_required
def suppliers_new():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            ruc=form.ruc.data,
            phone=form.phone.data,
            address=form.address.data,
            email=form.email.data,
            contact_person=form.contact_person.data,
            is_active=form.is_active.data
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Proveedor creado exitosamente', 'success')
        return redirect(url_for('main.suppliers_list'))
    return render_template('suppliers/form.html', form=form, title='Nuevo Proveedor')

@main_bp.route('/suppliers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def suppliers_edit(id):
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)
    if form.validate_on_submit():
        form.populate_obj(supplier)
        db.session.commit()
        flash('Proveedor actualizado exitosamente', 'success')
        return redirect(url_for('main.suppliers_list'))
    return render_template('suppliers/form.html', form=form, title='Editar Proveedor')

# Products
@main_bp.route('/products')
@login_required
def products_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)

    query = Product.query
    if search:
        query = query.filter(db.or_(Product.name.contains(search), Product.code.contains(search)))
    if category_id:
        query = query.filter_by(category_id=category_id)

    products = query.order_by(Product.name).paginate(page=page, per_page=20, error_out=False)
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('products/list.html',
                           products=products,
                           categories=categories,
                           search=search,
                           selected_category=category_id)

@main_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def products_new():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            code=form.code.data,
            name=form.name.data,
            description=form.description.data,
            category_id=form.category_id.data,
            unit=form.unit.data,
            cost_price=form.cost_price.data,
            sale_price=form.sale_price.data,
            iva_type=form.iva_type.data,
            stock_current=form.stock_current.data,
            stock_min=form.stock_min.data,
            stock_max=form.stock_max.data,
            is_active=form.is_active.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('main.products_list'))
    return render_template('products/form.html', form=form, title='Nuevo Producto')

@main_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def products_edit(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.commit()
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('main.products_list'))
    return render_template('products/form.html', form=form, title='Editar Producto')

# Sales
# 📄 Listado de ventas
@main_bp.route('/sales')
@login_required
def sales_list():
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    query = Sale.query.filter_by(status='completed')
    if start_date:
        query = query.filter(Sale.sale_date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Sale.sale_date <= datetime.strptime(end_date, '%Y-%m-%d'))
    sales = query.order_by(Sale.sale_date.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('sales/list.html', sales=sales)

# 🧾 Formulario y creación de nueva venta
@main_bp.route('/sales/new', methods=['GET', 'POST'])
@login_required
def sales_new():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            try:
                empresa = Empresa.query.first()
                if not empresa:
                    return jsonify({'error': 'Datos de empresa no configurados'}), 500

                # Generar número correlativo
                last_sale = Sale.query.order_by(Sale.id.desc()).first()
                next_number = 1
                if last_sale:
                    try:
                        next_number = int(last_sale.document_number) + 1
                    except:
                        next_number = 1
                document_number = f"{next_number:07d}"

                # Crear la venta
                sale = Sale(
                    customer_id=data.get('customer_id') or None,
                    user_id=current_user.id,
                    empresa_id=empresa.id,
                    sale_condition='contado',  # fijo como mencionaste
                    currency=empresa.moneda,
                    establishment=empresa.establecimiento,
                    issue_point=empresa.punto_expedicion,
                    document_number=document_number,
                    timbrado_numero=empresa.timbrado_numero,
                    notes=data.get('notes', ''),
                    status='completed'
                )
                db.session.add(sale)
                db.session.flush()  # obtener ID antes del commit

                subtotal = Decimal('0')
                iva_5 = Decimal('0')
                iva_10 = Decimal('0')

                for item in data.get('items', []):
                    product = Product.query.get(item['product_id'])
                    if not product:
                        return jsonify({'error': 'Producto no encontrado'}), 400

                    quantity = int(item['quantity'])
                    unit_price = Decimal(str(item['unit_price']))
                    item_subtotal = quantity * unit_price

                    detail = SaleDetail(
                        sale_id=sale.id,
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=unit_price,
                        subtotal=item_subtotal,
                        iva_type=product.iva_type
                    )
                    db.session.add(detail)

                    product.stock_current -= quantity

                    subtotal += item_subtotal
                    if product.iva_type == '5':
                        iva_5 += calculate_iva(item_subtotal, '5')
                    elif product.iva_type == '10':
                        iva_10 += calculate_iva(item_subtotal, '10')

                total = subtotal

                sale.subtotal = subtotal
                sale.iva_5 = iva_5
                sale.iva_10 = iva_10
                sale.total = total

                # Desglose de pagos
                pagos = data.get('payment_breakdown', {})
                efectivo = Decimal(str(pagos.get('efectivo', 0)))
                tarjeta = Decimal(str(pagos.get('tarjeta', 0)))
                transferencia = Decimal(str(pagos.get('transferencia', 0)))

                if efectivo > 0:
                    db.session.add(CashMovement(
                        type='ingreso',
                        amount=efectivo,
                        description=f'Venta en efectivo - Factura {sale.establishment}-{sale.issue_point}-{sale.document_number}',
                        reference_type='sale',
                        reference_id=sale.id,
                        user_id=current_user.id
                    ))
                if tarjeta > 0:
                    db.session.add(CashMovement(
                        type='ingreso',
                        amount=tarjeta,
                        description=f'Venta con tarjeta - Factura {sale.establishment}-{sale.issue_point}-{sale.document_number}',
                        reference_type='sale',
                        reference_id=sale.id,
                        user_id=current_user.id
                    ))
                if transferencia > 0:
                    db.session.add(CashMovement(
                        type='ingreso',
                        amount=transferencia,
                        description=f'Venta por transferencia - Factura {sale.establishment}-{sale.issue_point}-{sale.document_number}',
                        reference_type='sale',
                        reference_id=sale.id,
                        user_id=current_user.id
                    ))

                db.session.commit()

                invoice_number = f"{sale.establishment}-{sale.issue_point}-{sale.document_number}"

                return jsonify({
                    'success': True,
                    'sale_id': sale.id,
                    'invoice_number': invoice_number
                })

            except Exception as e:
                db.session.rollback()
                return jsonify({'error': f'Error al guardar la venta: {str(e)}'}), 500

    # GET: cargar formulario con datos
    empresa = Empresa.query.first()
    products = Product.query.filter_by(is_active=True).all()

    product_list = [{
        'id': p.id,
        'code': p.code,
        'name': p.name,
        'sale_price': float(p.sale_price),
        'stock_current': p.stock_current,
        'iva_type': p.iva_type
    } for p in products]

    return render_template(
        'sales/form.html',
        empresa=empresa,
        products=products,
        product_list=product_list
    )

# 📄 PDF de venta
@main_bp.route('/facturacion/pdf/<int:id>')
@login_required
def imprimir_factura(id):
    from decimal import Decimal
    sale = Sale.query.get_or_404(id)
    empresa = Empresa.query.first()

    # Calcular IVA
    iva_10 = 0
    iva_5 = 0
    iva_exento = 0
    for detalle in sale.details:
        subtotal = float(detalle.subtotal)
        tipo_iva = detalle.iva_type
        if tipo_iva == "10":
            iva_10 += round(subtotal / 11, 2)
        elif tipo_iva == "5":
            iva_5 += round(subtotal / 21, 2)
        else:
            iva_exento += subtotal

    cliente = sale.customer

    # Obtener movimientos de caja relacionados
    movimientos = CashMovement.query.filter_by(reference_type='sale', reference_id=sale.id).all()

    # Calcular total pagado desde movimientos
    total_pagado = sum([float(m.amount) for m in movimientos])
    vuelto = max(0, float(total_pagado) - float(sale.total))

    # Renderizar plantilla
    html = render_template(
        'sales/imprimir.html',
        factura=sale,
        empresa=empresa,
        iva_10=iva_10,
        iva_5=iva_5,
        iva_exento=iva_exento,
        cliente=cliente,
        total_pagado=total_pagado,
        vuelto=vuelto,
        movimientos=movimientos
    )

    options = {
        'page-width': '80mm',
        'margin-top': '0mm',
        'margin-bottom': '0mm',
        'margin-left': '0mm',
        'margin-right': '0mm',
        'encoding': "UTF-8",
        'enable-local-file-access': None
    }

    path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    pdf = pdfkit.from_string(html, False, options=options, configuration=config)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=factura_{sale.document_number}.pdf'
    return response
@main_bp.route('/api/next-invoice-number')
def api_next_invoice_number():
    empresa = Empresa.query.first()
    if not empresa:
        return jsonify({'invoice_number': '001-001-0000001'})  # fallback

    last_sale = Sale.query.order_by(Sale.id.desc()).first()

    if last_sale and last_sale.document_number.isdigit():
        try:
            last_num = int(last_sale.document_number)
            next_num = last_num + 1
        except:
            next_num = 1
    else:
        next_num = 1

    next_invoice = f"{empresa.establecimiento}-{empresa.punto_expedicion}-{next_num:07d}"

    return jsonify({'invoice_number': next_invoice})

# 🔍 Buscar cliente por RUC
@main_bp.route('/api/clientes')
def buscar_cliente_por_ruc():
    ruc = request.args.get('ruc')
    if not ruc:
        return jsonify({'error': 'RUC no proporcionado'}), 400

    cliente = Customer.query.filter_by(ruc=ruc).first()
    if cliente:
        return jsonify({
            'id': cliente.id,
            'name': cliente.name
        })
    else:
        return jsonify({'error': 'Cliente no encontrado'}), 404    
# Purchases
@main_bp.route('/purchases')
@login_required
def purchases_list():
    page = request.args.get('page', 1, type=int)
    purchases = Purchase.query.order_by(Purchase.purchase_date.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('purchases/list.html', purchases=purchases)

@main_bp.route('/purchases/new', methods=['GET', 'POST'])
@login_required
def purchases_new():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            purchase = Purchase(
                invoice_number=data.get('invoice_number'),
                supplier_id=data.get('supplier_id'),
                user_id=current_user.id,
                notes=data.get('notes', '')
            )
        db.session.add(purchase)
        db.session.flush()  # Necesario para obtener purchase.id

        subtotal = Decimal('0')
        iva_5 = Decimal('0')
        iva_10 = Decimal('0')

        for item in data.get('items', []):
            product = Product.query.get(item['product_id'])
            if not product:
                return jsonify({'error': 'Producto no encontrado'}), 400

            quantity = int(item['quantity'])
            unit_price = Decimal(str(item['unit_price']))
            item_subtotal = quantity * unit_price

            detail = PurchaseDetail(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=item_subtotal,
                iva_type=product.iva_type
            )
            db.session.add(detail)

            # ✅ Actualiza el producto
            product.stock_current += quantity
            product.cost_price = unit_price

            subtotal += item_subtotal
            if product.iva_type == '5':
                iva_5 += calculate_iva(item_subtotal, '5')
            elif product.iva_type == '10':
                iva_10 += calculate_iva(item_subtotal, '10')

        purchase.subtotal = subtotal
        purchase.iva_5 = iva_5
        purchase.iva_10 = iva_10
        purchase.total = subtotal + iva_5 + iva_10

        # ✅ Guardar movimiento de caja
        cash_movement = CashMovement(
            type='egreso',
            amount=purchase.total,
            description=f'Compra - Factura {purchase.invoice_number}',
            reference_type='purchase',
            reference_id=purchase.id,
            user_id=current_user.id
        )

        db.session.add(cash_movement)
        db.session.commit()

        return jsonify({
            'success': True,
            'purchase_id': purchase.id,
            'invoice_number': purchase.invoice_number
        })

    form = PurchaseForm()
    products = Product.query.filter_by(is_active=True).all()
    return render_template('purchases/form.html', form=form, products=products)

@main_bp.route('/api/suppliers/search')
def search_suppliers():
    query = request.args.get('q', '').lower()
    results = Supplier.query.filter(
        (Supplier.name.ilike(f'%{query}%')) |
        (Supplier.ruc.ilike(f'%{query}%'))
    ).limit(10).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'ruc': s.ruc
    } for s in results])

@main_bp.route('/api/products/search')
def search_products():
    query = request.args.get('q', '').lower()
    results = Product.query.filter(
        Product.code.ilike(f'%{query}%')
    ).limit(10).all()
    return jsonify([{
        'id': p.id,
        'code': p.code,
        'name': p.name,
        'cost_price': float(p.cost_price or 0),
        'iva_type': p.iva_type
    } for p in results])

# Cash Register
@main_bp.route('/cash', methods=['GET', 'POST'])
@login_required
def cash_register():
    today = datetime.now().date()
    movements = CashMovement.query.filter(
        CashMovement.movement_date >= today
    ).order_by(CashMovement.movement_date.desc()).all()

    total_ingresos = sum(m.amount for m in movements if m.type == 'ingreso')
    total_egresos = sum(m.amount for m in movements if m.type == 'egreso')
    balance = total_ingresos - total_egresos

    form = CashMovementForm()
    if form.validate_on_submit():
        movement = CashMovement(
            type=form.type.data,
            amount=form.amount.data,
            description=form.description.data,
            reference_type='manual',
            user_id=current_user.id,
            movement_date=datetime.now()
        )
        db.session.add(movement)
        db.session.commit()
        flash('Movimiento registrado exitosamente', 'success')
        return redirect(url_for('main.cash_register'))

    return render_template('cash/register.html',
                           movements=movements,
                           total_ingresos=total_ingresos,
                           total_egresos=total_egresos,
                           balance=balance,
                           form=form,
                           moment=datetime.now())


# Reports
@main_bp.route('/reports')
@login_required
def reports_index():
    return render_template('reports/index.html', moment=datetime.now())

@main_bp.route('/reports/sales')
@login_required
def reports_sales():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    query = Sale.query.filter_by(status='completed').filter(
        Sale.sale_date >= datetime.strptime(start_date, '%Y-%m-%d'),
        Sale.sale_date <= datetime.strptime(end_date, '%Y-%m-%d')
    )
    sales = query.all()
    total_revenue = sum(sale.total for sale in sales)
    return render_template('reports/sales.html',
                           sales=sales,
                           total_revenue=total_revenue,
                           start_date=start_date,
                           end_date=end_date)

# Admin
@main_bp.route('/admin/users')
@login_required
def admin_users():
    if not current_user.role or current_user.role.name != 'admin':
        abort(403)
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@main_bp.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
def admin_users_newa():
    if not current_user.role or current_user.role.name != 'admin':
        abort(403)
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role_id=form.role_id.data,
            is_active=form.is_active.data
        )
        if form.password.data:
            user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuario creado exitosamente', 'success')
        return redirect(url_for('main.admin_users'))
    return render_template('admin/user_form.html', form=form, title='Nuevo Usuario')

# API
@main_bp.route('/api/products/<int:id>')
@login_required
def api_product_detail(id):
    product = Product.query.get_or_404(id)
    return jsonify({
        'id': product.id,
        'code': product.code,
        'name': product.name,
        'sale_price': float(product.sale_price),
        'stock_current': product.stock_current,
        'iva_type': product.iva_type
    })

@main_bp.route('/api/customers/search')
@login_required
def api_customers_search():
    q = request.args.get('q', '')
    customers = Customer.query.filter(
        Customer.name.contains(q),
        Customer.is_active == True
    ).limit(10).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'ruc': c.ruc
    } for c in customers])

# Template Filters
@main_bp.app_template_filter('currency')
def currency_filter(amount):
    return format_currency(amount)

# Error Handlers
@main_bp.app_errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@main_bp.app_errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

#---------Empresa---------------
@main_bp.route('/empresa', methods=['GET', 'POST'])
@login_required
def empresa_datos():
    if not current_user.role.name == 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    empresa = Empresa.query.first()
    if request.method == 'POST':
        if not empresa:
            empresa = Empresa()

        empresa.nombre = request.form['nombre']
        empresa.ruc = request.form['ruc']
        empresa.direccion = request.form['direccion']
        empresa.ciudad = request.form['ciudad']
        empresa.telefono = request.form['telefono']
        empresa.timbrado_numero = request.form['timbrado_numero']
        empresa.timbrado_vigencia_desde = request.form['timbrado_vigencia_desde']
        empresa.timbrado_vigencia_hasta = request.form['timbrado_vigencia_hasta']
        empresa.establecimiento = request.form['establecimiento']
        empresa.punto_expedicion = request.form['punto_expedicion']
        empresa.moneda = request.form['moneda']

        db.session.add(empresa)
        db.session.commit()
        flash('Datos de la empresa guardados correctamente.', 'success')
        return redirect(url_for('main.empresa_datos'))

    return render_template('empresa/datos_empresa.html', empresa=empresa)

#-------------PDF y Excel----------------

@main_bp.route('/cash/export/excel')
@login_required
def export_cash_excel():
    today = datetime.now().date()
    movements = CashMovement.query.filter(
        CashMovement.movement_date >= today
    ).order_by(CashMovement.movement_date).all()

    data = [{
        'Hora': m.movement_date.strftime('%H:%M'),
        'Tipo': m.type.capitalize(),
        'Descripción': m.description,
        'Monto': float(m.amount),
        'Usuario': m.user.first_name if m.user else '---'
    } for m in movements]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Movimientos')

    output.seek(0)
    filename = f"movimientos_caja_{today.strftime('%Y%m%d')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@main_bp.route('/cash/export/pdf')
@login_required
def export_cash_pdf():
    today = datetime.now().date()
    movements = CashMovement.query.filter(
        CashMovement.movement_date >= today
    ).order_by(CashMovement.movement_date).all()

    total_ingresos = sum(m.amount for m in movements if m.type == 'ingreso')
    total_egresos = sum(m.amount for m in movements if m.type == 'egreso')
    balance = total_ingresos - total_egresos

    html = render_template('cash/pdf_report.html',
                           movements=movements,
                           total_ingresos=total_ingresos,
                           total_egresos=total_egresos,
                           balance=balance,
                           moment=datetime.now())

    pdf = render_pdf_from_template(html)
    filename = f"reporte_caja_{today.strftime('%Y%m%d')}.pdf"
    return send_file(BytesIO(pdf), download_name=filename, as_attachment=True, mimetype='application/pdf')

#-------------Reports PDF----------------
# --- RUTA: Ventas por período ---
@main_bp.route('/reports/sales/periodo', methods=['GET'])
@login_required
def reports_sales_period():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return redirect(url_for('main.reports_index'))

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

    sales = Sale.query.filter(Sale.sale_date >= start, Sale.sale_date < end).all()

    # Calcular totales generales
    total_general = sum(s.total or 0 for s in sales)
    total_iva_5 = sum(s.iva_5 or 0 for s in sales)
    total_iva_10 = sum(s.iva_10 or 0 for s in sales)
    subtotal_general = sum(s.subtotal or 0 for s in sales)
    total_exento = 0

    # Procesar ventas individuales con exento calculado por venta
    ventas = []
    for s in sales:
        exento = float(s.total or 0) - float(s.subtotal or 0) - float(s.iva_10 or 0) - float(s.iva_5 or 0)
        exento = max(exento, 0)
        total_exento += exento
        ventas.append({
            'venta': s,
            'exento': exento
        })

    totales = {
        'total': total_general,
        'iva_5': total_iva_5,
        'iva_10': total_iva_10,
        'subtotal': subtotal_general,
        'exento': total_exento
    }

    return render_pdf_template(
        'reports/pdf/ventas_periodo.html',
        sales=ventas,
        start=start,
        end=end,
        totales=totales,
        fecha_generacion=datetime.now(),
        user=current_user
    )

# --- RUTA: Productos más vendidos ---
@main_bp.route('/reports/sales/top-products', methods=['GET'])
@login_required
def reports_sales_top_products():
    today = datetime.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)

    top_products = (
        db.session.query(
            Product.code,
            Product.name,
            func.sum(SaleDetail.quantity).label('total_qty'),
            func.sum(SaleDetail.quantity * SaleDetail.unit_price).label('total_amount')
        )
        .join(SaleDetail.product)
        .join(SaleDetail.sale)
        .filter(Sale.sale_date >= start, Sale.sale_date < end)
        .group_by(Product.id)
        .order_by(func.sum(SaleDetail.quantity).desc())
        .limit(10)
        .all()
    )

    return render_pdf_template(
        'reports/pdf/productos_mas_vendidos.html',
        productos=top_products,
        start=start,
        end=end,
        fecha_generacion=datetime.now(),
        user=current_user
    )

# --- RUTA: Ventas por Cliente ---
@main_bp.route('/reports/sales/by-client', methods=['GET'])
@login_required
def reports_sales_by_client():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cliente = request.args.get('cliente')
    detalle = request.args.get('detalle') == 'si'

    if not start_date or not end_date:
        return redirect(url_for('main.reports'))

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

    query = Sale.query.filter(Sale.date >= start, Sale.date < end)

    if cliente:
        query = query.join(Sale.customer).filter(
            (Customer.name.ilike(f"%{cliente}%")) | (Customer.ruc.ilike(f"%{cliente}%"))
        )

    sales = query.all()

    return render_pdf_template('reportes/ventas_cliente_pdf.html', sales=sales, start=start, end=end, detalle=detalle, user=current_user)

# --- Stock Bajo: Productos con stock_current <= stock_min ---
@main_bp.route('/reports/inventory/low-stock', methods=['GET'])
@login_required
def reports_inventory_low_stock():
    productos_bajo_stock = Product.query.filter(Product.stock_current <= Product.stock_min).order_by(Product.stock_current.asc()).all()
    return render_pdf_template(
        'reports/pdf/low_stock_pdf.html',
        productos=productos_bajo_stock,
        fecha_generacion=datetime.now(),
        user=current_user
    )

# --- Inventario por Categoría: Listado de productos por categoría ---
@main_bp.route('/reports/inventory/by-category', methods=['GET'])
@login_required
def reports_inventory_by_category():
    categorias = Category.query.filter(Category.is_active==True).order_by(Category.name).all()
    return render_pdf_template(
        'reports/pdf/inventory_by_category_pdf.html',
        categorias=categorias,
        fecha_generacion=datetime.now(),
        user=current_user
    )

# --- Valorización de Stock: Valor total del inventario actual ---
@main_bp.route('/reports/inventory/stock-valuation', methods=['GET'])
@login_required
def reports_inventory_stock_valuation():
    # Calcular el valor total: sum(stock_current * sale_price) para todos los productos activos
    total_valor = db.session.query(
        func.sum(Product.stock_current * Product.sale_price)
    ).filter(Product.is_active==True).scalar() or 0

    productos = Product.query.filter(Product.is_active==True).order_by(Product.name).all()

    return render_pdf_template(
        'reports/pdf/stock_valuation_pdf.html',
        productos=productos,
        total_valor=total_valor,
        fecha_generacion=datetime.now(),
        user=current_user
    )

# Mostrar página principal de reportes financieros
@main_bp.route('/reports/financial')
@login_required
def reports_financial():
    return render_template('reports/financial.html')

# --- Flujo de caja PDF ---
@main_bp.route('/reports/financial/cash_flow', methods=['POST'])
@login_required
def reports_financial_cash_flow():
    # Leer fechas del formulario
    fecha_desde = request.form.get('fecha_desde')
    fecha_hasta = request.form.get('fecha_hasta')
    try:
        dt_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
        dt_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
    except:
        return "Formato de fecha inválido", 400

    # Consultar ingresos y egresos en el rango
    ingresos = db.session.query(func.coalesce(func.sum(CashMovement.amount), 0))\
        .filter(CashMovement.type == 'ingreso')\
        .filter(and_(CashMovement.movement_date >= dt_desde, CashMovement.movement_date <= dt_hasta)).scalar()

    egresos = db.session.query(func.coalesce(func.sum(CashMovement.amount), 0))\
        .filter(CashMovement.type == 'egreso')\
        .filter(and_(CashMovement.movement_date >= dt_desde, CashMovement.movement_date <= dt_hasta)).scalar()

    balance = ingresos - egresos

    # Generar PDF con plantilla (usar tu método preferido)
    rendered = render_template('reports/pdf/cash_flow_pdf.html', ingresos=ingresos, egresos=egresos, balance=balance,
                               fecha_desde=dt_desde, fecha_hasta=dt_hasta)

    # Aquí usá pdfkit o wkhtmltopdf para generar el PDF (ejemplo):
    import pdfkit
    pdf = pdfkit.from_string(rendered, False)

    return send_file(BytesIO(pdf), mimetype='application/pdf', download_name='flujo_de_caja.pdf')


# --- Rentabilidad PDF ---
@main_bp.route('/reports/financial/profitability', methods=['POST'])
@login_required
def reports_financial_profitability():
    fecha_desde = request.form.get('fecha_desde')
    fecha_hasta = request.form.get('fecha_hasta')
    try:
        dt_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
        dt_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
    except:
        return "Formato de fecha inválido", 400

    # Ejemplo básico: sumar ventas y compras para calcular margen bruto (simplificado)
    ventas = db.session.query(func.coalesce(func.sum(Sale.total), 0))\
        .filter(and_(Sale.sale_date >= dt_desde, Sale.sale_date <= dt_hasta)).scalar()

    compras = db.session.query(func.coalesce(func.sum(Purchase.total), 0))\
        .filter(and_(Purchase.purchase_date >= dt_desde, Purchase.purchase_date <= dt_hasta)).scalar()

    margen_bruto = ventas - compras
    margen_porcentaje = (margen_bruto / ventas * 100) if ventas > 0 else 0

    rendered = render_template('reports/pdf/profitability_pdf.html', ventas=ventas, compras=compras,
                               margen_bruto=margen_bruto, margen_porcentaje=margen_porcentaje,
                               fecha_desde=dt_desde, fecha_hasta=dt_hasta)

    import pdfkit
    pdf = pdfkit.from_string(rendered, False)

    return send_file(BytesIO(pdf), mimetype='application/pdf', download_name='rentabilidad.pdf')


# --- Compras por Proveedor PDF ---
@main_bp.route('/reports/financial/purchases_by_supplier', methods=['POST'])
@login_required
def reports_financial_purchases_by_supplier():
    supplier_id = request.form.get('supplier_id')
    include_all = request.form.get('include_all') == 'true'

    # Si include_all, traemos todas las compras con sus proveedores
    if include_all:
        compras = db.session.query(Purchase, Supplier).join(Supplier).all()
        # compras es lista de tuplas (Purchase, Supplier)
        # Vamos a agrupar o pasar directo a plantilla
        rendered = render_template('reports/pdf/purchases_by_supplier_pdf.html',
                                   compras=compras, supplier=None, include_all=True)
    else:
        # Por proveedor específico
        if not supplier_id:
            return "Proveedor no especificado", 400
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return "Proveedor no encontrado", 404

        compras = Purchase.query.filter(Purchase.supplier_id == supplier_id).all()

        rendered = render_template('reports/pdf/purchases_by_supplier_pdf.html',
                                   compras=compras, supplier=supplier, include_all=False)

    import pdfkit
    pdf = pdfkit.from_string(rendered, False)

    return send_file(BytesIO(pdf), mimetype='application/pdf', download_name='compras_por_proveedor.pdf')

@main_bp.route('/reports/financial')
@login_required
def reports_financial2():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('reports/financial.html', suppliers=suppliers)


#-----------RG90---------------------
def validar_periodo(periodo):
    import re
    return bool(periodo and re.match(r'^\d{6}$', periodo))

# ----------- Ventas RG90 -----------
@main_bp.route('/rg90/ventas', methods=['POST'])
@login_required
def rg90_ventas_ajax():
    periodo = request.form.get('periodo')
    if not validar_periodo(periodo):
        return jsonify({"ok": False, "errores": ["Período inválido, debe ser MMYYYY"]})

    try:
        ruta_zip = generar_archivo_rg90_ventas(periodo=periodo)
        ruta_csv = ruta_zip.replace('.zip', '.csv')

        errores = []
        if not os.path.exists(ruta_csv):
            return jsonify({"ok": False, "errores": ["Archivo CSV no encontrado después de generar."]})

        with open(ruta_csv, encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            for i, linea in enumerate(reader, start=1):
                errores.extend(validar_lineav(linea, i))

        if errores:
            return jsonify({"ok": False, "errores": errores})

        nombre_zip = os.path.basename(ruta_zip)
        return jsonify({"ok": True, "archivo": nombre_zip})

    except Exception as e:
        return jsonify({"ok": False, "errores": [str(e)]})

# ----------- Compras RG90 -----------
@main_bp.route('/rg90/compras', methods=['POST'])
@login_required
def rg90_compras_ajax():
    periodo = request.form.get('periodo')
    if not validar_periodo(periodo):
        return jsonify({"ok": False, "errores": ["Período inválido, debe ser MMYYYY"]})

    try:
        ruta_zip = generar_archivo_rg90_compras(periodo=periodo)
        ruta_csv = ruta_zip.replace('.zip', '.csv')

        errores = []
        if not os.path.exists(ruta_csv):
            return jsonify({"ok": False, "errores": ["Archivo CSV no encontrado después de generar."]})

        with open(ruta_csv, encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            for i, linea in enumerate(reader, start=1):
                errores.extend(validar_linea(linea, i))

        if errores:
            return jsonify({"ok": False, "errores": errores})

        nombre_zip = os.path.basename(ruta_zip)
        return jsonify({"ok": True, "archivo": nombre_zip})

    except Exception as e:
        return jsonify({"ok": False, "errores": [str(e)]})

# ----------- Descargar ZIP -----------

@main_bp.route('/rg90/download/<filename>')
@login_required
def rg90_download(filename):
    carpeta = os.path.join(current_app.root_path, 'static', 'rg90')
    ruta_archivo = os.path.join(carpeta, filename)

    if not os.path.exists(ruta_archivo):
        return "Archivo no encontrado", 404

    return send_from_directory(carpeta, filename, as_attachment=True)


#------------Users-------------------
@main_bp.route('/admin/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_users_edit(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role_id = form.role_id.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('main.admin_users'))
    return render_template('admin/user_form.html', form=form, title='Editar Usuario')

@main_bp.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
def admin_users_new():
    form = UserForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role_id=form.role_id.data,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('main.admin_users'))
    return render_template('admin/user_form.html', form=form, title='Nuevo Usuario')
