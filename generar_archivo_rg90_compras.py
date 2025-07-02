def generar_archivo_rg90_compras(periodo="062025", carpeta_salida=None):
    from flask import current_app
    import os
    import csv
    from zipfile import ZipFile
    from app.models import Purchase, Supplier, Empresa
    from app.script.rg90_validacion_compras import validar_archivo
    from app import db

    if carpeta_salida is None:
        carpeta_salida = os.path.join(current_app.root_path, 'static', 'rg90')
    os.makedirs(carpeta_salida, exist_ok=True)

    empresa = Empresa.query.first()
    if not empresa:
        raise Exception("No se encontró información de la empresa.")

    ruc = empresa.ruc.replace("-", "")
    nombre_archivo = f"{ruc}_REGC_{periodo}_V0001.csv"
    ruta_archivo = os.path.join(carpeta_salida, nombre_archivo)

    mes = int(periodo[:2])
    anho = int(periodo[2:])

    with open(ruta_archivo, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        compras = Purchase.query.filter(
            db.extract('month', Purchase.purchase_date) == mes,
            db.extract('year', Purchase.purchase_date) == anho
        ).all()

        for compra in compras:
            supplier = compra.supplier
            ruc_proveedor = (supplier.ruc or "").replace("-", "") if supplier else "0000000"

            gravada_10 = int(round(float(compra.iva_10 or 0)))
            gravada_5 = int(round(float(compra.iva_5 or 0)))
            exenta = 0  # Ajustar si tienes campo exentas
            total = gravada_10 + gravada_5 + exenta

            writer.writerow([
                1,
                109,
                compra.purchase_date.strftime("%d/%m/%Y"),
                compra.invoice_number,
                "11",
                ruc_proveedor,
                supplier.name if supplier else "Proveedor Desconocido",
                gravada_10,
                gravada_5,
                exenta,
                total,
                "S",
                "N",
                "N",
                "N",
                "", "", "", ""
            ])

    # Validar antes de crear ZIP
    validacion_ok = validar_archivo(ruta_archivo)

    if not validacion_ok:
        print("❌ El archivo de compras RG90 tuvo errores de validación. No se generó el ZIP.")
        os.remove(ruta_archivo)  # Borra el CSV si es inválido
        return None

    # Crear ZIP
    nombre_zip = nombre_archivo.replace(".csv", ".zip")
    ruta_zip = os.path.join(carpeta_salida, nombre_zip)
    with ZipFile(ruta_zip, 'w') as zipf:
        zipf.write(ruta_archivo, arcname=nombre_archivo)

    print("✅ El archivo de compras RG90 es válido.")
    print(f"✅ Archivo ZIP generado correctamente: {ruta_zip}")
    return ruta_zip


# Para ejecutar desde consola con contexto Flask
if __name__ == "__main__":
    from datetime import datetime
    from app import create_app

    app = create_app()
    with app.app_context():
        periodo_actual = datetime.now().strftime("%m%Y")  # ejemplo: "072025"
        print(f"Generando archivo RG90 de compras para el periodo {periodo_actual}...")

        try:
            ruta_zip = generar_archivo_rg90_compras(periodo=periodo_actual)
            if ruta_zip:
                print(f"✅ Archivo ZIP generado en: {ruta_zip}")
            else:
                print("❌ No se generó el archivo ZIP debido a errores en la validación.")
        except Exception as e:
            print(f"❌ Error al generar el archivo: {e}")
