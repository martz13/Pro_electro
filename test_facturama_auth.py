"""
Script de prueba para verificar credenciales de Facturama Producción.
Endpoint seguro que no genera ningún CFDI: solo consulta clientes.
"""
import requests

# ═══════════════════════════════════════════════════
# RELLENAR CON LAS CREDENCIALES REALES DE EDWIN
# ═══════════════════════════════════════════════════
CORREO_REAL = "edwgrro"
PASSWORD_REAL = "proelectro_123"

# ═══════════════════════════════════════════════════

url = "https://api.facturama.mx/api/client"
resp = requests.get(url, auth=(CORREO_REAL, PASSWORD_REAL), timeout=10)

print(f"HTTP Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Credenciales correctas. Conexión exitosa a Facturama Producción.")
else:
    print(f"❌ Error: {resp.text[:300]}")
