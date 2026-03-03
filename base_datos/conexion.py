import sqlite3
import os
import bcrypt

# Construimos la ruta dinámica. Esto asegura que funcione en tu Ubuntu
# y posteriormente en el Windows del cliente final sin cambiar una sola línea.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pro_electro.db")

# La ruta de tu script SQL original para cargar las tablas la primera vez
RUTA_SQL_ORIGINAL = "/home/mario/Documentos/Proyectos/PRO ELECTRO/DIagramaBD/SQL.sql"

def obtener_conexion():
    """Devuelve una conexión a la base de datos SQLite."""
    return sqlite3.connect(DB_PATH)

def inicializar_bd():
    """Crea la base de datos a partir del archivo SQL y agrega un usuario de prueba."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # 1. Crear las tablas a partir del archivo SQL.sql si existe
    if os.path.exists(RUTA_SQL_ORIGINAL):
        with open(RUTA_SQL_ORIGINAL, 'r', encoding='utf-8') as archivo_sql:
            script_sql = archivo_sql.read()
            # executescript ejecuta múltiples sentencias separadas por ;
            cursor.executescript(script_sql)
    else:
        print(f"Advertencia: No se encontró el archivo {RUTA_SQL_ORIGINAL}.")

    # 2. Insertar usuario de prueba (si no existe previamente)
    cursor.execute("SELECT * FROM usuarios WHERE correo = ?", ("admin@proelectro.mx",))
    if not cursor.fetchone():
        # Encriptar la contraseña "admin123"
        password_plana = "admin123".encode('utf-8')
        password_hash = bcrypt.hashpw(password_plana, bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute(
            "INSERT INTO usuarios (nombre_completo,correo, password, rol) VALUES (?,?, ?, ?)",
            ("Edwin Guerrero","admin@proelectro.mx", password_hash, "Super admin")
        )
        print("✅ Usuario de prueba creado: admin@proelectro.mx / Contraseña: admin123")

    conexion.commit()
    conexion.close()