import pdfkit
from flask import render_template, make_response
import os

# Ruta al ejecutable de wkhtmltopdf (ajustar si es necesario)
PDFKIT_CONFIG = pdfkit.configuration(
    wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
)


def render_pdf_template(template_name, **context):
    """
    Renderiza una plantilla HTML como PDF y devuelve un response Flask para descarga.
    """
    html = render_template(template_name, **context)
    pdf = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=report.pdf'

    return response
