"""
Módulo de envío de correos electrónicos por SMTP (Gmail)
Pro Electro - Sistema de Gestión
"""
import smtplib
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders

from utilidades.recursos import resource_path

# ==========================================
# CONFIGURACIÓN SMTP - GMAIL
# ==========================================
# Correo desde el cual se envían las facturas
SMTP_CORREO = "admin@proelectro.mx"
# Contraseña de aplicación de Google (NO es la contraseña normal del correo)
# Generar en: https://myaccount.google.com/apppasswords
SMTP_PASSWORD = "lmnw luwk qdfu rklr"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def enviar_factura_por_correo(correo_destino, nombre_cliente, folio_factura, ruta_pdf, ruta_xml=None):
    """
    Envía la factura (PDF + XML opcional) por correo electrónico.

    Args:
        correo_destino: Email del cliente
        nombre_cliente: Nombre del cliente (para el saludo)
        folio_factura: Folio de la factura para el asunto
        ruta_pdf: Ruta al archivo PDF de la factura
        ruta_xml: Ruta al archivo XML (opcional)

    Returns:
        (exito: bool, mensaje: str)
    """
    if SMTP_PASSWORD == "AQUI_VA_TU_CONTRASEÑA_DE_APLICACION":
        return False, "No se ha configurado la contraseña de aplicación de Gmail.\nContacta al desarrollador."

    try:
        # Obtener teléfono de datos fiscales
        from base_datos.conexion import obtener_conexion
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT telefono FROM datos_fiscales WHERE id = 1")
        row = cursor.fetchone()
        telefono_empresa = row[0] if row and row[0] else "(81) 8255 2128"
        conn.close()

        # ── Leer imagen de firma ────────────────────────────────────────────
        ruta_firma = resource_path("recursos/iconos/FIRMA.png")
        firma_disponible = os.path.exists(ruta_firma)

        # ── Construir cuerpo HTML ───────────────────────────────────────────
        adjuntos_desc = """
            <li>Factura en formato <strong>PDF</strong> (representación impresa)</li>"""
        if ruta_xml:
            adjuntos_desc += """
            <li>Factura en formato <strong>XML</strong> (comprobante fiscal digital)</li>"""

        if firma_disponible:
            bloque_firma = '<img src="cid:firma_proelectro" alt="Pro Electro" style="max-width:600px; width:100%;" />'
        else:
            bloque_firma = f"""
            <p style="margin:0; font-size:13px; color:#555;">
                Atentamente,<br/>
                <strong>Pro Electro</strong><br/>
                Tel. {telefono_empresa}<br/>
                {SMTP_CORREO}
            </p>"""

        cuerpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 650px; margin: 0 auto;">

          <p style="font-size:15px;">Estimado/a <strong>{nombre_cliente}</strong>,</p>

          <p style="font-size:14px;">
            Adjunto encontrará su factura electrónica (CFDI) con folio
            <strong>{folio_factura}</strong>.
          </p>

          <p style="font-size:14px; margin-bottom: 6px;"><strong>Documentos adjuntos:</strong></p>
          <ul style="font-size:14px;">{adjuntos_desc}
          </ul>

          <p style="font-size:14px;">
            Si tiene alguna duda sobre este documento, no dude en contactarnos.
          </p>

          <br/>
          {bloque_firma}

          <br/>
          <p style="font-size:11px; color:#999; border-top:1px solid #eee; padding-top:8px; margin-top:16px;">
            Este correo fue generado automáticamente por el sistema Pro Electro.
          </p>

        </body>
        </html>
        """

        # ── Armar mensaje (related para poder incrustar imagen inline) ──────
        msg = MIMEMultipart("related")
        msg['From']    = SMTP_CORREO
        msg['To']      = correo_destino
        msg['Subject'] = f"Factura Electrónica {folio_factura} - Pro Electro"

        # El contenido HTML va dentro de un "alternative" anidado
        parte_alternativa = MIMEMultipart("alternative")
        parte_alternativa.attach(MIMEText(cuerpo_html, "html", "utf-8"))
        msg.attach(parte_alternativa)

        # Imagen de firma inline (solo si existe el archivo)
        if firma_disponible:
            with open(ruta_firma, "rb") as f:
                img_firma = MIMEImage(f.read())
            img_firma.add_header("Content-ID", "<firma_proelectro>")
            img_firma.add_header("Content-Disposition", "inline", filename="firma.png")
            msg.attach(img_firma)

        # ── Adjuntar PDF ────────────────────────────────────────────────────
        if ruta_pdf and os.path.exists(ruta_pdf):
            with open(ruta_pdf, "rb") as f:
                adjunto_pdf = MIMEBase("application", "pdf")
                adjunto_pdf.set_payload(f.read())
            encoders.encode_base64(adjunto_pdf)
            adjunto_pdf.add_header(
                "Content-Disposition", "attachment",
                filename=f"Factura_{folio_factura}.pdf"
            )
            msg.attach(adjunto_pdf)

        # ── Adjuntar XML (opcional) ─────────────────────────────────────────
        if ruta_xml and os.path.exists(ruta_xml):
            with open(ruta_xml, "rb") as f:
                adjunto_xml = MIMEBase("application", "xml")
                adjunto_xml.set_payload(f.read())
            encoders.encode_base64(adjunto_xml)
            adjunto_xml.add_header(
                "Content-Disposition", "attachment",
                filename=f"Factura_{folio_factura}.xml"
            )
            msg.attach(adjunto_xml)

        # ── Enviar ──────────────────────────────────────────────────────────
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_CORREO, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True, f"Factura enviada exitosamente a {correo_destino}"

    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticación SMTP.\nVerifica la contraseña de aplicación de Gmail."
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {str(e)}"
    except Exception as e:
        return False, f"Error al enviar correo: {str(e)}"
