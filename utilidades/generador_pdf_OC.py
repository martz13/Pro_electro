import os
import unicodedata
from fpdf import FPDF
from PySide6.QtWidgets import QFileDialog, QMessageBox
from base_datos.conexion import obtener_conexion
from utilidades.recursos import resource_path

def clean_text(text):
    """Convierte texto Unicode a ASCII aproximado, eliminando acentos y caracteres especiales."""
    if not isinstance(text, str):
        text = str(text)
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

class PDFOrdenCompra(FPDF):
    def __init__(self, fiscal_telefono="", fiscal_rfc="",admin_correo="admin@proelectro.mx", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=20) # Margen inferior para el footer
        
        self.fiscal_telefono = fiscal_telefono
        self.fiscal_rfc = fiscal_rfc
        self.admin_correo = admin_correo
        
        self.rojo_oc = (200, 0, 0) # Letras rojas para el título
        self.negro = (0, 0, 0)
        self.gris_texto = (100, 100, 100)
        self.gris_claro = (220, 220, 220)

    def footer(self):
        """Pie de página que se repite en todas las hojas automáticamente"""
        self.set_y(-15)
        self.set_draw_color(*self.gris_claro)
        self.line(10, self.get_y(), 200, self.get_y()) # Línea divisoria inferior
        
        self.set_y(-12)
        self.set_font("helvetica", "", 9)
        self.set_text_color(*self.gris_texto)
        
        # Telefono a la izquierda
        self.set_x(10)
        self.cell(60, 5, f"Teléfono: {self.fiscal_telefono}", 0, 0, 'L')
        
        # Correo al centro
        self.set_x(75)
        self.cell(60, 5, self.admin_correo, 0, 0, 'C')
        
        # RFC a la derecha
        self.set_x(140)
        self.cell(60, 5, f"RFC: {self.fiscal_rfc}", 0, 0, 'R')

