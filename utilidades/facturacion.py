"""
Módulo de Facturación Electrónica (CFDI 4.0)
Comunicación con la API de Facturama (Sandbox/Producción)
Pro Electro - Sistema de Gestión
"""
import requests
import os
import tempfile
import webbrowser
from base_datos.conexion import obtener_conexion

# ==========================================
# CONFIGURACIÓN DE FACTURAMA
# ==========================================
FACTURAMA_SANDBOX_URL = "https://apisandbox.facturama.mx"
FACTURAMA_PROD_URL = "https://api.facturama.mx"

# Credenciales Facturama
# PRODUCCIÓN - RFC real de Edwin
FACTURAMA_USER = "edwgrro"
FACTURAMA_PASS = "proelectro_123"
FACTURAMA_ENV = "production"


def obtener_url_base():
    """Retorna la URL base según el entorno configurado"""
    if FACTURAMA_ENV == "production":
        return FACTURAMA_PROD_URL
    return FACTURAMA_SANDBOX_URL


def obtener_auth():
    """Retorna la tupla de autenticación para requests"""
    return (FACTURAMA_USER, FACTURAMA_PASS)


# ==========================================
# VALIDACIÓN DE DATOS ANTES DE FACTURAR
# ==========================================
def validar_datos_facturacion(cotizacion_id):
    """
    Valida que todos los datos estén completos para facturar.
    Retorna (valido: bool, errores: list)
    """
    errores = []
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        # 1. Validar datos del emisor (datos_fiscales)
        cursor.execute("""
            SELECT nombre_empresa, rfc, regimen_fiscal, cp_fiscal 
            FROM datos_fiscales WHERE id = 1
        """)
        emisor = cursor.fetchone()
        
        if not emisor:
            errores.append("No hay datos fiscales configurados.")
            return False, errores
        
        nombre_emisor, rfc_emisor, regimen_emisor, cp_emisor = emisor
        
        if not rfc_emisor:
            errores.append("Falta el RFC del emisor en Datos Fiscales.")
        if not regimen_emisor:
            errores.append("Falta el Régimen Fiscal del emisor en Datos Fiscales.")
        if not cp_emisor:
            errores.append("Falta el Código Postal Fiscal del emisor en Datos Fiscales.")

        # 2. Validar datos del cliente (receptor)
        cursor.execute("""
            SELECT c.nombre_completo, c.rfc, c.regimen, c.cfdi, c.cp
            FROM cotizaciones cot
            JOIN clientes c ON cot.cliente_id = c.id_cliente
            WHERE cot.id_cotizacion = ?
        """, (cotizacion_id,))
        cliente = cursor.fetchone()

        if not cliente:
            errores.append("No se encontró el cliente asociado a esta cotización.")
            return False, errores

        nombre_cliente, rfc_cliente, regimen_cliente, cfdi_cliente, cp_cliente = cliente

        if not rfc_cliente:
            errores.append(f"El cliente '{nombre_cliente}' no tiene RFC registrado.")
        if not regimen_cliente:
            errores.append(f"El cliente '{nombre_cliente}' no tiene Régimen Fiscal registrado.")
        if not cfdi_cliente:
            errores.append(f"El cliente '{nombre_cliente}' no tiene Uso de CFDI registrado.")
        if not cp_cliente:
            errores.append(f"El cliente '{nombre_cliente}' no tiene Código Postal registrado.")

        # 3. Validar productos (claves SAT)
        cursor.execute("""
            SELECT cd.codigo_producto, cd.descripcion, i.clave_sat_producto, i.um
            FROM cotizaciones_detalle cd
            LEFT JOIN inventario i ON cd.codigo_producto = i.codigo_producto
            WHERE cd.cotizacion_id = ?
        """, (cotizacion_id,))
        productos = cursor.fetchall()

        if not productos:
            errores.append("La cotización no tiene productos.")
            return False, errores

        productos_sin_clave = []
        for codigo, desc, clave_sat, um in productos:
            if not clave_sat:
                productos_sin_clave.append(f"  • {codigo} - {desc}")

        if productos_sin_clave:
            errores.append("Los siguientes productos NO tienen Clave SAT asignada:\n" + "\n".join(productos_sin_clave[:10]))
            if len(productos_sin_clave) > 10:
                errores.append(f"  ... y {len(productos_sin_clave) - 10} más.")

        # 4. Validar claves SAT de unidades de medida
        cursor.execute("""
            SELECT DISTINCT cd.um 
            FROM cotizaciones_detalle cd
            WHERE cd.cotizacion_id = ?
        """, (cotizacion_id,))
        unidades = cursor.fetchall()

        for (um,) in unidades:
            if um and um != "S/U":
                cursor.execute("SELECT clave_sat_unidad FROM catalogo_um WHERE sigla = ?", (um,))
                row = cursor.fetchone()
                if not row or not row[0]:
                    errores.append(f"La unidad de medida '{um}' no tiene Clave SAT asignada (Gestionar UM).")

    except Exception as e:
        errores.append(f"Error al validar: {str(e)}")
    finally:
        conn.close()

    return len(errores) == 0, errores


