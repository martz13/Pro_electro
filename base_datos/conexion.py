import sqlite3
import os
import sys
import platform
import bcrypt
import json
from datetime import datetime
import threading
import requests
from PySide6.QtCore import QThread, Signal

# ==========================================
# 1. RUTAS INTELIGENTES PARA EVITAR PÉRDIDA DE DATOS
# ==========================================
sistema = platform.system()

# A) Ruta persistente para la Base de Datos (Sobrevive al cerrar el .exe)
if sistema == "Windows":
    # C:\Users\NombreUsuario\AppData\Roaming\ProElectro
    app_data = os.getenv('APPDATA')
    DB_DIR = os.path.join(app_data, 'ProElectro')
else:
    # Para Linux / Mac
    DB_DIR = os.path.expanduser('~/.pro_electro')

# Creamos la carpeta si no existe
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_PATH = os.path.join(DB_DIR, "pro_electro.db")

# B) Ruta para el archivo SQL.sql (Para crear las tablas la primera vez)
if getattr(sys, 'frozen', False):
    # Si estamos corriendo desde el .exe, los archivos están en la carpeta temporal _MEIPASS
    BASE_DIR_APP = sys._MEIPASS
else:
    # Si estamos en Visual Studio Code (.py)
    BASE_DIR_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUTA_SQL_ORIGINAL = os.path.join(BASE_DIR_APP, "base_datos", "SQL.sql")

# ==========================================
# 2. FUNCIONES DE SINCRONIZACIÓN Y BD
# ==========================================

def operacion_crud_nube(tabla, operacion, datos_dict=None, registro_id=None):
    """
    Ejecuta una operación ONLINE-FIRST. 
    Retorna (True, nuevo_id_de_la_nube) si funciona, o (False, mensaje_error) si falla.
    """
    URL_API = "https://api-pro-electro.pro-electro.workers.dev/api/crud"
    payload = {
        "tabla": tabla,
        "operacion": operacion,
        "id": registro_id,
        "datos": datos_dict or {}
    }
    try:
        resp = requests.post(URL_API, json=payload, timeout=5)
        
        # Intentamos leer la respuesta de la nube SIEMPRE, para capturar el error real
        try:
            data = resp.json()
            if resp.status_code == 200 and data.get("success"):
                return True, data.get("id")
            else:
                # Aquí capturamos el mensaje real de D1 (Ej: "FOREIGN KEY constraint failed")
                return False, data.get("error", "Error desconocido en el servidor")
        except ValueError:
            # Solo entra aquí si la nube se cae por completo y manda texto raro
            return False, f"Error HTTP del servidor: {resp.status_code}. Respuesta cruda: {resp.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Error de red: {str(e)}"

def obtener_conexion():
    """Devuelve una conexión a la base de datos SQLite persistente."""
    return sqlite3.connect(DB_PATH)

