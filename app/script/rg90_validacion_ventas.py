# rg90_validacion_ventas.py
import csv
import re
from datetime import datetime

def validar_fecha(fecha_str):
    try:
        datetime.strptime(fecha_str, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def validar_lineav(linea, numero_linea):
    errores = []
    linea = [col.strip() for col in linea]

    if len(linea) < 18:
        errores.append(f"Línea {numero_linea}: cantidad de columnas insuficientes (esperadas al menos 18, encontradas {len(linea)})")
        return errores
    
    linea = linea[:18]

    if linea[0] != '1':
        errores.append(f"Línea {numero_linea}: columna 1 debe ser '1', encontrado '{linea[0]}'")

    if linea[1] != '109':
        errores.append(f"Línea {numero_linea}: columna 2 debe ser '109', encontrado '{linea[1]}'")

    if not validar_fecha(linea[2]):
        errores.append(f"Línea {numero_linea}: columna 3 fecha inválida '{linea[2]}'")

    for i in [7, 8, 9]:
        valor_str = linea[i]
        try:
            valor = int(valor_str)
            if valor < 0:
                errores.append(f"Línea {numero_linea}: columna {i+1} monto negativo '{valor_str}'")
        except ValueError:
            errores.append(f"Línea {numero_linea}: columna {i+1} no es entero válido '{valor_str}'")

    try:
        gravadas = int(linea[7])
        exentas = int(linea[8])
        total = int(linea[9])
        if gravadas + exentas != total:
            errores.append(f"Línea {numero_linea}: suma de gravadas ({gravadas}) + exentas ({exentas}) != total ({total})")
    except ValueError:
        errores.append(f"Línea {numero_linea}: error en valores numéricos de montos para validar suma")

    for i in range(14):
        if linea[i] == "":
            errores.append(f"Línea {numero_linea}: columna {i+1} está vacía")

    ruc = linea[5]
    if not re.fullmatch(r"\d{7,14}", ruc):
        errores.append(f"Línea {numero_linea}: RUC/Documento '{ruc}' no válido (debe tener 7-14 dígitos numéricos)")

    return errores

def validar_archivo(ruta_archivo):
    errores_totales = []
    try:
        with open(ruta_archivo, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            for i, linea in enumerate(reader, start=1):
                errores_linea = validar_lineav(linea, i)
                errores_totales.extend(errores_linea)
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el archivo: {ruta_archivo}")
        return False, []
    except Exception as e:
        print(f"❌ ERROR inesperado al leer el archivo: {e}")
        return False, []

    if errores_totales:
        print("Se encontraron errores en el archivo RG90 de ventas:")
        for error in errores_totales:
            print(" -", error)
        return False, errores_totales
    else:
        print("✅ Archivo RG90 de ventas validado correctamente, sin errores.")
        return True, []