def generar_pdf_orden_compra(folio_oc, parent_widget=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # 1. Obtener datos de la Orden de Compra y Proveedor
    query_oc = """
        SELECT o.id_orden, o.folio, o.fecha, o.proveedor_id, o.representante, o.referencia, o.direccion_envio, o.telefono_envio, o.monto_total,
               p.nombre_empresa, p.direccion
        FROM ordenes_compra o
        JOIN proveedores p ON o.proveedor_id = p.id_prov
        WHERE o.folio = ?
    """
    cursor.execute(query_oc, (folio_oc,))
    oc_data = cursor.fetchone()
    
    if not oc_data:
        conexion.close()
        return False, "No se encontró la Orden de Compra."

    id_ord, folio, fecha, id_prov, rep, ref, dir_envio, tel_envio, total, prov_nombre, prov_dir = oc_data

    # 2. Obtener datos fiscales
    cursor.execute("SELECT nombre_empresa, ubicacion, telefono, rfc FROM datos_fiscales WHERE id=1")
    fiscal_data = cursor.fetchone()
    empresa_nom, empresa_ubi, fiscal_tel, fiscal_rfc = fiscal_data if fiscal_data else ("-", "-", "-", "-")

    # Buscar el correo del representante (super admin) usando su nombre completo
    cursor.execute("SELECT correo FROM usuarios WHERE nombre_completo = ? AND rol = 'Super admin'", (rep,))
    admin_correo_result = cursor.fetchone()
    admin_correo = admin_correo_result[0] if admin_correo_result else "admin@proelectro.mx"
    admin_correo = clean_text(admin_correo)

    # 3. Obtener detalle de productos (Respetando el orden de inserción)
    cursor.execute("SELECT codigo_producto, descripcion, cantidad, um, precio_unitario, monto FROM ordenes_compra_detalle WHERE orden_id=? ORDER BY id ASC", (id_ord,))
    productos = cursor.fetchall()
    conexion.close()

    # Limpieza de textos
    empresa_nom = clean_text(empresa_nom)
    empresa_ubi = clean_text(empresa_ubi)
    fiscal_tel = clean_text(fiscal_tel)
    fiscal_rfc = clean_text(fiscal_rfc)
    
    prov_nombre = clean_text(prov_nombre)
    prov_dir = clean_text(prov_dir if prov_dir else "N/D")
    dir_envio = clean_text(dir_envio if dir_envio else "N/D")
    tel_envio = clean_text(tel_envio if tel_envio else "N/D")
    rep = clean_text(rep)
    ref = clean_text(ref if ref else "N/D")

    # --- INICIO DEL DISEÑO DEL PDF ---
    pdf = PDFOrdenCompra(fiscal_telefono=fiscal_tel, fiscal_rfc=fiscal_rfc,admin_correo=admin_correo, orientation="P", unit="mm", format="A4")
    pdf.add_page()
    
    # ================= LOGO =================
    ruta_logo = resource_path("recursos/logo.png")
    if os.path.exists(ruta_logo):
        # 🌟 AJUSTE DE LOGO:
        # y = 8 (qué tan arriba/abajo está)
        # w = 35 (qué tan ancho es)
        pdf.image(ruta_logo, x=10, y=0, w=30) 
    
    # Línea debajo del logo
    pdf.set_draw_color(*pdf.gris_claro)
    pdf.line(10, 25, 200, 25)

    # ================= DATOS DE TU EMPRESA =================
    pdf.set_xy(10, 28)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*pdf.negro)
    pdf.cell(100, 5, empresa_nom, ln=True)
    
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*pdf.gris_texto)
    pdf.cell(100, 5, empresa_ubi, ln=True)

    # ================= DIRECCIÓN ENVÍO Y PROVEEDOR =================
    y_bloque_direcciones = 45
    
    # Izquierda: Dirección de envío
    pdf.set_xy(10, y_bloque_direcciones)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*pdf.gris_texto)
    pdf.cell(90, 5, "Dirección de envío", ln=True)
    
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*pdf.negro)
    pdf.multi_cell(90, 4, dir_envio)

    # Guardar la posición Y después de la dirección
    y_despues_direccion = pdf.get_y()

    pdf.set_font("helvetica", "B", 9)
    pdf.set_x(10)  # Asegurar que estamos en X=10
    pdf.cell(90, 6, f"Tel: {tel_envio}", ln=True)
    y_fin_envio = pdf.get_y()

    # Derecha: Proveedor
    pdf.set_xy(110, y_bloque_direcciones)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(*pdf.negro)
    pdf.cell(90, 5, prov_nombre, ln=True)
    
    pdf.set_x(110)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*pdf.gris_texto)
    pdf.multi_cell(90, 4, prov_dir)
    y_fin_prov = pdf.get_y()

    # ================= TÍTULO ROJO Y DATOS HORIZONTALES =================
    # Calculamos para que quede debajo del teléfono de envío y de la info del proveedor
    y_pedido = max(y_fin_envio, y_fin_prov) + 8

    # Título
    pdf.set_xy(10, y_pedido)
    pdf.set_font("helvetica", "", 18)
    pdf.set_text_color(*pdf.rojo_oc) # Letras rojas, sin fondo
    pdf.cell(190, 8, f"Pedido de compra #{folio}", ln=True)

    y_datos_horiz = pdf.get_y() + 4
    
    # Etiquetas (Representante, Referencia, Fecha)
    pdf.set_xy(10, y_datos_horiz)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*pdf.gris_texto)
    pdf.cell(63, 4, "Representante de compra:")
    pdf.cell(63, 4, "Referencia del pedido:")
    pdf.cell(64, 4, "Fecha de orden:")
    pdf.ln()
    
    # Valores
    pdf.set_x(10)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*pdf.negro)
    pdf.cell(63, 5, rep)
    pdf.cell(63, 5, ref)
    pdf.cell(64, 5, fecha)
    pdf.ln(10)

    # ================= TABLA DE PRODUCTOS =================
    y_tabla = pdf.get_y()
    w_col = [30, 80, 20, 15, 20, 25] # Total: 190mm
    headers = ["CÓDIGO", "DESCRIPCIÓN", "CANTIDAD", "UM", "COMPRA", "IMPORTE"]

    def dibujar_encabezados():
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(*pdf.gris_texto)
        pdf.set_draw_color(*pdf.gris_claro)
        pdf.set_x(10)
        # Solo borde inferior ("B"), SIN fondo (fill=False)
        for i in range(len(headers)):
            pdf.cell(w_col[i], 6, headers[i], border="B", fill=False, align="L" if i <= 1 else "C" if i <= 3 else "R")
        pdf.ln()

    dibujar_encabezados()

    for prod in productos:
        cod, desc, cant, um, precio, monto = prod
        desc = clean_text(desc)
        
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(*pdf.negro)
        
        lineas = 0
        for parrafo in desc.split('\n'):
            ancho_texto = pdf.get_string_width(parrafo)
            lineas += max(1, int(ancho_texto / (w_col[1] - 3)) + 1)
        alto_fila = max(6, lineas * 4) 
        
        # Salto de página
        if pdf.get_y() + alto_fila > 260:
            pdf.add_page()
            dibujar_encabezados()
            
        x_inicio = 10
        y_inicio = pdf.get_y()
        
        # SIN bordes para los artículos (border=0)
        pdf.set_xy(x_inicio, y_inicio + 1) # Ligero margen superior para que no pegue
        pdf.cell(w_col[0], 4, cod, border=0, align="L")
        
        pdf.set_xy(x_inicio + w_col[0], y_inicio + 1)
        pdf.multi_cell(w_col[1], 4, desc, border=0, align="L")
        
        pdf.set_xy(x_inicio + w_col[0] + w_col[1], y_inicio + 1)
        pdf.cell(w_col[2], 4, f"{cant:g}", border=0, align="C")
        pdf.cell(w_col[3], 4, clean_text(um), border=0, align="C")
        pdf.cell(w_col[4], 4, f"${precio:,.2f}", border=0, align="R")
        pdf.cell(w_col[5], 4, f"${monto:,.2f}", border=0, align="R")
        
        pdf.set_y(y_inicio + alto_fila)

    # Una línea sutil al final de la tabla para cerrarla
    pdf.set_draw_color(*pdf.gris_claro)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # ================= TOTALES =================
    if pdf.get_y() + 30 > 270:
        pdf.add_page()
    
    subtotal = total / 1.16
    iva = total - subtotal

    y_totales = pdf.get_y()
    
    # Importe base
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*pdf.gris_texto)
    pdf.set_xy(135, y_totales)
    pdf.cell(30, 6, "Importe base", align="R")
    
    pdf.set_text_color(*pdf.negro)
    pdf.cell(35, 6, f"${subtotal:,.2f}", align="R", ln=True)
    
    # IVA
    pdf.set_x(135)
    pdf.set_text_color(*pdf.gris_texto)
    pdf.cell(30, 6, "IVA (16%)", align="R")
    
    pdf.set_text_color(*pdf.negro)
    pdf.cell(35, 6, f"${iva:,.2f}", align="R", ln=True)
    
    # Total
    pdf.set_x(135)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(30, 8, "Total", align="R")
    pdf.cell(35, 8, f"${total:,.2f}", align="R", ln=True)

    # ================= GUARDAR PDF =================
    nombre_sugerido = f"Pedido_Compra_{folio}.pdf"
    
    if parent_widget:
        ruta_guardado, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Guardar Pedido de Compra PDF",
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
                f"El Pedido de Compra se guardó en:\n{ruta_guardado}\n\n¿Deseas abrirlo?",
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