def inicializar_bd():
    """Crea la base de datos a partir del archivo SQL y agrega un usuario de prueba."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # 1. Crear las tablas a partir del archivo SQL.sql si existe
    if os.path.exists(RUTA_SQL_ORIGINAL):
        with open(RUTA_SQL_ORIGINAL, 'r', encoding='utf-8') as archivo_sql:
            script_sql = archivo_sql.read()
            cursor.executescript(script_sql)
    else:
        print(f"Advertencia: No se encontró el archivo {RUTA_SQL_ORIGINAL}.")

    # 2. MIGRACIONES - Agregar columnas nuevas a tablas existentes (protege la BD de Edwin)
    # Si la columna ya existe, SQLite lanza error que ignoramos con try/except
    migraciones = [
        ("inventario", "clave_sat_producto", "TEXT"),
        ("catalogo_um", "clave_sat_unidad", "TEXT"),
        ("datos_fiscales", "facturacion_todos_usuarios", "INTEGER DEFAULT 0"),
        ("datos_fiscales", "regimen_fiscal", "TEXT"),
        ("datos_fiscales", "cp_fiscal", "TEXT"),
        # Campos fiscales del timbre para PDF personalizado y QR
        ("facturas", "cert_numero", "TEXT"),
        ("facturas", "sello_cfdi", "TEXT"),
        ("facturas", "sello_sat", "TEXT"),
        ("facturas", "cert_sat_numero", "TEXT"),
        ("facturas", "rfc_pac", "TEXT"),
        ("facturas", "cadena_original", "TEXT"),
        ("facturas", "forma_pago", "TEXT"),
        ("facturas", "metodo_pago", "TEXT"),
    ]
    
    for tabla, columna, tipo in migraciones:
        try:
            cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
            print(f"✅ Migración aplicada: {tabla}.{columna}")
        except sqlite3.OperationalError:
            pass  # La columna ya existe, no pasa nada

    # 3. Insertar usuario de prueba (si no existe previamente)
    cursor.execute("SELECT id FROM usuarios WHERE correo = ?", ("admin@proelectro.mx",))
    usuario_existente = cursor.fetchone()
    
    if not usuario_existente:
        password_plana = "admin123".encode('utf-8')
        password_hash = bcrypt.hashpw(password_plana, bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute(
            "INSERT INTO usuarios (nombre_completo, correo, password, rol) VALUES (?, ?, ?, ?)",
            ("Edwin Guerrero", "admin@proelectro.mx", password_hash, "Super admin")
        )
        print("✅ Usuario local de emergencia creado: admin@proelectro.mx")

    conexion.commit()
    conexion.close()

# ==========================================
# 3. HILOS Y LÓGICA DE SINCRONIZACIÓN VISUAL
# ==========================================
class SyncThread(QThread):
    """Hilo en segundo plano para sincronizar sin congelar la pantalla"""
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def run(self):
        exito, msj = sincronizar_datos_nube(lambda val, txt: self.progress.emit(val, txt))
        self.finished.emit(exito, msj)

def forzar_descarga_nube():
    """Mantenemos esta función por compatibilidad con la Regla 2 (Colisiones) en las demás vistas"""
    sincronizar_datos_nube()

def sincronizar_datos_nube(progress_callback=None):
    """Descarga e inyecta la BD calculando el progreso del 0 al 100%."""
    def emit(val, text):
        if progress_callback:
            progress_callback(val, text)
    
    try:
        emit(5, "Verificando conexión a internet...")
        requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
    except:
        return False, "Sin conexión a internet. Trabajando en modo local."

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        
        # 1. Subir cotizaciones offline
        emit(15, "Sincronizando cotizaciones offline...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cotizaciones_ext'")
        if cursor.fetchone():
            cursor.execute("SELECT * FROM cotizaciones_ext")
            cotizaciones_ext = cursor.fetchall()
            
            if cotizaciones_ext:
                emit(25, "Subiendo cotizaciones pendientes...")
                payload = {"cotizaciones": []}
                for cot in cotizaciones_ext:
                    c_id, folio, fecha, cli_id, vend, oc, obra, estado, monto = cot
                    cursor.execute("SELECT * FROM cotizaciones_detalle_ext WHERE cotizacion_id=?", (c_id,))
                    detalles_ext = cursor.fetchall()
                    
                    lista_detalles = []
                    for det in detalles_ext:
                        lista_detalles.append({
                            "codigo_producto": det[2], "descripcion": det[3], "cantidad": det[4],
                            "um": det[5], "precio_unitario": det[6], "monto": det[7], "disponibilidad": det[8]
                        })
                        
                    payload["cotizaciones"].append({
                        "folio": folio, "fecha": fecha, "cliente_id": cli_id, "vendedor": vend,
                        "oc": oc, "obra": obra, "estado": estado, "monto_total": monto,
                        "detalles": lista_detalles
                    })

                URL_SUBIR_EXT = "https://api-pro-electro.pro-electro.workers.dev/api/subir_cotizaciones_ext"
                resp = requests.post(URL_SUBIR_EXT, json=payload, timeout=15)
                
                if resp.status_code == 200 and resp.json().get("success"):
                    cursor.execute("DELETE FROM cotizaciones_detalle_ext")
                    cursor.execute("DELETE FROM cotizaciones_ext")
                    conexion.commit()
        
        # 2. Descargar BD
        emit(45, "Descargando base de datos actualizada...")
        URL_API_PULL = "https://api-pro-electro.pro-electro.workers.dev/api/descargar_todo"
        respuesta = requests.get(URL_API_PULL, timeout=20)
        
        if respuesta.status_code == 200 and respuesta.json().get("success"):
            data = respuesta.json()["data"]
            
            emit(60, "Limpiando registros locales antiguos...")
            cursor.execute("PRAGMA foreign_keys = OFF;")
            
            cursor.execute("DELETE FROM facturas")
            cursor.execute("DELETE FROM historial_compras")
            cursor.execute("DELETE FROM ordenes_compra_detalle")
            cursor.execute("DELETE FROM ordenes_compra")
            cursor.execute("DELETE FROM cotizaciones_detalle")
            cursor.execute("DELETE FROM cotizaciones")
            cursor.execute("DELETE FROM inventario")
            cursor.execute("DELETE FROM proveedores")
            cursor.execute("DELETE FROM clientes")
            cursor.execute("DELETE FROM usuarios")
            cursor.execute("DELETE FROM catalogo_um")
            cursor.execute("DELETE FROM datos_fiscales")
            
            def insertar_lote(tabla, registros):
                if not registros: return
                columnas = ", ".join(registros[0].keys())
                placeholders = ", ".join(["?"] * len(registros[0]))
                query = f"INSERT OR REPLACE INTO {tabla} ({columnas}) VALUES ({placeholders})"
                valores = [tuple(r.values()) for r in registros]
                cursor.executemany(query, valores)
            
            # Insertar en orden lógico
            tablas = ["usuarios", "clientes", "proveedores", "inventario", "historial_compras", "cotizaciones", "cotizaciones_detalle", "ordenes_compra", "ordenes_compra_detalle", "catalogo_um", "datos_fiscales", "facturas"]
            for i, t in enumerate(tablas):
                progreso = 60 + int(((i+1)/len(tablas)) * 35) # Matemática de 60% a 95%
                emit(progreso, f"Instalando tabla: {t}...")
                insertar_lote(t, data.get(t, []))
            
            cursor.execute("PRAGMA foreign_keys = ON;")
            conexion.commit()
            emit(100, "¡Base de datos lista!")
            return True, "Sincronización completada exitosamente."
        else:
            return False, "Error en la respuesta del servidor."
            
    except Exception as e:
        return False, f"Error durante la sincronización:\n{str(e)}"
    finally:
        conexion.close()   
        