# ==========================================
# TIMBRADO DE CFDI
# ==========================================
def timbrar_cfdi(cotizacion_id, forma_pago="03", metodo_pago="PUE", uso_cfdi=None):
    """
    Genera y timbra un CFDI a partir de una cotización.
    
    Args:
        cotizacion_id: ID de la cotización a facturar
        forma_pago: Código de forma de pago (03=Transferencia, 01=Efectivo, etc.)
        metodo_pago: PUE (una exhibición) o PPD (parcialidades)
        uso_cfdi: Uso del CFDI (si None, se toma del cliente)
    
    Returns:
        (exito: bool, datos: dict o mensaje_error: str)
        Si éxito: datos = {"cfdi_id": "...", "uuid": "...", "folio": "..."}
    """
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        # 1. Obtener datos del emisor
        cursor.execute("""
            SELECT nombre_empresa, rfc, regimen_fiscal, cp_fiscal 
            FROM datos_fiscales WHERE id = 1
        """)
        emisor = cursor.fetchone()
        nombre_emisor, rfc_emisor, regimen_emisor, cp_emisor = emisor

        # 2. Obtener datos del cliente
        cursor.execute("""
            SELECT c.nombre_completo, c.rfc, c.regimen, c.cfdi, c.cp
            FROM cotizaciones cot
            JOIN clientes c ON cot.cliente_id = c.id_cliente
            WHERE cot.id_cotizacion = ?
        """, (cotizacion_id,))
        cliente = cursor.fetchone()
        nombre_cliente, rfc_cliente, regimen_cliente, cfdi_cliente, cp_cliente = cliente

        # Usar el uso_cfdi proporcionado o el del cliente
        uso_cfdi_final = uso_cfdi if uso_cfdi else cfdi_cliente

        # 3. Obtener productos de la cotización
        cursor.execute("""
            SELECT cd.codigo_producto, cd.descripcion, cd.cantidad, cd.um, 
                   cd.precio_unitario, cd.monto, i.clave_sat_producto
            FROM cotizaciones_detalle cd
            LEFT JOIN inventario i ON cd.codigo_producto = i.codigo_producto
            WHERE cd.cotizacion_id = ?
        """, (cotizacion_id,))
        productos = cursor.fetchall()

        # 4. Construir los Items del CFDI
        items = []
        for codigo, desc, cantidad, um, precio_unit, monto, clave_sat_prod in productos:
            # Obtener clave SAT de la unidad
            clave_um = "H87"  # Default: Pieza
            if um and um != "S/U":
                cursor.execute("SELECT clave_sat_unidad FROM catalogo_um WHERE sigla = ?", (um,))
                row = cursor.fetchone()
                if row and row[0]:
                    clave_um = row[0]

            subtotal = round(cantidad * precio_unit, 2)
            iva = round(subtotal * 0.16, 2)
            total_item = round(subtotal + iva, 2)

            item = {
                "ProductCode": clave_sat_prod or "01010101",
                "IdentificationNumber": codigo,
                "Description": desc,
                "Unit": um or "Pieza",
                "UnitCode": clave_um,
                "UnitPrice": round(precio_unit, 2),
                "Quantity": round(cantidad, 2),
                "Subtotal": subtotal,
                "TaxObject": "02",  # Sí objeto de impuesto
                "Taxes": [
                    {
                        "Total": iva,
                        "Name": "IVA",
                        "Base": subtotal,
                        "Rate": 0.16,
                        "IsRetention": False
                    }
                ],
                "Total": total_item
            }
            items.append(item)

        # 5. Construir el payload del CFDI
        cfdi_payload = {
            "Currency": "MXN",
            "ExpeditionPlace": cp_emisor,
            "CfdiType": "I",  # Ingreso
            "PaymentForm": forma_pago,
            "PaymentMethod": metodo_pago,
            "Receiver": {
                "Rfc": rfc_cliente,
                "Name": nombre_cliente,
                "CfdiUse": uso_cfdi_final,
                "FiscalRegime": regimen_cliente,
                "TaxZipCode": cp_cliente
            },
            "Items": items
        }

        # 6. Enviar a Facturama
        url = f"{obtener_url_base()}/api/3/cfdis"

        # DEBUG TEMPORAL - Ver payload y respuesta completa
        import json
        print("=" * 60)
        print("PAYLOAD ENVIADO A FACTURAMA:")
        print(json.dumps(cfdi_payload, indent=2, ensure_ascii=False))
        print("=" * 60)

        resp = requests.post(url, json=cfdi_payload, auth=obtener_auth(), timeout=30)

        print(f"RESPUESTA HTTP: {resp.status_code}")
        print(f"RESPUESTA BODY: {resp.text}")
        print("=" * 60)

        if resp.status_code in (200, 201):
            data = resp.json()
            timbre = data.get("Complement", {}).get("TaxStamp", {})
            resultado = {
                "cfdi_id":        data.get("Id", ""),
                "uuid":           timbre.get("Uuid", ""),
                "folio":          data.get("Folio", ""),
                "fecha":          data.get("Date", ""),
                "cert_numero":    data.get("CertNumber", ""),
                "sello_cfdi":     timbre.get("CfdiSign", ""),
                "sello_sat":      timbre.get("SatSign", ""),
                "cert_sat_numero":timbre.get("SatCertNumber", ""),
                "rfc_pac":        timbre.get("RfcProvCertif", ""),
                "cadena_original":data.get("OriginalString", ""),
            }
            return True, resultado
        else:
            # Extraer mensaje de error detallado de Facturama
            try:
                error_data = resp.json()
                if isinstance(error_data, dict):
                    # Intentar extraer mensaje principal
                    msg = error_data.get("Message", "") or error_data.get("message", "")
                    # Extraer errores de ModelState (validación de campos)
                    model_state = error_data.get("ModelState", {})
                    if model_state:
                        detalles = []
                        for campo, errores in model_state.items():
                            if isinstance(errores, list):
                                detalles.append(f"• {campo}: {', '.join(errores)}")
                            else:
                                detalles.append(f"• {campo}: {errores}")
                        if detalles:
                            msg = (msg + "\n" if msg else "") + "\n".join(detalles)
                    # Extraer lista de Errors
                    errors_list = error_data.get("Errors", []) or error_data.get("errors", [])
                    if errors_list and isinstance(errors_list, list):
                        detalles = [f"• {e}" if isinstance(e, str) else f"• {e.get('Message', str(e))}" for e in errors_list]
                        msg = (msg + "\n" if msg else "") + "\n".join(detalles)
                    if not msg:
                        msg = json.dumps(error_data, ensure_ascii=False, indent=2)
                else:
                    msg = str(error_data)
            except Exception:
                msg = f"Error HTTP {resp.status_code}: {resp.text[:500]}"
            return False, msg

    except requests.exceptions.RequestException as e:
        return False, f"Error de conexión: {str(e)}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"
    finally:
        conn.close()


