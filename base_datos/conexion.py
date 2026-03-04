import sqlite3
import os
import sys
import platform
import bcrypt
import json
from datetime import datetime
import threading

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
def registrar_en_cola_sync(tabla_afectada, operacion, registro_id, datos_dict=None):
    datos_json = json.dumps(datos_dict, ensure_ascii=False) if datos_dict else None
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            INSERT INTO sync_queue (tabla_afectada, operacion, registro_id, datos_json, fecha_modificacion)
            VALUES (?, ?, ?, ?, ?)
        """, (tabla_afectada, operacion, str(registro_id), datos_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conexion.commit()
        
        # ==========================================
        # DISPARADOR DE SINCRONIZACIÓN INSTANTÁNEA
        # ==========================================
        # Usamos importación local para evitar problemas de referencias circulares
        from utilidades.sincronizador import ejecutar_sincronizacion
        
        # Disparamos el envío a la nube en un hilo separado.
        # Así el usuario no sufre ningún "lag" al guardar.
        hilo_sync = threading.Thread(target=ejecutar_sincronizacion)
        hilo_sync.daemon = True # Si la app se cierra, este hilo muere pacíficamente
        hilo_sync.start()
        
    except Exception as e:
        print(f"Error al registrar en cola de sincronización: {e}")
    finally:
        conexion.close()

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

    # 2. Insertar usuario de prueba (si no existe previamente)
    cursor.execute("SELECT id FROM usuarios WHERE correo = ?", ("admin@proelectro.mx",))
    usuario_existente = cursor.fetchone()
    
    if not usuario_existente:
        # Encriptar la contraseña "admin123"
        password_plana = "admin123".encode('utf-8')
        password_hash = bcrypt.hashpw(password_plana, bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute(
            "INSERT INTO usuarios (nombre_completo, correo, password, rol) VALUES (?, ?, ?, ?)",
            ("Edwin Guerrero", "admin@proelectro.mx", password_hash, "Super admin")
        )
        
        # Obtenemos el ID que SQLite le acaba de asignar
        id_nuevo_usuario = cursor.lastrowid
        
        # --- NUEVO: CREAR DICCIONARIO Y MANDARLO A LA NUBE ---
        datos_usuario = {
            "id": id_nuevo_usuario,
            "nombre_completo": "Edwin Guerrero",
            "correo": "admin@proelectro.mx",
            "password": password_hash,
            "rol": "Super admin"
        }
        
        # Registramos en la cola para que el hilo en segundo plano lo suba a Cloudflare
        registrar_en_cola_sync('usuarios', 'INSERT', id_nuevo_usuario, datos_usuario)
        
        print("✅ Usuario de prueba creado y encolado para la nube: admin@proelectro.mx")

    conexion.commit()
    conexion.close()