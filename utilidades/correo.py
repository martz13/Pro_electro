"""
Módulo de envío de correos electrónicos por SMTP (Gmail)
Pro Electro - Sistema de Gestión
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

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
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = SMTP_CORREO
        msg['To'] = correo_destino
        msg['Subject'] = f"Factura Electrónica {folio_factura} - Pro Electro"

        # Cuerpo del correo
        cuerpo = f"""Estimado/a {nombre_cliente},

Adjunto encontrará su factura electrónica (CFDI) con folio {folio_factura}.

Documentos adjuntos:
- Factura en formato PDF (representación impresa)
{"- Factura en formato XML (comprobante fiscal digital)" if ruta_xml else ""}

Si tiene alguna duda sobre este documento, no dude en contactarnos.

Atentamente,
Pro Electro
Tel. (81) 1634 7681
{SMTP_CORREO}

---
Este correo fue generado automáticamente por el sistema Pro Electro.
"""
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        # Adjuntar PDF
        if ruta_pdf and os.path.exists(ruta_pdf):
            with open(ruta_pdf, 'rb') as f:
                adjunto_pdf = MIMEBase('application', 'pdf')
                adjunto_pdf.set_payload(f.read())
                encoders.encode_base64(adjunto_pdf)
                nombre_archivo_pdf = f"Factura_{folio_factura}.pdf"
                adjunto_pdf.add_header('Content-Disposition', 'attachment', filename=nombre_archivo_pdf)
                msg.attach(adjunto_pdf)

        # Adjuntar XML (opcional)
        if ruta_xml and os.path.exists(ruta_xml):
            with open(ruta_xml, 'rb') as f:
                adjunto_xml = MIMEBase('application', 'xml')
                adjunto_xml.set_payload(f.read())
                encoders.encode_base64(adjunto_xml)
                nombre_archivo_xml = f"Factura_{folio_factura}.xml"
                adjunto_xml.add_header('Content-Disposition', 'attachment', filename=nombre_archivo_xml)
                msg.attach(adjunto_xml)

        # Enviar
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
