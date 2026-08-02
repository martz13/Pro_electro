"""
Generador de PDF para Facturas Electrónicas (CFDI 4.0)
Diseño personalizado Pro Electro con QR, sellos digitales y cadena original.
"""
import os
import unicodedata
import tempfile
from fpdf import FPDF
from num2words import num2words
from base_datos.conexion import obtener_conexion
from utilidades.recursos import resource_path


# ==========================================
# CATÁLOGOS SAT
# ==========================================
REGIMENES = {
    "601": "GENERAL DE LEY PERSONAS MORALES",
    "603": "PERSONAS MORALES CON FINES NO LUCRATIVOS",
    "605": "SUELDOS Y SALARIOS E INGRESOS ASIMILADOS A SALARIOS",
    "606": "ARRENDAMIENTO",
    "607": "REGIMEN DE ENAJENACION O ADQUISICION DE BIENES",
    "608": "DEMAS INGRESOS",
    "610": "RESIDENTES EN EL EXTRANJERO SIN ESTABLECIMIENTO PERMANENTE EN MEXICO",
    "611": "INGRESOS POR DIVIDENDOS",
    "612": "PERSONAS FISICAS CON ACTIVIDADES EMPRESARIALES Y PROFESIONALES",
    "614": "INGRESOS POR INTERESES",
    "616": "SIN OBLIGACIONES FISCALES",
    "620": "SOCIEDADES COOPERATIVAS DE PRODUCCION",
    "621": "INCORPORACION FISCAL",
    "622": "ACTIVIDADES AGRICOLAS, GANADERAS, SILVICOLAS Y PESQUERAS",
    "623": "OPCIONAL PARA GRUPOS DE SOCIEDADES",
    "624": "COORDINADOS",
    "625": "ACTIVIDADES EMPRESARIALES CON INGRESOS A TRAVES DE PLATAFORMAS TECNOLOGICAS",
    "626": "REGIMEN SIMPLIFICADO DE CONFIANZA",
}

USOS_CFDI = {
    "G01": "ADQUISICION DE MERCANCIAS",
    "G03": "GASTOS EN GENERAL",
    "I01": "CONSTRUCCIONES",
    "I02": "MOBILIARIO Y EQUIPO DE OFICINA",
    "I03": "EQUIPO DE TRANSPORTE",
    "I08": "OTRA MAQUINARIA Y EQUIPO",
    "S01": "SIN EFECTOS FISCALES",
    "CP01": "PAGOS",
}

FORMAS_PAGO_DESC = {
    "01": "EFECTIVO",
    "02": "CHEQUE NOMINATIVO",
    "03": "TRANSFERENCIA ELECTRONICA DE FONDOS",
    "04": "TARJETA DE CREDITO",
    "28": "TARJETA DE DEBITO",
    "99": "POR DEFINIR",
}

METODOS_PAGO_DESC = {
    "PUE": "PAGO EN UNA SOLA EXHIBICION",
    "PPD": "PAGO EN PARCIALIDADES O DIFERIDO",
}


