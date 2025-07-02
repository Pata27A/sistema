import os
from decimal import ROUND_HALF_UP, Decimal
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from flask import current_app

def validate_ruc(ruc):
    """Validate Paraguay RUC format"""
    if not ruc:
        return False
    
    # Remove dots and hyphens
    clean_ruc = ruc.replace('-', '').replace('.', '')
    
    # Basic format validation
    if len(clean_ruc) < 7 or len(clean_ruc) > 9:
        return False
    
    if not clean_ruc.isdigit():
        return False
    
    return True

def calculate_iva(amount, iva_type):
    """Calcula el IVA incluido desde un monto con IVA"""
    amount = Decimal(str(amount))
    
    if iva_type == '10':
        return (amount / Decimal('11')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    elif iva_type == '5':
        return (amount / Decimal('21')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    else:
        return Decimal('0')

def calculate_sale_totals(details):
    """Calcula totales con IVA incluido en el precio"""
    subtotal = Decimal('0')
    iva_5 = Decimal('0')
    iva_10 = Decimal('0')
    
    for detail in details:
        detail_subtotal = Decimal(str(detail.quantity)) * Decimal(str(detail.unit_price))
        subtotal += detail_subtotal
        
        if detail.iva_type == '5':
            iva_5 += calculate_iva(detail_subtotal, '5')
        elif detail.iva_type == '10':
            iva_10 += calculate_iva(detail_subtotal, '10')
    
    total = subtotal  # ✅ No se suma el IVA, ya está incluido

    return {
        'subtotal': subtotal,
        'iva_5': iva_5,
        'iva_10': iva_10,
        'total': total
    }

def generate_invoice_pdf(sale):
    """Generate PDF invoice for a sale"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    )
    
    # Company header
    story.append(Paragraph("FERRETERÍA - SISTEMA DE GESTIÓN", title_style))
    story.append(Paragraph("RUC: 80000000-1", header_style))
    story.append(Paragraph("Dirección: Asunción, Paraguay", header_style))
    story.append(Spacer(1, 20))
    
    # Invoice details
    story.append(Paragraph(f"FACTURA N°: {sale.invoice_number}", header_style))
    story.append(Paragraph(f"Fecha: {sale.sale_date.strftime('%d/%m/%Y %H:%M')}", header_style))
    
    if sale.customer:
        story.append(Paragraph(f"Cliente: {sale.customer.name}", header_style))
        if sale.customer.ruc:
            story.append(Paragraph(f"RUC Cliente: {sale.customer.ruc}", header_style))
    
    story.append(Spacer(1, 20))
    
    # Products table
    data = [['Código', 'Producto', 'Cant.', 'P. Unit.', 'IVA', 'Subtotal']]
    
    for detail in sale.details:
        data.append([
            detail.product.code,
            detail.product.name[:30],  # Truncate long names
            str(detail.quantity),
            f"₲ {detail.unit_price:,.0f}",
            detail.iva_type + '%' if detail.iva_type != 'exento' else 'Exento',
            f"₲ {detail.subtotal:,.0f}"
        ])
    
    table = Table(data, colWidths=[1*inch, 3*inch, 0.8*inch, 1*inch, 0.8*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Totals
    totals_data = [
        ['Subtotal:', f"₲ {sale.subtotal:,.0f}"],
        ['IVA 5%:', f"₲ {sale.iva_5:,.0f}"],
        ['IVA 10%:', f"₲ {sale.iva_10:,.0f}"],
        ['TOTAL:', f"₲ {sale.total:,.0f}"]
    ]
    
    totals_table = Table(totals_data, colWidths=[2*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black)
    ]))
    
    story.append(totals_table)
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph(f"Método de pago: {sale.payment_method.title()}", styles['Normal']))
    story.append(Paragraph(f"Vendedor: {sale.user.first_name} {sale.user.last_name}", styles['Normal']))
    
    if sale.notes:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Observaciones: {sale.notes}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_rg90_sales_file(sales, month, year):
    """Generate RG90 format file for sales"""
    lines = []
    
    for sale in sales:
        # RG90 format: Type|Date|Invoice|RUC|Amount|IVA|etc
        line = f"V|{sale.sale_date.strftime('%d/%m/%Y')}|{sale.invoice_number}|"
        
        if sale.customer and sale.customer.ruc:
            line += f"{sale.customer.ruc}|"
        else:
            line += "|"
        
        line += f"{sale.subtotal}|{sale.iva_10}|{sale.iva_5}|{sale.total}"
        lines.append(line)
    
    return '\n'.join(lines)

def generate_rg90_purchases_file(purchases, month, year):
    """Generate RG90 format file for purchases"""
    lines = []
    
    for purchase in purchases:
        line = f"C|{purchase.purchase_date.strftime('%d/%m/%Y')}|{purchase.invoice_number}|"
        line += f"{purchase.supplier.ruc}|"
        line += f"{purchase.subtotal}|{purchase.iva_10}|{purchase.iva_5}|{purchase.total}"
        lines.append(line)
    
    return '\n'.join(lines)

def format_currency(amount):
    """Format amount as Paraguayan Guaraní"""
    if amount is None:
        amount = 0
    return f"₲ {amount:,.0f}"

def get_next_invoice_number():
    """Genera el siguiente número de factura con formato 001-001-XXXXXXX"""
    from app.models import Sale
    last_sale = Sale.query.order_by(Sale.id.desc()).first()

    if last_sale and last_sale.invoice_number:
        try:
            # Intentamos extraer la parte numérica final
            parts = last_sale.invoice_number.split('-')
            if len(parts) == 3 and parts[2].isdigit():
                next_number = int(parts[2]) + 1
                return f"{parts[0]}-{parts[1]}-{next_number:07d}"
        except Exception as e:
            print(f"Error al generar número de factura: {e}")

    # Si no hay ventas o algo falló, devolvemos el primer número
    return "001-001-0000001"

