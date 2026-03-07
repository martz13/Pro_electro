import sqlite3
import os
import sys
import platform
import bcrypt
import json
from datetime import datetime
import threading
import requests

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
        
        id_nuevo_usuario = cursor.lastrowid
        
        datos_usuario = {
            "id": id_nuevo_usuario,
            "nombre_completo": "Edwin Guerrero",
            "correo": "admin@proelectro.mx",
            "password": password_hash,
            "rol": "Super admin"
        }
        
        # --- SOLUCIÓN AL DATABASE LOCKED ---
        # Guardamos y liberamos la tabla usuarios PRIMERO
        conexion.commit()
        
        # AHORA SÍ registramos en la cola (que abre su propia conexión internamente)
#        registrar_en_cola_sync('usuarios', 'INSERT', id_nuevo_usuario, datos_usuario)
        
        print("✅ Usuario de prueba creado y encolado para la nube: admin@proelectro.mx")
    else:
        conexion.commit()

    conexion.close()
    
def realizar_descarga_inicial():
    """Descarga toda la BD de la nube si la instalación local es nueva (inventario vacío)."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Verificamos si la base de datos ya tiene información (usamos inventario como referencia)
        cursor.execute("SELECT COUNT(*) FROM inventario")
        if cursor.fetchone()[0] > 0:
            # Ya hay datos, no necesitamos descargar nada
            return

        print("Iniciando descarga inicial desde la nube...")
        URL_API_PULL = "https://api-pro-electro.pro-electro.workers.dev/api/descargar_todo"
        
        respuesta = requests.get(URL_API_PULL, timeout=15) # Damos más tiempo porque son muchos datos
        
        if respuesta.status_code == 200:
            datos_nube = respuesta.json()
            
            if datos_nube.get("success"):
                data = datos_nube["data"]
                
                # Desactivar temporalmente las llaves foráneas para inserción masiva más rápida
                cursor.execute("PRAGMA foreign_keys = OFF;")
                
                # Función auxiliar para insertar dinámicamente
                def insertar_lote(tabla, registros):
                    if not registros: return
                    columnas = ", ".join(registros[0].keys())
                    placeholders = ", ".join(["?"] * len(registros[0]))
                    query = f"INSERT OR REPLACE INTO {tabla} ({columnas}) VALUES ({placeholders})"
                    
                    # Convertimos la lista de diccionarios en lista de tuplas
                    valores = [tuple(r.values()) for r in registros]
                    cursor.executemany(query, valores)
                
                # Insertamos las tablas (El orden importa lógicamente, aunque PRAGMA esté OFF)
                insertar_lote("usuarios", data.get("usuarios", []))
                insertar_lote("clientes", data.get("clientes", []))
                insertar_lote("proveedores", data.get("proveedores", []))
                insertar_lote("inventario", data.get("inventario", []))
                insertar_lote("cotizaciones", data.get("cotizaciones", []))
                insertar_lote("cotizaciones_detalle", data.get("cotizaciones_detalle", []))
                insertar_lote("catalogo_um", data.get("catalogo_um", []))
                insertar_lote("datos_fiscales", data.get("datos_fiscales", []))
                
                # Reactivamos las llaves foráneas
                cursor.execute("PRAGMA foreign_keys = ON;")
                conexion.commit()
                print("✅ Descarga inicial completada exitosamente. Base de datos sincronizada.")
            else:
                print(f"Error en los datos de la nube: {datos_nube.get('error')}")
                
    except requests.exceptions.RequestException as e:
        print(f"⚠️ No hay internet para la descarga inicial. El sistema iniciará vacío. Detalle: {e}")
    except Exception as e:
        print(f"❌ Error durante la descarga inicial: {str(e)}")
    finally:
        conexion.close()
        
def forzar_descarga_nube():
    """Descarga e inyecta la BD de la nube sobreescribiendo los datos locales viejos."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        URL_API_PULL = "https://api-pro-electro.pro-electro.workers.dev/api/descargar_todo"
        respuesta = requests.get(URL_API_PULL, timeout=10)
        
        if respuesta.status_code == 200 and respuesta.json().get("success"):
            data = respuesta.json()["data"]
            cursor.execute("PRAGMA foreign_keys = OFF;")
            
            def insertar_lote(tabla, registros):
                if not registros: return
                columnas = ", ".join(registros[0].keys())
                placeholders = ", ".join(["?"] * len(registros[0]))
                query = f"INSERT OR REPLACE INTO {tabla} ({columnas}) VALUES ({placeholders})"
                valores = [tuple(r.values()) for r in registros]
                cursor.executemany(query, valores)
            
            insertar_lote("usuarios", data.get("usuarios", []))
            insertar_lote("clientes", data.get("clientes", []))
            insertar_lote("proveedores", data.get("proveedores", []))
            insertar_lote("inventario", data.get("inventario", []))
            insertar_lote("cotizaciones", data.get("cotizaciones", []))
            insertar_lote("cotizaciones_detalle", data.get("cotizaciones_detalle", []))
            insertar_lote("catalogo_um", data.get("catalogo_um", []))
            
            cursor.execute("PRAGMA foreign_keys = ON;")
            conexion.commit()
    except Exception as e:
        print(f"Error al forzar descarga: {e}")
    finally:
        conexion.close()

def procesar_arranque_app():
    """Se ejecuta al abrir el sistema. Sube cotizaciones offline y baja lo más nuevo."""
    import requests
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # 1. VERIFICAMOS SI HAY INTERNET
        requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        
        # 2. SUBIR COTIZACIONES EXTERNAS SI EXISTEN
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cotizaciones_ext'")
        if cursor.fetchone():
            cursor.execute("SELECT * FROM cotizaciones_ext")
            cotizaciones_ext = cursor.fetchall()
            
            if cotizaciones_ext:
                print("Subiendo cotizaciones offline encontradas...")
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
                resp = requests.post(URL_SUBIR_EXT, json=payload, timeout=10)
                
                if resp.status_code == 200 and resp.json().get("success"):
                    # Si se subieron bien, las borramos de la tabla temporal local
                    cursor.execute("DELETE FROM cotizaciones_detalle_ext")
                    cursor.execute("DELETE FROM cotizaciones_ext")
                    conexion.commit()
                    print("Cotizaciones offline subidas exitosamente.")
        
        # 3. SINCRONIZAR (DESCARGAR) LA BASE DE DATOS FRESCA
        forzar_descarga_nube()
        print("Base de datos sincronizada al arranque.")

    except requests.exceptions.RequestException:
        print("Iniciando en modo OFFLINE. No se pudo sincronizar el arranque.")
    except Exception as e:
        print(f"Error en arranque: {e}")
    finally:
        conexion.close()