# ==========================================
# DESCARGAR PDF
# ==========================================
def descargar_pdf(cfdi_id):
    """
    Descarga el PDF de una factura a un archivo temporal.
    Facturama devuelve el contenido en Base64 dentro de un JSON: {"Content": "base64...", "ContentType": "application/pdf"}
    Retorna (exito: bool, ruta_archivo o mensaje_error: str)
    """
    import base64
    try:
        url = f"{obtener_url_base()}/api/Cfdi/Pdf/issued/{cfdi_id}"
        resp = requests.get(url, auth=obtener_auth(), timeout=15)

        if resp.status_code == 200:
            ruta_temp = os.path.join(tempfile.gettempdir(), f"Factura_{cfdi_id}.pdf")
            # Facturama puede devolver JSON con Base64 o bytes directos
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type or resp.content[:1] == b'{':
                try:
                    data = resp.json()
                    contenido_b64 = data.get("Content", "")
                    contenido = base64.b64decode(contenido_b64)
                except Exception:
                    contenido = resp.content
            else:
                contenido = resp.content

            with open(ruta_temp, 'wb') as f:
                f.write(contenido)
            return True, ruta_temp
        else:
            return False, f"Error al descargar PDF: HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexión: {str(e)}"


def abrir_pdf_en_navegador(cfdi_id):
    """Descarga y abre el PDF de la factura en el navegador"""
    exito, resultado = descargar_pdf(cfdi_id)
    if exito:
        webbrowser.open(f"file://{resultado}")
        return True, resultado
    return False, resultado


