import os
import time
import requests
from base_datos.conexion import obtener_conexion

# ==========================================
# URL EXACTA DE TU API (Debe terminar en /api/sync)
# ==========================================
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
            ids_a_borrar.append(p[0])

        # 3. Enviar a Cloudflare
        respuesta = requests.post(URL_API_SYNC, json=payload, timeout=5)

        # 4. Intentar decodificar JSON de forma segura
        try:
            datos_respuesta = respuesta.json()
        except ValueError:
            print(f"[SYNC] Error crítico: La API no devolvió JSON válido. Respuesta cruda: {respuesta.text}")
            return

        # 5. Si la nube responde OK, borramos los registros locales
        if respuesta.status_code == 200 and datos_respuesta.get("success"):
            placeholders = ",".join("?" * len(ids_a_borrar))
            cursor.execute(f"DELETE FROM sync_queue WHERE id IN ({placeholders})", ids_a_borrar)
            conexion.commit()
            print(f"[SYNC] Éxito: {len(ids_a_borrar)} registros subidos a la nube en la tabla {pendientes[0][1]}.")
        else:
            print(f"[SYNC] Error de la API: {respuesta.text}")

    except requests.exceptions.RequestException as e: # <-- CORRECCIÓN AQUÍ (as e)
        print(f"[SYNC] Falla de red o URL incorrecta: {e}")
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