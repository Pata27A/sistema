import pdfkit

def render_pdf_from_template(html):
    options = {
        'enable-local-file-access': '',
        'encoding': "UTF-8",
        'page-size': 'A4',
        'margin-top': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'margin-right': '10mm',
    }
    return pdfkit.from_string(html, False, options=options)