# ==========================================
# DESCARGAR XML
# ==========================================
def descargar_xml(cfdi_id):
    """
    Descarga el XML de una factura.
    Facturama devuelve el contenido en Base64 dentro de un JSON: {"Content": "base64...", "ContentType": "text/xml"}
    Retorna (exito: bool, ruta_archivo o mensaje_error: str)
    """
    import base64
    try:
        url = f"{obtener_url_base()}/api/Cfdi/Xml/issued/{cfdi_id}"
        resp = requests.get(url, auth=obtener_auth(), timeout=15)

        if resp.status_code == 200:
            ruta_temp = os.path.join(tempfile.gettempdir(), f"Factura_{cfdi_id}.xml")
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type or resp.content[:1] == b'{':
                try:
                    data = resp.json()
                    contenido_b64 = data.get("Content", "")
                    contenido = base64.b64decode(contenido_b64)
                except Exception:
                    contenido = resp.content
            else:
                contenido = resp.content

            with open(ruta_temp, 'wb') as f:
                f.write(contenido)
            return True, ruta_temp
        else:
            return False, f"Error al descargar XML: HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexión: {str(e)}"


# ==========================================
# CANCELAR CFDI
# ==========================================
# Motivos de cancelación del SAT
MOTIVOS_CANCELACION = {
    "01": "Comprobante emitido con errores con relación",
    "02": "Comprobante emitido con errores sin relación",
    "03": "No se llevó a cabo la operación",
    "04": "Operación nominativa relacionada en una factura global"
}


def cancelar_cfdi(cfdi_id, uuid, motivo="02"):
    """
    Cancela un CFDI ante el SAT.
    
    Args:
        cfdi_id: ID interno de Facturama
        uuid: UUID del timbre fiscal
        motivo: Código de motivo de cancelación (01, 02, 03, 04)
    
    Returns:
        (exito: bool, mensaje: str)
    """
    try:
        url = f"{obtener_url_base()}/api/Cfdi/{cfdi_id}?type=issued&motive={motivo}"
        
        # Si el motivo es "01" se necesita el UUID de la factura que sustituye
        # Por ahora manejamos los motivos simples (02, 03, 04)
        resp = requests.delete(url, auth=obtener_auth(), timeout=30)

        if resp.status_code == 200:
            return True, "CFDI cancelado exitosamente."
        else:
            try:
                error = resp.json()
                msg = error.get("Message", "") or str(error)
            except:
                msg = f"Error HTTP {resp.status_code}: {resp.text[:200]}"
            return False, msg
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexión: {str(e)}"


# ==========================================
# ENVIAR FACTURA POR CORREO
# ==========================================
def enviar_por_correo(cfdi_id, correo_destino):
    """
    Envía la factura (PDF + XML) por correo electrónico usando Facturama.
    Retorna (exito: bool, mensaje: str)
    """
    try:
        url = f"{obtener_url_base()}/api/Cfdi?cfdiType=issued&cfdiId={cfdi_id}&email={correo_destino}"
        resp = requests.post(url, auth=obtener_auth(), timeout=15)

        if resp.status_code == 200:
            return True, f"Factura enviada a {correo_destino}"
        else:
            return False, f"Error al enviar correo: HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexión: {str(e)}"


# ==========================================
# CATÁLOGOS SAT (FORMAS Y MÉTODOS DE PAGO)
# ==========================================
FORMAS_PAGO = [
    ("01", "Efectivo"),
    ("02", "Cheque nominativo"),
    ("03", "Transferencia electrónica de fondos"),
    ("04", "Tarjeta de crédito"),
    ("28", "Tarjeta de débito"),
    ("99", "Por definir"),
]

METODOS_PAGO = [
    ("PUE", "Pago en una sola exhibición"),
    ("PPD", "Pago en parcialidades o diferido"),
]

USOS_CFDI = [
    ("G01", "Adquisición de mercancías"),
    ("G03", "Gastos en general"),
    ("I01", "Construcciones"),
    ("I02", "Mobiliario y equipo de oficina"),
    ("I03", "Equipo de transporte"),
    ("I08", "Otra maquinaria y equipo"),
    ("S01", "Sin efectos fiscales"),
    ("CP01", "Pagos"),
]
