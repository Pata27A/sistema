def generar_archivo_rg90_ventas(periodo="062025", carpeta_salida=None):
    from flask import current_app
    import os
    import csv
    from zipfile import ZipFile
    from app.models import Sale, Customer, Empresa
    from app.script.rg90_validacion_ventas import validar_archivo
    from app import db

    if carpeta_salida is None:
        carpeta_salida = os.path.join(current_app.root_path, 'static', 'rg90')
    os.makedirs(carpeta_salida, exist_ok=True)

    empresa = Empresa.query.first()
    if not empresa:
        raise Exception("No se encontró información de la empresa.")

    ruc = empresa.ruc.replace("-", "")
    nombre_archivo = f"{ruc}_REG_{periodo}_V0001.csv"
    ruta_archivo = os.path.join(carpeta_salida, nombre_archivo)

    mes = int(periodo[:2])
    anho = int(periodo[2:])

    def calcular_iva_por_venta(sale):
        gravada_10 = 0
        gravada_5 = 0
        exenta = 0

        for detalle in sale.details:
            producto = detalle.product
            subtotal = float(detalle.subtotal)

            if producto.iva_type == "10":
                neto = subtotal * 10 / 11
                gravada_10 += neto
            elif producto.iva_type == "5":
                neto = subtotal * 20 / 21
                gravada_5 += neto
            else:
                exenta += subtotal

        return {
            "gravada_10": int(round(gravada_10)),
            "gravada_5": int(round(gravada_5)),
            "exenta": int(round(exenta)),
            "total": int(round(gravada_10 + gravada_5 + exenta))
        }

    def formatear_documento(numero):
        """Formatea número como 001-001-0000008"""
        return f"001-001-{str(numero).zfill(7)}"

    with open(ruta_archivo, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        ventas = Sale.query.filter(
            db.extract('month', Sale.sale_date) == mes,
            db.extract('year', Sale.sale_date) == anho
        ).all()

        for venta in ventas:
            customer = venta.customer
            tipo_id = "11" if customer and customer.ruc and len(customer.ruc.replace("-", "")) >= 7 else "12"
            doc = (customer.ruc or "00000000").replace("-", "") if customer else "00000000"
            nombre = customer.name if customer else "Consumidor Final"

            iva_data = calcular_iva_por_venta(venta)

            fila = [
                1,
                109,
                venta.sale_date.strftime("%d/%m/%Y"),
                formatear_documento(venta.document_number),
                tipo_id,
                doc,
                nombre,
                iva_data["gravada_10"] + iva_data["gravada_5"],
                iva_data["exenta"],
                iva_data["total"],
                "S",
                "N",
                "N",
                "N",
                "", "", "", "", ""
            ]
            writer.writerow(fila)

    # Validar archivo generado
    es_valido, errores = validar_archivo(ruta_archivo)

    if es_valido:
        print(f"✅ Archivo RG90 de ventas generado y validado correctamente: {ruta_archivo}")
        # Crear ZIP
        nombre_zip = nombre_archivo.replace(".csv", ".zip")
        ruta_zip = os.path.join(carpeta_salida, nombre_zip)
        with ZipFile(ruta_zip, 'w') as zipf:
            zipf.write(ruta_archivo, arcname=nombre_archivo)
        print(f"✅ Archivo ZIP generado en: {ruta_zip}")
        return ruta_zip
    else:
        print("❌ Errores encontrados en el archivo generado:")
        for err in errores:
            print(f" - {err}")
        raise Exception("El archivo no se generó por errores de validación.")


if __name__ == "__main__":
    from app import app
    with app.app_context():
        from datetime import datetime
        periodo_actual = datetime.now().strftime("%m%Y")
        print(f"Generando archivo RG90 de ventas para el periodo {periodo_actual}...")

        try:
            ruta_zip = generar_archivo_rg90_ventas(periodo=periodo_actual)
            print(f"✅ Archivo generado correctamente: {ruta_zip}")
        except Exception as e:
            print(f"❌ Error al generar el archivo: {e}")
