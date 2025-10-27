import sys
import sqlite3
from sqlite3 import Error
import datetime
from tabulate import tabulate
import random
import pandas as pd

DB_FILE = "coworking.db"

def inicializar_bd() -> None:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS CLIENTES (
                            clave INTEGER PRIMARY KEY AUTOINCREMENT,
                            nombre TEXT NOT NULL,
                            apellidos TEXT NOT NULL)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS SALAS (
                            clave_s INTEGER PRIMARY KEY AUTOINCREMENT,
                            nombre_sala TEXT NOT NULL,
                            cupo INTEGER NOT NULL)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS RESERVACIONES (
                            folio INTEGER PRIMARY KEY AUTOINCREMENT,
                            clave INTEGER,
                            clave_s INTEGER,
                            fecha TEXT,
                            turno TEXT NOT NULL,
                            evento TEXT NOT NULL,
                            FOREIGN KEY (clave) REFERENCES CLIENTES(clave),
                            FOREIGN KEY (clave_s) REFERENCES SALAS(clave_s))""")
            conn.commit()
    except Error as e:
        print("Error al inicializar la base de datos:", e)
        sys.exit(1)

def mostrar_tabla(datos: list, encabezado: list) -> None:
    if datos:
        print(tabulate(datos, headers=encabezado, tablefmt="grid"))
    else:
        print("No hay datos para mostrar.")

def leer_clientes() -> list:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT clave, apellidos, nombre FROM CLIENTES ORDER BY apellidos, nombre")
    filas = cur.fetchall()
    conn.close()
    return filas

def registrar_cliente() -> None:
    nombre = input("Ingrese el nombre del cliente: ").strip()
    apellidos = input("Ingrese los apellidos del cliente: ").strip()
    if not nombre or not apellidos:
        print("Debe ingresar nombre y apellidos.")
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO CLIENTES (nombre, apellidos) VALUES (?, ?)", (nombre, apellidos))
    conn.commit()
    conn.close()
    print("Cliente registrado correctamente.")

def registrar_sala() -> None:
    nombre_sala = input("Ingrese el nombre de la sala: ").strip()
    if not nombre_sala:
        print("Debe ingresar un nombre de sala.")
        return
    try:
        cupo = int(input("Ingrese el cupo máximo de la sala: ").strip())
        if cupo <= 0:
            print("El cupo debe ser mayor a 0.")
            return
    except ValueError:
        print("Cupo inválido.")
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO SALAS (nombre_sala, cupo) VALUES (?, ?)", (nombre_sala, cupo))
    conn.commit()
    conn.close()
    print("Sala registrada correctamente.")

def fecha_input_valida() -> str:
    while True:
        s = input("Ingrese la fecha de reservación (mm-dd-aaaa): ").strip()
        try:
            fecha = datetime.datetime.strptime(s, "%m-%d-%Y")
        except ValueError:
            print("Formato inválido. Use mm-dd-aaaa.")
            continue
        if fecha.weekday() == 6:
            lunes = fecha + datetime.timedelta(days=1)
            propuesta = lunes.strftime("%m-%d-%Y")
            print("No se permiten reservaciones en domingo.")
            aceptar = input(f"¿Desea usar el lunes siguiente {propuesta}? (s/n): ").strip().lower()
            if aceptar == "s":
                fecha = lunes
            else:
                continue
        hoy = datetime.datetime.now()
        if fecha <= hoy + datetime.timedelta(days=2):
            print("La fecha debe ser al menos dos días después de hoy.")
            continue
        return fecha.strftime("%m-%d-%Y")

def generar_folio_unico(cur: sqlite3.Cursor) -> int:
    while True:
        folio = random.randint(1000, 9999)
        cur.execute("SELECT 1 FROM RESERVACIONES WHERE folio = ?", (folio,))
        if not cur.fetchone():
            return folio

def listar_salas_disponibles(fecha: str) -> list:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT clave_s, nombre_sala, cupo FROM SALAS")
    salas = cur.fetchall()
    disponibles = []
    for clave_s, nombre_sala, cupo in salas:
        cur.execute("SELECT turno FROM RESERVACIONES WHERE clave_s = ? AND fecha = ?", (clave_s, fecha))
        ocupadas = [r[0] for r in cur.fetchall()]
        turnos = [t for t in ["Matutino", "Vespertino", "Nocturno"] if t not in ocupadas]
        if turnos:
            disponibles.append((clave_s, nombre_sala, cupo, ", ".join(turnos)))
    conn.close()
    return disponibles

def registrar_reservacion() -> None:
    clientes = leer_clientes()
    if not clientes:
        print("No hay clientes registrados. Registre un cliente primero.")
        return
    mostrar_tabla(clientes, ["Clave", "Apellidos", "Nombre"])
    while True:
        entrada = input("Ingrese la clave del cliente o 'C' para cancelar: ").strip()
        if entrada.upper() == "C":
            return
        try:
            clave = int(entrada)
        except ValueError:
            print("Clave inválida.")
            continue
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT clave FROM CLIENTES WHERE clave = ?", (clave,))
        if not cur.fetchone():
            conn.close()
            print("Clave no encontrada.")
            continue
        break
    fecha = fecha_input_valida()
    disponibles = listar_salas_disponibles(fecha)
    if not disponibles:
        print("No hay salas disponibles en esa fecha.")
        return
    mostrar_tabla(disponibles, ["Clave", "Sala", "Cupo", "Turnos disponibles"])
    while True:
        try:
            clave_s = int(input("Seleccione la clave de la sala: ").strip())
            if not any(clave_s == s[0] for s in disponibles):
                print("Sala inválida.")
                continue
            break
        except ValueError:
            print("Clave inválida.")
    for item in disponibles:
        if item[0] == clave_s:
            turnos = [t.strip() for t in item[3].split(",")]
            break
    while True:
        turno = input("Seleccione turno (Matutino, Vespertino, Nocturno): ").strip().capitalize()
        if turno not in turnos:
            print("Turno no disponible.")
            continue
        break
    evento = input("Ingrese el nombre del evento: ").strip()
    if not evento:
        print("El nombre del evento no puede estar vacío.")
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    folio = generar_folio_unico(cur)
    cur.execute("""INSERT INTO RESERVACIONES (folio, clave, clave_s, fecha, turno, evento)
                   VALUES (?, ?, ?, ?, ?, ?)""", (folio, clave, clave_s, fecha, turno, evento))
    conn.commit()
    conn.close()
    print(f"Reservación registrada con folio: {folio}")

def consultar_reservaciones() -> None:
    s = input("Ingrese la fecha (mm-dd-aaaa) o Enter para hoy: ").strip()
    if not s:
        fecha = datetime.datetime.now().strftime("%m-%d-%Y")
    else:
        try:
            datetime.datetime.strptime(s, "%m-%d-%Y")
            fecha = s
        except ValueError:
            print("Formato inválido.")
            return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""SELECT R.folio, C.nombre || ' ' || C.apellidos, S.nombre_sala, R.turno, R.evento
                   FROM RESERVACIONES R
                   JOIN CLIENTES C ON R.clave = C.clave
                   JOIN SALAS S ON R.clave_s = S.clave_s
                   WHERE R.fecha = ?
                   ORDER BY R.folio""", (fecha,))
    registros = cur.fetchall()
    conn.close()
    if not registros:
        print("No hay reservaciones en esa fecha.")
        return
    mostrar_tabla(registros, ["Folio", "Cliente", "Sala", "Turno", "Evento"])
    exportar = input("¿Desea exportar el reporte? (s/n): ").strip().lower()
    if exportar != "s":
        return
    print("Formatos disponibles:\n1. CSV\n2. JSON\n3. Excel")
    opcion = input("Seleccione formato: ").strip()
    df = pd.DataFrame(registros, columns=["Folio", "Cliente", "Sala", "Turno", "Evento"])
    nombre_archivo = f"reservaciones_{fecha.replace('-', '')}"
    if opcion == "1":
        df.to_csv(nombre_archivo + ".csv", index=False)
        print("Exportado a CSV.")
    elif opcion == "2":
        df.to_json(nombre_archivo + ".json", orient="records", indent=4)
        print("Exportado a JSON.")
    elif opcion == "3":
        df.to_excel(nombre_archivo + ".xlsx", index=False)
        print("Exportado a Excel.")
    else:
        print("Opción inválida.")