def clean_text(text):
    """Convierte texto Unicode a ASCII para compatibilidad con fpdf2 sin fuentes TTF."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


def generar_qr_temp(uuid, rfc_emisor, rfc_receptor, total, sello_cfdi):
    """Genera la imagen QR del SAT en un archivo temporal y devuelve la ruta."""
    try:
        import qrcode
        ultimos_8 = sello_cfdi[-8:] if sello_cfdi and len(sello_cfdi) >= 8 else "00000000"
        url = (
            f"https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx"
            f"?id={uuid}&re={rfc_emisor}&rr={rfc_receptor}"
            f"&tt={total:.6f}&fe={ultimos_8}"
        )
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        ruta_qr = os.path.join(tempfile.gettempdir(), f"qr_{uuid[:8]}.png")
        img.save(ruta_qr)
        return ruta_qr
    except Exception:
        return None


class PDFFactura(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_margins(5, 5, 5)
        self.set_auto_page_break(auto=True, margin=15)
        self.ROJO        = (192, 0, 0)
        self.NEGRO       = (0, 0, 0)
        self.BLANCO      = (255, 255, 255)
        self.GRIS_CLARO  = (240, 240, 240)   # fondo de encabezados
        self.GRIS_LINEA  = (200, 200, 200)   # líneas divisoras internas de tabla
        self.GRIS_TEXTO  = (100, 100, 100)   # texto secundario (objeto impuesto)


def generar_pdf_factura(factura_id, ruta_destino=None):
    """
    Genera el PDF personalizado de una factura CFDI 4.0.
    Retorna (exito: bool, ruta_archivo o mensaje_error: str)
    """
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        # ── 1. Datos de la factura ──────────────────────────────────────────
        cursor.execute("""
            SELECT id, cfdi_id, uuid, folio_fiscal, cotizacion_id, cliente_id,
                   fecha_timbrado, monto_total, estado,
                   cert_numero, sello_cfdi, sello_sat, cert_sat_numero,
                   rfc_pac, cadena_original, forma_pago, metodo_pago
            FROM facturas WHERE id = ?
        """, (factura_id,))
        row = cursor.fetchone()
        if not row:
            return False, "No se encontro la factura."
        (fac_id, cfdi_id, uuid, folio_fiscal, cotizacion_id, cliente_id,
         fecha_timbrado, monto_total, estado,
         cert_numero, sello_cfdi, sello_sat, cert_sat_numero,
         rfc_pac, cadena_original, forma_pago, metodo_pago) = row

        # ── 2. Datos del emisor ─────────────────────────────────────────────
        cursor.execute("""
            SELECT nombre_empresa, telefono, ubicacion, rfc,
                   representante_legal, regimen_fiscal, cp_fiscal
            FROM datos_fiscales WHERE id = 1
        """)
        emisor = cursor.fetchone()
        if not emisor:
            return False, "No hay datos fiscales configurados."
        nombre_emp, tel_emp, ubi_emp, rfc_emp, rep_legal, regimen_emp, cp_emp = emisor

        # ── 3. Datos del cliente ────────────────────────────────────────────
        cursor.execute("""
            SELECT nombre_completo, rfc, direccion, colonia,
                   poblacion, cp, regimen, cfdi
            FROM clientes WHERE id_cliente = ?
        """, (cliente_id,))
        cli = cursor.fetchone()
        if not cli:
            return False, "No se encontro el cliente."
        nom_cl, rfc_cl, dir_cl, col_cl, pob_cl, cp_cl, regimen_cl, cfdi_cl = cli

        # ── 4. Datos de la cotización ───────────────────────────────────────
        cursor.execute("""
            SELECT folio, vendedor, oc, obra
            FROM cotizaciones WHERE id_cotizacion = ?
        """, (cotizacion_id,))
        cot = cursor.fetchone()
        folio_cot, vendedor, oc, obra = cot if cot else ("", "", "", "")

        # ── 5. Productos ────────────────────────────────────────────────────
        cursor.execute("""
            SELECT cd.codigo_producto, cd.descripcion, cd.cantidad, cd.um,
                   cd.precio_unitario, cd.monto, i.clave_sat_producto
            FROM cotizaciones_detalle cd
            LEFT JOIN inventario i ON cd.codigo_producto = i.codigo_producto
            WHERE cd.cotizacion_id = ?
        """, (cotizacion_id,))
        productos = cursor.fetchall()

        cursor.execute("SELECT sigla, clave_sat_unidad FROM catalogo_um")
        claves_um = {s: (c or "H87") for s, c in cursor.fetchall()}

    except Exception as e:
        conn.close()
        return False, f"Error al obtener datos: {str(e)}"
    finally:
        conn.close()

    # ── Normalizar strings ──────────────────────────────────────────────────
    nombre_emp      = clean_text(nombre_emp      or "PRO ELECTRO")
    tel_emp         = clean_text(tel_emp         or "")
    ubi_emp         = clean_text(ubi_emp         or "")
    rfc_emp         = clean_text(rfc_emp         or "")
    rep_legal       = clean_text(rep_legal       or "")
    regimen_emp     = clean_text(regimen_emp     or "")
    cp_emp          = clean_text(cp_emp          or "")
    nom_cl          = clean_text(nom_cl          or "")
    rfc_cl          = clean_text(rfc_cl          or "")
    dir_cl          = clean_text(dir_cl          or "")
    col_cl          = clean_text(col_cl          or "")
    pob_cl          = clean_text(pob_cl          or "")
    cp_cl           = clean_text(cp_cl           or "")
    regimen_cl      = clean_text(regimen_cl      or "")
    cfdi_cl         = clean_text(cfdi_cl         or "")
    vendedor        = clean_text(vendedor        or "")
    oc              = clean_text(oc              or "N/A")
    folio_cot       = clean_text(folio_cot       or "")
    uuid            = uuid or ""
    fecha_timbrado  = clean_text(fecha_timbrado  or "")
    cert_numero     = clean_text(cert_numero     or "")
    sello_cfdi      = sello_cfdi      or ""
    sello_sat       = sello_sat       or ""
    cert_sat_numero = clean_text(cert_sat_numero or "")
    rfc_pac         = clean_text(rfc_pac         or "")
    cadena_original = cadena_original or ""
    forma_pago      = clean_text(forma_pago      or "")
    metodo_pago     = clean_text(metodo_pago     or "")

    # Descripciones legibles
    desc_regimen_emp = REGIMENES.get(regimen_emp, regimen_emp)
    desc_regimen_cl  = REGIMENES.get(regimen_cl,  regimen_cl)
    desc_uso_cfdi    = f"{cfdi_cl} - {USOS_CFDI.get(cfdi_cl, cfdi_cl)}"
    desc_forma_pago  = f"{forma_pago} - {FORMAS_PAGO_DESC.get(forma_pago, forma_pago)}"
    desc_metodo_pago = f"{metodo_pago} - {METODOS_PAGO_DESC.get(metodo_pago, metodo_pago)}"

    # Totales
    subtotal = round(monto_total / 1.16, 2)
    iva      = round(monto_total - subtotal, 2)
    pesos    = int(monto_total)
    centavos = int(round((monto_total - pesos) * 100))
    try:
        texto_letras = num2words(pesos, lang='es').upper()
    except Exception:
        texto_letras = str(pesos)
    importe_letra = f"({texto_letras} PESOS {centavos:02d}/100 M.N.)"

    ruta_logo = resource_path("recursos/logo.png")
    ruta_qr   = generar_qr_temp(uuid, rfc_emp, rfc_cl, monto_total, sello_cfdi)


def generar_pdf_factura(factura_id, ruta_destino=None):
    """
    Genera el PDF personalizado de una factura CFDI 4.0.
    Retorna (exito: bool, ruta_archivo o mensaje_error: str)
    """
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        # ── 1. Datos de la factura ──────────────────────────────────────────
        cursor.execute("""
            SELECT id, cfdi_id, uuid, folio_fiscal, cotizacion_id, cliente_id,
                   fecha_timbrado, monto_total, estado,
                   cert_numero, sello_cfdi, sello_sat, cert_sat_numero,
                   rfc_pac, cadena_original, forma_pago, metodo_pago
            FROM facturas WHERE id = ?
        """, (factura_id,))
        row = cursor.fetchone()
        if not row:
            return False, "No se encontro la factura."
        (fac_id, cfdi_id, uuid, folio_fiscal, cotizacion_id, cliente_id,
         fecha_timbrado, monto_total, estado,
         cert_numero, sello_cfdi, sello_sat, cert_sat_numero,
         rfc_pac, cadena_original, forma_pago, metodo_pago) = row

        # ── 2. Datos del emisor ─────────────────────────────────────────────
        cursor.execute("""
            SELECT nombre_empresa, telefono, ubicacion, rfc,
                   representante_legal, regimen_fiscal, cp_fiscal
            FROM datos_fiscales WHERE id = 1
        """)
        emisor = cursor.fetchone()
        if not emisor:
            return False, "No hay datos fiscales configurados."
        nombre_emp, tel_emp, ubi_emp, rfc_emp, rep_legal, regimen_emp, cp_emp = emisor

        # ── 3. Datos del cliente ────────────────────────────────────────────
        cursor.execute("""
            SELECT nombre_completo, rfc, direccion, colonia,
                   poblacion, cp, regimen, cfdi
            FROM clientes WHERE id_cliente = ?
        """, (cliente_id,))
        cli = cursor.fetchone()
        if not cli:
            return False, "No se encontro el cliente."
        nom_cl, rfc_cl, dir_cl, col_cl, pob_cl, cp_cl, regimen_cl, cfdi_cl = cli

        # ── 4. Datos de la cotización ───────────────────────────────────────
        cursor.execute("""
            SELECT folio, vendedor, oc, obra
            FROM cotizaciones WHERE id_cotizacion = ?
        """, (cotizacion_id,))
        cot = cursor.fetchone()
        folio_cot, vendedor, oc, obra = cot if cot else ("", "", "", "")

        # ── 5. Productos ────────────────────────────────────────────────────
        cursor.execute("""
            SELECT cd.codigo_producto, cd.descripcion, cd.cantidad, cd.um,
                   cd.precio_unitario, cd.monto, i.clave_sat_producto
            FROM cotizaciones_detalle cd
            LEFT JOIN inventario i ON cd.codigo_producto = i.codigo_producto
            WHERE cd.cotizacion_id = ?
        """, (cotizacion_id,))
        productos = cursor.fetchall()

        cursor.execute("SELECT sigla, clave_sat_unidad FROM catalogo_um")
        claves_um = {s: (c or "H87") for s, c in cursor.fetchall()}

    except Exception as e:
        conn.close()
        return False, f"Error al obtener datos: {str(e)}"
    finally:
        conn.close()

    # ── Normalizar strings ──────────────────────────────────────────────────
    nombre_emp      = clean_text(nombre_emp      or "PRO ELECTRO")
    tel_emp         = clean_text(tel_emp         or "")
    ubi_emp         = clean_text(ubi_emp         or "")
    rfc_emp         = clean_text(rfc_emp         or "")
    rep_legal       = clean_text(rep_legal       or "")
    regimen_emp     = clean_text(regimen_emp     or "")
    cp_emp          = clean_text(cp_emp          or "")
    nom_cl          = clean_text(nom_cl          or "")
    rfc_cl          = clean_text(rfc_cl          or "")
    dir_cl          = clean_text(dir_cl          or "")
    col_cl          = clean_text(col_cl          or "")
    pob_cl          = clean_text(pob_cl          or "")
    cp_cl           = clean_text(cp_cl           or "")
    regimen_cl      = clean_text(regimen_cl      or "")
    cfdi_cl         = clean_text(cfdi_cl         or "")
    vendedor        = clean_text(vendedor        or "")
    oc              = clean_text(oc              or "N/A")
    folio_cot       = clean_text(folio_cot       or "")
    uuid            = uuid or ""
    fecha_timbrado  = clean_text(fecha_timbrado  or "")
    cert_numero     = clean_text(cert_numero     or "")
    sello_cfdi      = sello_cfdi      or ""
    sello_sat       = sello_sat       or ""
    cert_sat_numero = clean_text(cert_sat_numero or "")
    rfc_pac         = clean_text(rfc_pac         or "")
    cadena_original = cadena_original or ""
    forma_pago      = clean_text(forma_pago      or "")
    metodo_pago     = clean_text(metodo_pago     or "")

    desc_regimen_emp = REGIMENES.get(regimen_emp, regimen_emp)
    desc_regimen_cl  = REGIMENES.get(regimen_cl,  regimen_cl)
    desc_uso_cfdi    = f"{cfdi_cl} - {USOS_CFDI.get(cfdi_cl, cfdi_cl)}"
    desc_forma_pago  = f"{forma_pago} - {FORMAS_PAGO_DESC.get(forma_pago, forma_pago)}"
    desc_metodo_pago = f"{metodo_pago} - {METODOS_PAGO_DESC.get(metodo_pago, metodo_pago)}"

    subtotal = round(monto_total / 1.16, 2)
    iva      = round(monto_total - subtotal, 2)
    pesos    = int(monto_total)
    centavos = int(round((monto_total - pesos) * 100))
    try:
        texto_letras = num2words(pesos, lang='es').upper()
    except Exception:
        texto_letras = str(pesos)
    importe_letra = f"({texto_letras} PESOS {centavos:02d}/100 M.N.)"

    ruta_logo = resource_path("recursos/logo.png")
    ruta_qr   = generar_qr_temp(uuid, rfc_emp, rfc_cl, monto_total, sello_cfdi)

    # ══════════════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DEL PDF (NUEVO DISEÑO ESTILO PRO ELECTRO)
    # ══════════════════════════════════════════════════════════════════════
    pdf = PDFFactura(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    # Colores definidos
    GRIS_OSCURO  = (190, 190, 190)
    GRIS_CLARITO = (240, 240, 240)

    # ── ENCABEZADO ─────────────────────────────────────────────────────────
    # Logo
    if os.path.exists(ruta_logo):
        pdf.image(ruta_logo, x=10, y=2, w=40)

    # Datos Emisor (Centro)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_xy(65, 10)
    pdf.cell(80, 5, nombre_emp, align="C")

    pdf.set_font("helvetica", "", 8)
    pdf.set_xy(65, 16)
    pdf.cell(80, 4, rep_legal, align="C")
    pdf.set_xy(65, 20)
    pdf.cell(80, 4, "PEDRO CELESTINO #100", align="C")
    pdf.set_xy(65, 24)
    pdf.cell(80, 4, f"{ubi_emp} C.P. {cp_emp}", align="C")
    pdf.set_xy(65, 28)
    pdf.cell(80, 4, f"TEL. {tel_emp}", align="C")
    
    pdf.set_font("helvetica", "B", 9)
    pdf.set_xy(65, 32)
    pdf.cell(80, 4, f"RFC: {rfc_emp}", align="C")

    # Recuadro FACTURA (Derecha)
    pdf.set_draw_color(0, 0, 0)
    pdf.rect(150, 10, 50, 25) 
    pdf.set_fill_color(*GRIS_OSCURO)
    pdf.rect(150, 10, 50, 6, style="FD") 
    
    pdf.set_font("helvetica", "B", 10)
    pdf.set_xy(150, 10)
    pdf.cell(50, 6, "F A C T U R A", align="C")
    
    pdf.set_text_color(*pdf.ROJO)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_xy(150, 18)
    pdf.cell(50, 5, folio_cot, align="C")
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "B", 7)
    pdf.set_xy(150, 25)
    pdf.cell(50, 4, "Fecha y hora de certificacion:", align="C")
    pdf.set_font("helvetica", "", 8)
    pdf.set_xy(150, 29)
    pdf.cell(50, 4, fecha_timbrado, align="C")

    # ── DATOS DEL CLIENTE + COMPROBANTE ────────────────────────────────────
    # y0 más abajo para dar 5mm extra entre recuadro FACTURA y estas tablas
    y0 = 39

    # Bloque Izquierdo (Cliente) — llega hasta x=125, deja 1mm antes del bloque derecho
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(10, y0, 115, 26, style="FD")
    pdf.set_fill_color(*GRIS_OSCURO)
    pdf.rect(10, y0, 115, 5, style="FD")

    pdf.set_font("helvetica", "B", 7)
    pdf.set_xy(10, y0)
    pdf.cell(115, 5, "FACTURADO A:", align="C")

    pdf.set_font("helvetica", "", 7)
    pdf.set_xy(12, y0 + 5)
    pdf.cell(110, 3.3, f"DATOS DE CLIENTE: {nom_cl}")
    pdf.set_xy(12, y0 + 8.3)
    pdf.cell(110, 3.3, dir_cl)
    pdf.set_xy(12, y0 + 11.6)
    pdf.cell(110, 3.3, f"COLONIA {col_cl} C.P. {cp_cl}")
    pdf.set_xy(12, y0 + 14.9)
    pdf.cell(110, 3.3, f"{pob_cl}")
    pdf.set_xy(12, y0 + 18.2)
    pdf.cell(110, 3.3, f"RFC. {rfc_cl}")
    pdf.set_font("helvetica", "", 6)
    pdf.set_xy(12, y0 + 21.5)
    pdf.cell(110, 3.3, f"REGIMEN FISCAL: {regimen_cl} {REGIMENES.get(regimen_cl, '')}")
    pdf.set_font("helvetica", "", 7)

    # ── FILA PEDIDO / VENDEDOR — mismo ancho que "FACTURADO A" (115), 1mm antes del bloque derecho
    y1 = y0 + 27
    w_cols1 = [25, 35, 30, 25]  # suma = 115, llega hasta x=125
    lbls1 = ["PEDIDO", "VENDEDOR", "CONDICIONES PAGO", "REFERENCIA"]
    vals1 = [folio_cot, vendedor, "CONTADO", oc]

    pdf.set_font("helvetica", "B", 7)
    pdf.set_fill_color(*GRIS_OSCURO)
    x_pos = 10
    for w, lbl in zip(w_cols1, lbls1):
        pdf.set_xy(x_pos, y1)
        pdf.cell(w, 5, lbl, border=1, fill=True, align="C")
        x_pos += w

    pdf.set_font("helvetica", "", 7)
    x_pos = 10
    for w, val in zip(w_cols1, vals1):
        pdf.set_xy(x_pos, y1 + 5)
        pdf.cell(w, 5, val, border=1, align="C")
        x_pos += w

    # Bloque Derecho (Comprobante) — empieza en x=126 (1mm después de x=125)
    # ancho=74 para llegar exactamente a x=200 (igual que la tabla principal)
    x_der    = 126
    w_lbl    = 22   # columna etiqueta reducida
    w_val    = 52   # columna valor (llega hasta 200: 126+22+52=200)
    altura_der = 37
    pdf.rect(x_der, y0, w_lbl + w_val, altura_der)
    # Sin línea divisora interior
    pdf.set_draw_color(255, 255, 255)
    pdf.line(x_der + w_lbl, y0, x_der + w_lbl, y0 + altura_der)
    pdf.set_draw_color(0, 0, 0)

    # Etiquetas con salto de línea en la columna izquierda
    datos_comp = [
        ("TIPO DE\nCOMPROBANTE",   "I - INGRESO"),
        ("LUGAR DE\nEXPEDICION",   cp_emp),
        ("FECHA DE\nEXPEDICION",   fecha_timbrado[:10]),
        ("USO CFDI",               desc_uso_cfdi),
        ("MONEDA",                 "MXN - PESO MEXICANO"),
    ]
    espacio_y = altura_der / len(datos_comp)
    for i, (lbl, val) in enumerate(datos_comp):
        y_fila = y0 + i * espacio_y
        # Etiqueta — puede tener salto de línea
        lineas_lbl = lbl.split("\n")
        pdf.set_font("helvetica", "", 5.5)
        if len(lineas_lbl) == 2:
            pdf.set_xy(x_der, y_fila + (espacio_y / 2) - 3.5)
            pdf.cell(w_lbl, 3.5, lineas_lbl[0], align="R")
            pdf.set_xy(x_der, y_fila + (espacio_y / 2))
            pdf.cell(w_lbl, 3.5, lineas_lbl[1], align="R")
        else:
            pdf.set_xy(x_der, y_fila + (espacio_y / 2) - 2)
            pdf.cell(w_lbl, 4, lbl, align="R")
        # Valor
        pdf.set_font("helvetica", "", 6.5)
        pdf.set_xy(x_der + w_lbl, y_fila + (espacio_y / 2) - 2)
        pdf.cell(w_val, 4, val, align="L")

    # ── TABLA DE PRODUCTOS (GRID ESTIRABLE) ─────────────────────────────────
    y2 = y1 + 11
    cols = [15, 18, 12, 16, 12, 73, 22, 22] # Suma = 190
    hdrs = ["CODIGO", "CANTIDAD", "UM", "CODIGO\nSAT", "UM\nSAT", "DESCRIPCION", "PRECIO\nUNITARIO", "IMPORTE"]

    pdf.set_fill_color(*GRIS_OSCURO)
    pdf.set_font("helvetica", "B", 6)
    
    # Dibujar fondo y contorno de cabecera
    pdf.set_draw_color(0, 0, 0)
    pdf.rect(10, y2, 190, 8, style="FD") 
    
    # Líneas verticales del encabezado en gris claro (igual que el cuerpo)
    pdf.set_draw_color(*GRIS_CLARITO)
    x_line = 10
    for w in cols[:-1]:
        x_line += w
        pdf.line(x_line, y2, x_line, y2 + 8)
    pdf.set_draw_color(0, 0, 0)

    # Imprimir textos (Centrados verticalmente para efecto Excel)
    x_pos = 10
    for i, h in enumerate(hdrs):
        if "\n" in h:
            pdf.set_xy(x_pos, y2 + 1)
            lineas = h.split("\n")
            pdf.cell(cols[i], 3, lineas[0], align="C")
            pdf.set_xy(x_pos, y2 + 4)
            pdf.cell(cols[i], 3, lineas[1], align="C")
        else:
            pdf.set_xy(x_pos, y2)
            pdf.cell(cols[i], 8, h, align="C")
        x_pos += cols[i]

    y_items_start = y2 + 8
    y_current = y_items_start
    # Guardamos la página donde empieza la tabla para dibujar el rect al final de esa página
    pagina_tabla_inicio = pdf.page_no()
    pdf.set_font("helvetica", "", 7)

    for prod in productos:
        cod, desc, cant, um, precio_unit, monto_prod, clave_sat = prod
        cod       = clean_text(cod)
        desc      = clean_text(desc)
        um        = clean_text(um or "PZ")
        clave_sat = clean_text(clave_sat)
        clave_um  = claves_um.get(um, "H87")

        # Estimar altura de fila
        pdf.set_font("helvetica", "", 7)
        chars_linea   = max(1, int(cols[5] / 1.85))
        n_lineas_desc = max(1, -(-len(desc) // chars_linea))
        alto_fila     = max(9, n_lineas_desc * 3.5 + 4)

        # ── Salto de página ────────────────────────────────────────────────
        if y_current + alto_fila > 268:
            # Cerrar tabla en esta página
            pdf.set_draw_color(0, 0, 0)
            pdf.rect(10, y_items_start, 190, y_current - y_items_start)
            pdf.set_draw_color(*GRIS_CLARITO)
            x_ln = 10
            for w in cols[:-1]:
                x_ln += w
                pdf.line(x_ln, y_items_start, x_ln, y_current)
            pdf.set_draw_color(0, 0, 0)

            pdf.add_page()
            # Repetir encabezado de tabla
            y2_nuevo = 10
            pdf.set_fill_color(*GRIS_OSCURO)
            pdf.set_font("helvetica", "B", 6)
            pdf.set_draw_color(0, 0, 0)
            pdf.rect(10, y2_nuevo, 190, 8, style="FD")
            pdf.set_draw_color(*GRIS_CLARITO)
            x_line = 10
            for w in cols[:-1]:
                x_line += w
                pdf.line(x_line, y2_nuevo, x_line, y2_nuevo + 8)
            pdf.set_draw_color(0, 0, 0)
            x_pos = 10
            for i, h in enumerate(hdrs):
                if "\n" in h:
                    lns = h.split("\n")
                    pdf.set_xy(x_pos, y2_nuevo + 1)
                    pdf.cell(cols[i], 3, lns[0], align="C")
                    pdf.set_xy(x_pos, y2_nuevo + 4)
                    pdf.cell(cols[i], 3, lns[1], align="C")
                else:
                    pdf.set_xy(x_pos, y2_nuevo)
                    pdf.cell(cols[i], 8, h, align="C")
                x_pos += cols[i]

            y_items_start = y2_nuevo + 8
            y_current     = y_items_start
            pdf.set_font("helvetica", "", 7)

        y_fila = y_current
        x_pos  = 10

        # Columnas fijas
        valores = [cod, f"{cant:g}", um, clave_sat, clave_um]
        for val, w_col in zip(valores, cols[:5]):
            pdf.set_xy(x_pos, y_fila + 1)
            pdf.cell(w_col, 4, val, align="C")
            x_pos += w_col

        # Descripción multi-línea
        pdf.set_font("helvetica", "", 7)
        pdf.set_xy(x_pos, y_fila + 1)
        pdf.multi_cell(cols[5], 3.5, desc, align="L")

        # Objeto de impuesto
        pdf.set_font("helvetica", "", 6)
        pdf.set_text_color(90, 90, 90)
        pdf.set_x(x_pos)
        pdf.cell(cols[5], 3, "02 - Con objeto de impuesto  |  IVA: Tasa 16%", align="L")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", "", 7)

        y_desc_end = pdf.get_y()
        x_pos += cols[5]

        # Precio e importe
        pdf.set_xy(x_pos, y_fila + 1)
        pdf.cell(cols[6], 4, f"${precio_unit:,.2f}", align="R")
        x_pos += cols[6]
        pdf.set_xy(x_pos, y_fila + 1)
        pdf.cell(cols[7], 4, f"${monto_prod:,.2f}", align="R")

        alto_real  = max(9, (y_desc_end - y_fila) + 3)
        y_current += alto_real

    # Borde exterior + líneas interiores de la última sección de tabla
    # 🌟 Borde exterior + líneas interiores (Grid Estirable) 🌟
    # Definimos un límite fijo (Y = 195) para que el diseño mantenga 
    # la proporción de la página y empuje los totales hacia abajo.
    LIMITE_Y_FIJO = 195
    
    if y_current < LIMITE_Y_FIJO:
        y_bottom = LIMITE_Y_FIJO
    else:
        y_bottom = y_current + 3

    pdf.set_draw_color(0, 0, 0)
    pdf.rect(10, y_items_start, 190, y_bottom - y_items_start)
    
    pdf.set_draw_color(*GRIS_CLARITO)
    x_ln = 10
    for w in cols[:-1]:
        x_ln += w
        pdf.line(x_ln, y_items_start, x_ln, y_bottom)
    pdf.set_draw_color(0, 0, 0)

    # ── TOTALES Y PAGARÉ ────────────────────────────────────────────────────
    # Si no caben totales + sección fiscal en lo que queda, nueva página
    ESPACIO_MINIMO = 60  # mm necesarios para totales + datos SAT básicos
    if y_bottom + ESPACIO_MINIMO > 268:
        pdf.add_page()
        y_totales = 15
    else:
        y_totales = y_bottom + 3

    pdf.set_font("helvetica", "B", 7)
    pdf.set_xy(10, y_totales)
    pdf.cell(140, 4, importe_letra)

    pdf.set_font("helvetica", "", 5)
    pagare_txt = "DEBO(EMOS) Y PAGARE(MOS) INCONDICIONALMENTE A LA ORDEN DE PRO ELECTRO EN MONTERREY, NUEVO LEON, EL IMPORTE TOTAL DE ESTA FACTURA POR MERCANCIA RECIBIDA A MI(NUESTRA) ENTERA CONFORMIDAD. EN CASO DE NO CUBRIRSE EN LA FECHA INDICADA CAUSARA UN INTERES MORATORIO."
    pdf.set_xy(10, y_totales + 5)
    pdf.multi_cell(140, 2.5, pagare_txt, align="J")

    x_tot      = 10 + sum(cols[:6])
    w_col_tot1 = cols[6]
    w_col_tot2 = cols[7]

    pdf.set_font("helvetica", "B", 7)
    pdf.set_fill_color(*GRIS_OSCURO)

    pdf.set_xy(x_tot, y_totales)
    pdf.cell(w_col_tot1, 5, "SUB-TOTAL", border=1, align="C", fill=True)
    pdf.cell(w_col_tot2, 5, f"${subtotal:,.2f}", border=1, align="R")

    pdf.set_xy(x_tot, y_totales + 5)
    pdf.cell(w_col_tot1, 5, "IVA 16%", border=1, align="C", fill=True)
    pdf.cell(w_col_tot2, 5, f"${iva:,.2f}", border=1, align="R")

    pdf.set_xy(x_tot, y_totales + 10)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(w_col_tot1, 6, "TOTAL", border=1, fill=True, align="C")
    pdf.set_fill_color(255, 255, 255)
    pdf.cell(w_col_tot2, 6, f"${monto_total:,.2f}", border=1, fill=True, align="R")

    # ── SECCIÓN FISCAL: SELLOS, CADENA Y QR ────────────────────────────────
    y_fiscal = y_totales + 20
    if y_fiscal + 40 > 268:
        pdf.add_page()
        y_fiscal = 15

    datos_sat = [
        ("Certificado de sello digital:",          cert_numero),
        ("No. de Serie del Certificado del SAT:",  cert_sat_numero),
        ("RFC del proveedor de certificacion:",    rfc_pac),
        ("Folio fiscal:",                          uuid),
    ]
    for i, (lbl, val) in enumerate(datos_sat):
        pdf.set_font("helvetica", "B", 6)
        pdf.set_xy(10, y_fiscal + (i * 3))
        pdf.cell(45, 3, lbl)
        pdf.set_font("helvetica", "", 6)
        pdf.cell(60, 3, val)

    y_cadenas = y_fiscal + 14

    def imprimir_texto_largo(lbl, texto_largo, x, y):
        if not texto_largo:
            return y
        if y + 8 > 268:
            pdf.add_page()
            y = 15
        pdf.set_font("helvetica", "B", 6)
        pdf.set_xy(x, y)
        pdf.cell(150, 3, lbl)
        y += 3
        pdf.set_font("helvetica", "", 5)
        chunk_size = 148
        texto_limpio = clean_text(texto_largo)
        for i in range(0, len(texto_limpio), chunk_size):
            if y + 3 > 272:
                pdf.add_page()
                y = 15
            pdf.set_xy(x, y)
            pdf.cell(150, 2.5, texto_limpio[i:i+chunk_size])
            y += 2.5
        return y + 1.5

    y_cadenas = imprimir_texto_largo("Cadena original del complemento de certificacion digital del SAT:", cadena_original, 10, y_cadenas)
    y_cadenas = imprimir_texto_largo("Sello digital del CFDI:", sello_cfdi, 10, y_cadenas)
    y_cadenas = imprimir_texto_largo("Sello digital del SAT:", sello_sat, 10, y_cadenas)

    # QR — se coloca junto a los datos SAT, no en Y fija
    if ruta_qr and os.path.exists(ruta_qr):
        pdf.image(ruta_qr, x=165, y=y_fiscal, w=35, h=35)

    # ── PIE DE PÁGINA — siempre en la última página, posición dinámica ──────
    y_footer = max(y_cadenas + 3, pdf.get_y() + 3)
    if y_footer + 10 > 275:
        pdf.add_page()
        y_footer = 268

    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, y_footer, 200, y_footer)
    pdf.set_draw_color(0, 0, 0)

    pdf.set_font("helvetica", "B", 5)
    pdf.set_xy(10, y_footer + 2)
    pdf.cell(100, 3, f"FORMA DE PAGO: {desc_forma_pago}")
    pdf.set_xy(105, y_footer + 2)
    pdf.cell(95, 3, f"REGIMEN FISCAL: {regimen_emp} - {desc_regimen_emp}")

    pdf.set_xy(10, y_footer + 5)
    pdf.cell(100, 3, f"METODO DE PAGO: {desc_metodo_pago}")
    pdf.set_font("helvetica", "B", 6)
    pdf.set_xy(10, y_footer + 8)
    pdf.cell(190, 3, "ESTE DOCUMENTO ES UNA REPRESENTACION IMPRESA DE UN CFDI", align="C")

    # ── GUARDAR ────────────────────────────────────────────────────────────
    if ruta_destino:
        ruta_guardado = ruta_destino
    else:
        ruta_guardado = os.path.join(tempfile.gettempdir(), f"Factura_{folio_cot}_{factura_id}.pdf")

    try:
        pdf.output(ruta_guardado)
        if ruta_qr and os.path.exists(ruta_qr):
            try: os.remove(ruta_qr) 
            except Exception: pass
        return True, ruta_guardado
    except Exception as e:
        return False, f"Error al guardar el PDF: {str(e)}"
