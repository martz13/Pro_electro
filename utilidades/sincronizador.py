import os
import time
import requests
from base_datos.conexion import obtener_conexion

# REEMPLAZA ESTA URL CON LA DE TU WORKER DE CLOUDFLARE
URL_API_SYNC = "https://api-pro-electro.pro-electro.workers.dev/api/sync"

def ejecutar_sincronizacion():
    """Lee la cola local y la envía a la nube. Falla en silencio si no hay red."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # 1. Leer todas las operaciones pendientes
        cursor.execute("SELECT id, tabla_afectada, operacion, registro_id, datos_json FROM sync_queue ORDER BY id ASC")
        pendientes = cursor.fetchall()

        if not pendientes:
            return # No hay nada que sincronizar, salimos en silencio

        # 2. Empaquetar los datos
        payload = []
        ids_a_borrar = []
        for p in pendientes:
            payload.append({
                "tabla_afectada": p[1],
                "operacion": p[2],
                "registro_id": p[3],
                "datos_json": p[4]
            })
            ids_a_borrar.append(p[0]) # Guardamos los IDs locales para borrarlos después

        # 3. Enviar a Cloudflare (Timeout corto de 5 segundos para no congelar nada)
        respuesta = requests.post(URL_API_SYNC, json=payload, timeout=5)

        # 4. Si la nube responde OK, borramos los registros locales
        if respuesta.status_code == 200 and respuesta.json().get("success"):
            placeholders = ",".join("?" * len(ids_a_borrar))
            cursor.execute(f"DELETE FROM sync_queue WHERE id IN ({placeholders})", ids_a_borrar)
            conexion.commit()
            print(f"[SYNC] Éxito: {len(ids_a_borrar)} registros subidos a la nube.")
        else:
            print(f"[SYNC] Error de la API: {respuesta.text}")

    except requests.exceptions.RequestException:
        # Falla en silencio: No hay internet o el servidor tardó en responder.
        # Los registros se quedan en la BD local para el siguiente intento.
        pass
    except Exception as e:
        print(f"[SYNC] Error local: {str(e)}")
    finally:
        conexion.close()

if __name__ == "__main__":
    print("Iniciando Sincronizador de Respaldo en segundo plano...")
    # Bucle infinito (El Task Scheduler Multiplataforma)
    while True:
        ejecutar_sincronizacion()
        time.sleep(300) # Duerme 5 minutos (300 segundos) y vuelve a intentar