def editar_evento() -> None:
    fi = input("Ingrese la fecha inicial (mm-dd-aaaa): ").strip()
    ff = input("Ingrese la fecha final (mm-dd-aaaa): ").strip()
    try:
        datetime.datetime.strptime(fi, "%m-%d-%Y")
        datetime.datetime.strptime(ff, "%m-%d-%Y")
    except ValueError:
        print("Formato inválido.")
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""SELECT folio, fecha, evento FROM RESERVACIONES
                   WHERE fecha BETWEEN ? AND ?
                   ORDER BY fecha, folio""", (fi, ff))
    reservas = cur.fetchall()
    if not reservas:
        print("No hay reservaciones en ese rango.")
        conn.close()
        return
    mostrar_tabla(reservas, ["Folio", "Fecha", "Evento"])
    while True:
        entrada = input("Ingrese el folio a editar o 'C' para cancelar: ").strip()
        if entrada.upper() == "C":
            conn.close()
            return
        try:
            folio = int(entrada)
        except ValueError:
            print("Folio inválido.")
            continue
        if folio not in [r[0] for r in reservas]:
            print("Folio fuera del rango.")
            continue
        break
    nuevo = input("Ingrese el nuevo nombre del evento: ").strip()
    if not nuevo:
        print("El nombre no puede estar vacío.")
        conn.close()
        return
    cur.execute("UPDATE RESERVACIONES SET evento = ? WHERE folio = ?", (nuevo, folio))
    conn.commit()
    conn.close()
    print("Evento actualizado correctamente.")

def confirmar_salida() -> bool:
    return input("¿Confirma que desea salir? (s/n): ").strip().lower() == "s"

def menu() -> None:
    inicializar_bd()
    while True:
        print("""
==============================
 SISTEMA DE RESERVAS COWORKING
==============================
1. Registrar una reservación
2. Editar nombre de evento
3. Consultar reservaciones
4. Registrar cliente
5. Registrar sala
6. Salir
""")
        try:
            op = int(input("Seleccione una opción: ").strip())
        except ValueError:
            print("Opción inválida.")
            continue
        if op == 1:
            registrar_reservacion()
        elif op == 2:
            editar_evento()
        elif op == 3:
            consultar_reservaciones()
        elif op == 4:
            registrar_cliente()
        elif op == 5:
            registrar_sala()
        elif op == 6:
            if confirmar_salida():
                print("Saliendo del sistema.")
                break
        else:
            print("Opción no válida.")

if __name__ == "__main__":
    menu()