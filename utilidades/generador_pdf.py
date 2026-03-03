import os
import unicodedata
from fpdf import FPDF
from num2words import num2words
from PySide6.QtWidgets import QFileDialog, QMessageBox
from base_datos.conexion import obtener_conexion
from utilidades.recursos import resource_path

def clean_text(text):
    """Convierte texto Unicode a ASCII aproximado, eliminando acentos y caracteres especiales."""
    if not isinstance(text, str):
        text = str(text)
    # Normalizar y eliminar diacríticos
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

class PDFCotizacion(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=15)
        # Colores corporativos
        self.rojo_oscuro = (192, 0, 0)
        self.negro = (0, 0, 0)
        self.blanco = (255, 255, 255)
        self.verde = (0, 153, 51)
        self.naranja_oscuro = (204, 102, 0) # Nuevo color para Sobrepedido

def generar_pdf_cotizacion(folio_cotizacion, parent_widget=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # 1. Obtener datos de la cotización y el cliente
    query_cot = """
        SELECT c.id_cotizacion, c.folio, c.fecha, c.vendedor, c.oc, c.obra, c.monto_total,
               cl.id_cliente, cl.nombre_completo, cl.rfc, cl.direccion, cl.colonia, cl.poblacion, cl.cp
        FROM cotizaciones c
        JOIN clientes cl ON c.cliente_id = cl.id_cliente
        WHERE c.folio = ?
    """
    cursor.execute(query_cot, (folio_cotizacion,))
    cot_data = cursor.fetchone()
    
    if not cot_data:
        conexion.close()
        return False, "No se encontró la cotización."

    id_cot, folio, fecha, vendedor, oc, obra, total, id_cl, nom_cl, rfc_cl, dir_cl, col_cl, pob_cl, cp_cl = cot_data

    # 2. Obtener datos fiscales de la empresa
    cursor.execute("SELECT representante_legal, telefono, ubicacion, rfc, terminos_condiciones FROM datos_fiscales WHERE id=1")
    fiscal_data = cursor.fetchone()
    rep_legal, tel_emp, ubi_emp, rfc_emp, terminos = fiscal_data if fiscal_data else ("-", "-", "-", "-", "")

    # 3. Obtener detalle de productos (INCLUYENDO DISPONIBILIDAD)
    cursor.execute("SELECT codigo_producto, descripcion, cantidad, um, precio_unitario, monto, disponibilidad FROM cotizaciones_detalle WHERE cotizacion_id=?", (id_cot,))
    productos = cursor.fetchall()
    conexion.close()

    # Limpiar textos que puedan contener caracteres especiales
    rep_legal = clean_text(rep_legal)
    tel_emp = clean_text(tel_emp)
    ubi_emp = clean_text(ubi_emp)
    rfc_emp = clean_text(rfc_emp)
    nom_cl = clean_text(nom_cl)
    rfc_cl = clean_text(rfc_cl)
    dir_cl = clean_text(dir_cl)
    col_cl = clean_text(col_cl)
    pob_cl = clean_text(pob_cl)
    cp_cl = clean_text(cp_cl)
    vendedor = clean_text(vendedor)
    oc = clean_text(oc if oc else "N/D")
    obra = clean_text(obra if obra else "N/D")
    terminos = clean_text(terminos)
    # Para productos, limpiar descripción (otros campos son numéricos o códigos sin acentos)
    productos_limpios = []
    for prod in productos:
        cod, desc, cant, um, precio, monto, disp = prod
        desc_limpia = clean_text(desc)
        um_limpia = clean_text(um)
        productos_limpios.append((cod, desc_limpia, cant, um_limpia, precio, monto, disp))

    # --- INICIO DEL DISEÑO DEL PDF ---
    pdf = PDFCotizacion(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    
    # Fuentes y rutas
    ruta_logo = resource_path("recursos/logo.png")

    # ================= ENCABEZADO IZQUIERDO =================
    if os.path.exists(ruta_logo):
        pdf.image(ruta_logo, x=10, y=8, w=32) 
    
    pdf.set_font("helvetica", "B", 9)
    pdf.set_xy(10, 35)
    pdf.cell(0, 4, rep_legal, ln=True)
    pdf.cell(0, 4, f"TEL. {tel_emp}", ln=True)
    pdf.cell(0, 4, ubi_emp, ln=True)
    pdf.cell(0, 4, rfc_emp, ln=True)
    pdf.ln(2)

    # Etiqueta CLIENTE roja
    pdf.set_fill_color(*pdf.rojo_oscuro)
    pdf.set_text_color(*pdf.blanco)
    pdf.cell(20, 5, "CLIENTE", border=0, ln=True, fill=True, align="C")
    
    # Datos del cliente
    pdf.set_text_color(*pdf.negro)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 4, nom_cl, ln=True)
    pdf.cell(0, 4, rfc_cl, ln=True)
    pdf.cell(0, 4, dir_cl, ln=True)
    pdf.cell(0, 4, f"{col_cl} {pob_cl} CP {cp_cl}", ln=True)

    # ================= ENCABEZADO DERECHO =================
    # Título COTIZACIÓN
    pdf.set_font("helvetica", "B", 20)
    pdf.set_xy(135, 12)
    pdf.cell(60, 10, "COTIZACIÓN", ln=True, align="R")

    # Tabla de metadatos (FECHA, FOLIO, etc.)
    pdf.set_font("helvetica", "B", 8)
    x_meta = 145
    y_meta = 25
    alto_celda = 4

    etiquetas = ["FECHA", "FOLIO", "CLIENTE", "VIGENCIA", "VENDEDOR", "OC.", "OBRA"]
    valores = [fecha, folio, id_cl, "24 H", vendedor, oc, obra]

    for i in range(len(etiquetas)):
        pdf.set_xy(x_meta, y_meta + (i * alto_celda))
        pdf.set_text_color(*pdf.negro)
        pdf.cell(25, alto_celda, etiquetas[i], align="R")
        
        pdf.set_xy(x_meta + 27, y_meta + (i * alto_celda))
        
        if etiquetas[i] == "FOLIO":
            pdf.set_fill_color(*pdf.rojo_oscuro)
            pdf.set_text_color(*pdf.blanco)
            pdf.cell(25, alto_celda, valores[i], border=1, fill=True, align="C")
        elif etiquetas[i] in ["VENDEDOR", "OC.", "OBRA"]:
            pdf.set_fill_color(*pdf.blanco)
            pdf.set_text_color(*pdf.negro)
            pdf.cell(25, alto_celda, valores[i], border=0, fill=False, align="C")
        else:
            pdf.set_fill_color(*pdf.blanco)
            pdf.set_text_color(*pdf.negro)
            pdf.cell(25, alto_celda, valores[i], border=1, fill=True, align="C")

    # ================= TABLA DE PRODUCTOS =================
    y_tabla = 75
    pdf.set_xy(10, y_tabla)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(*pdf.rojo_oscuro)
    pdf.set_text_color(*pdf.blanco)

    # Anchos de columnas (Total = 190mm)
    w_col = [20, 80, 15, 10, 20, 25, 20]
    headers = ["CODIGO", "DESCRIPCIÓN", "CANT.", "UM", "PRECIO", "MONTO", "STOCK"]

    for i in range(len(headers)):
        pdf.cell(w_col[i], 5, headers[i], border=1, fill=True, align="C")
    pdf.ln()

    # Filas de productos
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*pdf.negro)
    
    y_actual = pdf.get_y()
    for prod in productos_limpios:
        cod, desc, cant, um, precio, monto, disp = prod
        x_inicio = pdf.get_x()
        y_inicio = pdf.get_y()
        
        pdf.cell(w_col[0], 5, cod, border=0, align="L")
        
        pdf.set_xy(x_inicio + w_col[0], y_inicio)
        pdf.multi_cell(w_col[1], 5, desc, border=0, align="L")
        y_max = pdf.get_y()
        
        pdf.set_xy(x_inicio + w_col[0] + w_col[1], y_inicio)
        pdf.cell(w_col[2], 5, f"{cant:g}", border=0, align="C")
        pdf.cell(w_col[3], 5, um, border=0, align="C")
        pdf.cell(w_col[4], 5, f"{precio:,.2f}", border=0, align="R")
        pdf.cell(w_col[5], 5, f"{monto:,.2f}", border=0, align="R")
        
        pdf.set_font("helvetica", "B", 8)
        if disp and disp.lower() == 'sobrepedido':
            pdf.set_text_color(*pdf.naranja_oscuro)
            texto_stock = "S / PEDIDO"
        else:
            pdf.set_text_color(*pdf.verde)
            texto_stock = "DISPONIBLE"
            
        pdf.cell(w_col[6], 5, texto_stock, border=0, align="C")
        
        pdf.set_text_color(*pdf.negro)
        pdf.set_font("helvetica", "", 8)
        
        pdf.set_y(max(y_max, y_inicio + 5))

    # Dibujar el rectángulo exterior de la tabla
    alto_caja = 130
    pdf.rect(10, y_tabla, 190, alto_caja)

    # ================= TOTALES Y CANTIDAD EN LETRA =================
    y_totales = y_tabla + alto_caja + 5
    pdf.set_xy(10, y_totales + 10)
    
    # Texto importe con letra
    pesos = int(total)
    centavos = int(round((total - pesos) * 100))
    texto_letras = num2words(pesos, lang='es').upper()
    importe_letra = f"{texto_letras} PESOS {centavos:02d}/100 M.N."
    
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(120, 5, importe_letra, ln=False, align="L")

    # Cuadro de totales
    subtotal = total / 1.16
    iva = total - subtotal

    pdf.set_font("helvetica", "B", 9)
    pdf.set_xy(140, y_totales)
    
    pdf.cell(25, 5, "SUBTOTAL", align="R")
    pdf.cell(5, 5, "$", align="C")
    pdf.cell(30, 5, f"{subtotal:,.2f}", align="R")
    pdf.ln()
    
    pdf.set_x(140)
    pdf.cell(25, 5, "IVA", align="R")
    pdf.cell(5, 5, "$", align="C")
    pdf.cell(30, 5, f"{iva:,.2f}", align="R")
    pdf.ln()
    
    pdf.set_x(140)
    pdf.set_fill_color(*pdf.rojo_oscuro)
    pdf.set_text_color(*pdf.blanco)
    pdf.cell(25, 6, "TOTAL", border=1, fill=True, align="C")
    pdf.cell(5, 6, "$", border="TB", fill=True, align="C")
    pdf.cell(30, 6, f"{total:,.2f}", border="TRB", fill=True, align="R")
    
    # ================= TÉRMINOS Y CONDICIONES =================
    pdf.set_text_color(*pdf.blanco)
    pdf.set_fill_color(*pdf.rojo_oscuro)
    y_terminos = pdf.get_y() + 10
    pdf.set_xy(10, y_terminos)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(190, 5, "TÉRMINOS Y CONDICIONES", border=1, fill=True, align="C", ln=True)

    pdf.set_text_color(*pdf.negro)
    pdf.set_font("helvetica", "", 6)
    pdf.multi_cell(190, 3, terminos, border=1, align="J")

    # ================= GUARDAR PDF CON DIÁLOGO =================
    nombre_sugerido = f"Cotizacion_{folio}.pdf"
    
    if parent_widget:
        ruta_guardado, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Guardar Cotización PDF",
            nombre_sugerido,
            "Archivos PDF (*.pdf);;Todos los archivos (*.*)"
        )
        
        if not ruta_guardado:
            return False, "Operación cancelada por el usuario"
        
        if not ruta_guardado.lower().endswith('.pdf'):
            ruta_guardado += '.pdf'
    else:
        ruta_guardado = nombre_sugerido

    try:
        pdf.output(ruta_guardado)
        
        if parent_widget:
            respuesta = QMessageBox.question(
                parent_widget,
                "PDF Generado",
                f"PDF guardado en:\n{ruta_guardado}\n\n¿Deseas abrirlo?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if respuesta == QMessageBox.Yes:
                import subprocess
                import platform
                
                if platform.system() == 'Windows':
                    os.startfile(ruta_guardado)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', ruta_guardado])
                else:
                    subprocess.run(['xdg-open', ruta_guardado])
        
        return True, ruta_guardado
    except Exception as e:
        return False, f"Error al guardar el PDF: {str(e)}"