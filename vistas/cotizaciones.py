from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QHeaderView, QDialog, QMessageBox, 
                               QGridLayout, QComboBox, QDateEdit, QDoubleSpinBox, QGroupBox,
                               QScrollArea, QFrame, QSizePolicy, QSpinBox, QApplication)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor
import requests

# --- NUEVAS IMPORTACIONES ONLINE-FIRST ---
from base_datos.conexion import obtener_conexion, operacion_crud_nube, forzar_descarga_nube
from utilidades.generador_pdf import generar_pdf_cotizacion

# ==========================================
# 0. DIÁLOGOS PARA SELECCIÓN (PRODUCTOS Y CLIENTES)
# ==========================================
class DialogoSeleccionarProducto(QDialog):
    def __init__(self, parent=None, resultados=[]):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Producto")
        self.setFixedSize(600, 350)
        self.setModal(True)
        self.producto_seleccionado = None
        self.resultados = resultados

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        lbl_info = QLabel("Se encontraron múltiples coincidencias. Selecciona el producto correcto:")
        lbl_info.setObjectName("labelTitulo")
        layout.addWidget(lbl_info)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["Código", "Descripción"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:!active { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla)

        self.tabla.setRowCount(len(resultados))
        for fila, prod in enumerate(resultados):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(prod[0])))
            item_desc = QTableWidgetItem(str(prod[1]))
            item_desc.setToolTip(str(prod[1]))
            self.tabla.setItem(fila, 1, item_desc)

        btn_seleccionar = QPushButton("Seleccionar Producto")
        btn_seleccionar.setObjectName("botonPrincipal")
        btn_seleccionar.setMinimumHeight(45)
        btn_seleccionar.clicked.connect(self.seleccionar)
        layout.addWidget(btn_seleccionar)

    def seleccionar(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.producto_seleccionado = self.resultados[fila]
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Por favor, selecciona un producto de la lista.")

class DialogoSeleccionarCliente(QDialog):
    def __init__(self, parent=None, resultados=[]):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Cliente")
        self.setFixedSize(600, 350)
        self.setModal(True)
        self.cliente_seleccionado = None
        self.resultados = resultados

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        lbl_info = QLabel("Se encontraron múltiples coincidencias. Selecciona el cliente correcto:")
        lbl_info.setObjectName("labelTitulo")
        layout.addWidget(lbl_info)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre Completo", "RFC"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:!active { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla)

        self.tabla.setRowCount(len(resultados))
        for fila, cli in enumerate(resultados):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(cli[0])))
            self.tabla.setItem(fila, 1, QTableWidgetItem(str(cli[1])))
            self.tabla.setItem(fila, 2, QTableWidgetItem(str(cli[2])))

        btn_seleccionar = QPushButton("Seleccionar Cliente")
        btn_seleccionar.setObjectName("botonPrincipal")
        btn_seleccionar.setMinimumHeight(45)
        btn_seleccionar.clicked.connect(self.seleccionar)
        layout.addWidget(btn_seleccionar)

    def seleccionar(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.cliente_seleccionado = self.resultados[fila]
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Por favor, selecciona un cliente de la lista.")

# ==========================================
# 1. DIÁLOGO PARA CREAR/EDITAR COTIZACIÓN
# ==========================================
class DialogoCotizacion(QDialog):
    def __init__(self, parent=None, cotizacion_id=None):
        super().__init__(parent)
        self.cotizacion_id = cotizacion_id
        self.setWindowTitle("Nueva Cotización" if not cotizacion_id else f"Editar Cotización - CT{cotizacion_id:03d}")
        
        self.setMinimumSize(1000, 700) 
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setWindowState(Qt.WindowMaximized)
        self.setModal(True)
        
        self.cliente_seleccionado = None

        layout_base = QVBoxLayout(self)
        layout_base.setContentsMargins(0, 0, 0, 0) 

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) 
        scroll_area.setFrameShape(QFrame.NoFrame) 
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenedor_scroll = QWidget()
        contenedor_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.layout_principal = QVBoxLayout(contenedor_scroll)
        self.layout_principal.setContentsMargins(20, 20, 20, 20) 
        self.layout_principal.setSpacing(20) 

        self.grupo_encabezado = self.crear_encabezado()
        self.grupo_detalle = self.crear_detalle_productos()
        self.layout_totales = self.crear_pie_totales()

        self.layout_principal.addWidget(self.grupo_encabezado)
        self.layout_principal.addWidget(self.grupo_detalle)
        self.layout_principal.addLayout(self.layout_totales)

        scroll_area.setWidget(contenedor_scroll)
        layout_base.addWidget(scroll_area)

        self.cargar_vendedores()

        if self.cotizacion_id:
            self.cargar_cotizacion_existente()
        else:
            self.generar_folio()

    def crear_encabezado(self):
        grupo = QGroupBox("1. Datos Generales")
        grupo.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 16px; border: 1px solid #CBD5E0; border-radius: 6px; margin-top: 15px; } 
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2B6CB0; }
        """)
        grid = QGridLayout(grupo)
        grid.setContentsMargins(25, 35, 25, 25)
        grid.setSpacing(20)

        lbl_cliente = QLabel("Buscar Cliente:"); lbl_cliente.setObjectName("labelTitulo")
        lbl_fecha = QLabel("Fecha:"); lbl_fecha.setObjectName("labelTitulo")
        lbl_folio = QLabel("Folio (Auto):"); lbl_folio.setObjectName("labelTitulo")
        lbl_vendedor = QLabel("Vendedor:"); lbl_vendedor.setObjectName("labelTitulo")
        lbl_oc = QLabel("OC (Orden Compra):"); lbl_oc.setObjectName("labelTitulo")
        lbl_obra = QLabel("Obra:"); lbl_obra.setObjectName("labelTitulo")

        grid.addWidget(lbl_cliente, 0, 0)
        
        layout_buscador_cliente = QHBoxLayout()
        self.input_buscar_cliente = QLineEdit()
        self.input_buscar_cliente.setPlaceholderText("🔍 Buscar por ID o Nombre y presionar Enter...")
        self.input_buscar_cliente.setMinimumHeight(42)
        self.input_buscar_cliente.returnPressed.connect(self.buscar_cliente)
        layout_buscador_cliente.addWidget(self.input_buscar_cliente)

        btn_buscar_cliente = QPushButton("Buscar")
        btn_buscar_cliente.setObjectName("botonAgregar")
        btn_buscar_cliente.setMinimumHeight(42)
        btn_buscar_cliente.clicked.connect(self.buscar_cliente)
        layout_buscador_cliente.addWidget(btn_buscar_cliente)

        grid.addLayout(layout_buscador_cliente, 0, 1, 1, 3)

        self.lbl_info_cliente = QLabel("Nombre: -\nRFC: -\nDirección: -")
        self.lbl_info_cliente.setStyleSheet("color: #4A5568; font-size: 14px; background-color: #F7FAFC; padding: 12px; border-radius: 6px; border: 1px dashed #CBD5E0;")
        grid.addWidget(self.lbl_info_cliente, 1, 0, 1, 4)

        grid.addWidget(lbl_fecha, 2, 0)
        self.input_fecha = QDateEdit()
        self.input_fecha.setMinimumHeight(42)
        self.input_fecha.setCalendarPopup(True)
        self.input_fecha.setDate(QDate.currentDate())
        grid.addWidget(self.input_fecha, 2, 1)

        grid.addWidget(lbl_folio, 2, 2)
        self.input_folio = QLineEdit()
        self.input_folio.setMinimumHeight(42)
        self.input_folio.setReadOnly(True)
        self.input_folio.setStyleSheet("background-color: #E2E8F0; color: #4A5568; font-weight: bold;")
        grid.addWidget(self.input_folio, 2, 3)

        grid.addWidget(lbl_vendedor, 3, 0)
        self.combo_vendedor = QComboBox()
        self.combo_vendedor.setMinimumHeight(42)
        grid.addWidget(self.combo_vendedor, 3, 1)

        grid.addWidget(lbl_oc, 3, 2)
        self.input_oc = QLineEdit()
        self.input_oc.setMinimumHeight(42)
        grid.addWidget(self.input_oc, 3, 3)

        grid.addWidget(lbl_obra, 4, 0)
        self.input_obra = QLineEdit()
        self.input_obra.setMinimumHeight(42)
        grid.addWidget(self.input_obra, 4, 1, 1, 3)

        return grupo

    def crear_detalle_productos(self):
        grupo = QGroupBox("2. Detalle de Productos")
        grupo.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 16px; border: 1px solid #CBD5E0; border-radius: 6px; margin-top: 15px; } 
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2B6CB0; }
        """)
        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(25, 35, 25, 25)
        layout.setSpacing(15)

        layout_buscador = QHBoxLayout()
        self.input_buscar_prod = QLineEdit()
        self.input_buscar_prod.setMinimumHeight(45)
        self.input_buscar_prod.setPlaceholderText("🔍 Buscar producto por Código o Descripción y presionar Enter...")
        self.input_buscar_prod.returnPressed.connect(self.buscar_y_agregar_producto) 
        layout_buscador.addWidget(self.input_buscar_prod)

        btn_agregar_prod = QPushButton("Buscar / Agregar")
        btn_agregar_prod.setObjectName("botonAgregar")
        btn_agregar_prod.setMinimumHeight(45)
        btn_agregar_prod.setMinimumWidth(180)
        btn_agregar_prod.clicked.connect(self.buscar_y_agregar_producto)
        layout_buscador.addWidget(btn_agregar_prod)
        layout.addLayout(layout_buscador)

        self.tabla_prod = QTableWidget()
        self.tabla_prod.setMinimumHeight(500) 
        
        columnas = ["Código", "Descripción", "Stock", "Cantidad", "UM", "Precio Unitario", "Monto", "Quitar", "Disponibilidad"]
        self.tabla_prod.setColumnCount(len(columnas))
        self.tabla_prod.setHorizontalHeaderLabels(columnas)
        
        self.tabla_prod.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) 
        self.tabla_prod.setColumnWidth(0, 150) 
        self.tabla_prod.setColumnWidth(2, 80)
        self.tabla_prod.setColumnWidth(3, 110)
        self.tabla_prod.setColumnWidth(4, 80)
        self.tabla_prod.setColumnWidth(5, 120)
        self.tabla_prod.setColumnWidth(6, 120)
        self.tabla_prod.setColumnWidth(7, 100)
        self.tabla_prod.setColumnWidth(8, 130)
        
        self.tabla_prod.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_prod.setAlternatingRowColors(True)
        self.tabla_prod.verticalHeader().setVisible(False)
        self.tabla_prod.verticalHeader().setDefaultSectionSize(60) 
        self.tabla_prod.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; font-size: 15px; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:!active { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla_prod)

        return grupo

    def crear_pie_totales(self):
        layout_totales = QHBoxLayout()
        layout_totales.setContentsMargins(10, 10, 10, 10)
        
        lbl_estado = QLabel("Estado:"); lbl_estado.setObjectName("labelTitulo")
        layout_totales.addWidget(lbl_estado)
        
        self.combo_estado = QComboBox()
        self.combo_estado.setMinimumHeight(45)
        self.combo_estado.setMinimumWidth(180)
        self.combo_estado.addItems(["Pendiente", "Aceptada", "Rechazada"])
        layout_totales.addWidget(self.combo_estado)
        
        layout_totales.addStretch()

        self.lbl_subtotal = QLabel("Subtotal: $0.00")
        self.lbl_iva = QLabel("IVA (16%): $0.00")
        self.lbl_total = QLabel("Total: $0.00")
        
        self.lbl_subtotal.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A5568;")
        self.lbl_iva.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A5568;")
        self.lbl_total.setStyleSheet("font-size: 24px; font-weight: bold; color: #2B6CB0; background-color: #EBF8FF; padding: 10px 20px; border-radius: 6px;")

        layout_totales.addWidget(self.lbl_subtotal)
        layout_totales.addSpacing(30)
        layout_totales.addWidget(self.lbl_iva)
        layout_totales.addSpacing(30)
        layout_totales.addWidget(self.lbl_total)

        self.btn_guardar = QPushButton("Guardar Cotización")
        self.btn_guardar.setObjectName("botonPrincipal")
        self.btn_guardar.setMinimumHeight(55) 
        self.btn_guardar.setMinimumWidth(250)
        self.btn_guardar.clicked.connect(self.guardar_cotizacion)
        
        layout_totales.addSpacing(40)
        layout_totales.addWidget(self.btn_guardar)

        return layout_totales

    # ========================================================
    # FUNCIONES LÓGICAS
    # ========================================================
    def buscar_cliente(self):
        texto = self.input_buscar_cliente.text().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Ingresa un ID o Nombre para buscar al cliente.")
            return

        filtro = f"%{texto}%"
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id_cliente, nombre_completo, rfc, direccion, telefono FROM clientes WHERE id_cliente LIKE ? OR nombre_completo LIKE ?", (filtro, filtro))
        resultados = cursor.fetchall()
        conexion.close()

        if not resultados:
            QMessageBox.warning(self, "Sin resultados", "No se encontró ningún cliente.")
        elif len(resultados) == 1:
            self.set_cliente_seleccionado(resultados[0])
        else:
            dialogo = DialogoSeleccionarCliente(self, resultados)
            if dialogo.exec() and dialogo.cliente_seleccionado:
                self.set_cliente_seleccionado(dialogo.cliente_seleccionado)

    def set_cliente_seleccionado(self, datos):
        self.cliente_seleccionado = datos
        self.input_buscar_cliente.setText(datos[1]) 
        self.lbl_info_cliente.setText(f"Nombre: {datos[1]} | RFC: {datos[2]}\nDirección: {datos[3]} | Tel: {datos[4]}")

    def cargar_vendedores(self):
        self.combo_vendedor.clear()
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_completo FROM usuarios WHERE rol IN ('Vendedor', 'Super admin') ORDER BY nombre_completo")
        for uid, nombre in cursor.fetchall():
            self.combo_vendedor.addItem(nombre, userData=uid)
        conexion.close()
        if self.combo_vendedor.count() == 0:
            self.combo_vendedor.addItem("No hay vendedores registrados")

    def generar_folio(self):
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT MAX(id_cotizacion) FROM cotizaciones")
        max_id = cursor.fetchone()[0]
        conexion.close()
        num = (max_id + 1) if max_id else 1
        self.input_folio.setText(f"F-{num:05d}")

    def buscar_y_agregar_producto(self):
        texto = self.input_buscar_prod.text().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Ingresa un código o descripción para buscar.")
            return

        filtro = f"%{texto}%"
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT codigo_producto, descripcion, stock, um, precio_venta FROM inventario WHERE codigo_producto LIKE ? OR descripcion LIKE ?", (filtro, filtro))
        resultados = cursor.fetchall()
        conexion.close()

        if not resultados:
            QMessageBox.warning(self, "Sin resultados", "No se encontró ningún producto con esa búsqueda.")
        elif len(resultados) == 1:
            self.agregar_producto_a_tabla(resultados[0])
            self.input_buscar_prod.clear()
        else:
            dialogo = DialogoSeleccionarProducto(self, resultados)
            if dialogo.exec() and dialogo.producto_seleccionado:
                self.agregar_producto_a_tabla(dialogo.producto_seleccionado)
                self.input_buscar_prod.clear()

    def agregar_producto_a_tabla(self, datos_prod, cantidad_inicial=1.0):
        codigo, desc, stock_inv, um, precio = datos_prod[0], datos_prod[1], datos_prod[2], datos_prod[3], float(datos_prod[4])
        
        for fila in range(self.tabla_prod.rowCount()):
            if self.tabla_prod.item(fila, 0).text() == codigo:
                spin = self.tabla_prod.cellWidget(fila, 3) 
                spin.setValue(spin.value() + float(cantidad_inicial))
                return

        fila = self.tabla_prod.rowCount()
        self.tabla_prod.insertRow(fila)

        items = [
            QTableWidgetItem(str(codigo)),
            QTableWidgetItem(str(desc)),
            QTableWidgetItem(str(stock_inv)), 
            None,  
            QTableWidgetItem(str(um)),
            QTableWidgetItem(f"{precio:.2f}"),
            QTableWidgetItem("0.00"),
            None,  
            None   
        ]

        items[1].setToolTip(str(desc))

        for col, item in enumerate(items):
            if item:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col in [0, 2, 4, 5, 6] else Qt.AlignLeft))
                self.tabla_prod.setItem(fila, col, item)

        spin_cantidad = QSpinBox() 
        spin_cantidad.setMinimumHeight(40) 
        spin_cantidad.setStyleSheet("font-size: 15px;")
        spin_cantidad.setRange(1, 999999)  
        spin_cantidad.setValue(int(cantidad_inicial))  
        spin_cantidad.setSingleStep(1)  
        spin_cantidad.valueChanged.connect(lambda val, f=fila: self.actualizar_fila_y_totales(f))
        self.tabla_prod.setCellWidget(fila, 3, spin_cantidad) 

        btn_quitar = QPushButton("❌ Quitar")
        btn_quitar.setObjectName("botonEliminar")
        btn_quitar.setMinimumHeight(35)
        btn_quitar.clicked.connect(lambda checked, f=fila: self.eliminar_fila(f))
        widget_btn = QWidget()
        layout_btn = QHBoxLayout(widget_btn)
        layout_btn.setContentsMargins(10, 5, 10, 5)
        layout_btn.addWidget(btn_quitar)
        self.tabla_prod.setCellWidget(fila, 7, widget_btn) 

        combo_disponibilidad = QComboBox()
        combo_disponibilidad.addItems(["Disponible", "Sobrepedido"])
        combo_disponibilidad.setCurrentText("Disponible")
        combo_disponibilidad.setMinimumHeight(35)
        self.tabla_prod.setCellWidget(fila, 8, combo_disponibilidad) 

        self.actualizar_fila_y_totales(fila)

    def actualizar_fila_y_totales(self, fila):
        try:
            precio = float(self.tabla_prod.item(fila, 5).text()) 
            cantidad = self.tabla_prod.cellWidget(fila, 3).value() 
            monto = precio * cantidad
            self.tabla_prod.item(fila, 6).setText(f"{monto:.2f}") 
            self.calcular_totales()
        except Exception:
            pass

    def eliminar_fila(self, fila):
        self.tabla_prod.removeRow(fila)
        self.calcular_totales()
        for i in range(self.tabla_prod.rowCount()):
            spin = self.tabla_prod.cellWidget(i, 3) 
            spin.valueChanged.disconnect()
            spin.valueChanged.connect(lambda val, f=i: self.actualizar_fila_y_totales(f))
            
            btn_widget = self.tabla_prod.cellWidget(i, 7) 
            btn = btn_widget.layout().itemAt(0).widget()
            btn.clicked.disconnect()
            btn.clicked.connect(lambda checked, f=i: self.eliminar_fila(f))

    def calcular_totales(self):
        subtotal = 0.0
        for fila in range(self.tabla_prod.rowCount()):
            monto_str = self.tabla_prod.item(fila, 6).text() 
            subtotal += float(monto_str) if monto_str else 0.0
        
        iva = subtotal * 0.16
        total = subtotal + iva

        self.lbl_subtotal.setText(f"Subtotal: ${subtotal:,.2f}")
        self.lbl_iva.setText(f"IVA (16%): ${iva:,.2f}")
        self.lbl_total.setText(f"Total: ${total:,.2f}")
        self.monto_total_guardar = total

    def guardar_cotizacion(self):
        if self.tabla_prod.rowCount() == 0:
            QMessageBox.warning(self, "Error", "Debes agregar al menos un producto.")
            return
        if not self.cliente_seleccionado:
            QMessageBox.warning(self, "Error", "Debes seleccionar un cliente.")
            return

        fecha = self.input_fecha.date().toString("yyyy-MM-dd")
        cliente_id = self.cliente_seleccionado[0]
        vendedor = self.combo_vendedor.currentText() 
        oc = self.input_oc.text().strip()
        obra = self.input_obra.text().strip()
        estado = self.combo_estado.currentText()

        # 1. VERIFICAR CONEXIÓN A INTERNET
        hay_internet = True
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            hay_internet = False

        if not hay_internet and self.cotizacion_id:
            QMessageBox.warning(self, "Sin Conexión", "No puedes editar cotizaciones existentes sin conexión a internet. Solo puedes crear nuevas offline.")
            return

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        try:
            if hay_internet:
                # --- REGLA 2: Prevención de Colisiones ---
                try:
                    resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=cotizaciones", timeout=3)
                    if resp.status_code == 200:
                        total_nube = resp.json().get("total", 0)
                        cursor.execute("SELECT COUNT(*) FROM cotizaciones")
                        total_local = cursor.fetchone()[0]
                        if total_nube > total_local:
                            QMessageBox.information(self, "Sincronizando...", "Se detectaron nuevos datos en la nube. Actualizando sistema...")
                            forzar_descarga_nube()
                except:
                    pass

                # --- REGLA 3: ONLINE-FIRST (NUBE PRIMERO) ---
                folio = self.input_folio.text()
                if self.cotizacion_id:
                    # UPDATE
                    datos_cotizacion = {
                        "fecha": fecha, "cliente_id": cliente_id, "vendedor": vendedor,
                        "oc": oc, "obra": obra, "estado": estado, "monto_total": self.monto_total_guardar
                    }
                    exito, msj = operacion_crud_nube('cotizaciones', 'UPDATE', datos_cotizacion, self.cotizacion_id)
                    if not exito: raise Exception(f"Error en nube (Cotización): {msj}")

                    # Borrar detalles viejos online y localmente
                    cursor.execute("SELECT id FROM cotizaciones_detalle WHERE cotizacion_id=?", (self.cotizacion_id,))
                    viejos = cursor.fetchall()
                    for v in viejos:
                        operacion_crud_nube('cotizaciones_detalle', 'DELETE', registro_id=v[0])
                    cursor.execute("DELETE FROM cotizaciones_detalle WHERE cotizacion_id=?", (self.cotizacion_id,))
                    
                    # Actualizar encabezado local
                    cursor.execute("""
                        UPDATE cotizaciones SET fecha=?, cliente_id=?, vendedor=?, oc=?, obra=?, estado=?, monto_total=?
                        WHERE id_cotizacion=?
                    """, (fecha, cliente_id, vendedor, oc, obra, estado, self.monto_total_guardar, self.cotizacion_id))
                    
                    id_cotizacion_actual = self.cotizacion_id
                else:
                    # INSERT
                    datos_cotizacion = {
                        "folio": folio, "fecha": fecha, "cliente_id": cliente_id, "vendedor": vendedor,
                        "oc": oc, "obra": obra, "estado": estado, "monto_total": self.monto_total_guardar
                    }
                    exito, nuevo_id = operacion_crud_nube('cotizaciones', 'INSERT', datos_cotizacion)
                    if not exito: raise Exception(f"Error en nube (Cotización): {nuevo_id}")
                    
                    id_cotizacion_actual = nuevo_id
                    
                    cursor.execute("""
                        INSERT INTO cotizaciones (id_cotizacion, folio, fecha, cliente_id, vendedor, oc, obra, estado, monto_total)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id_cotizacion_actual, folio, fecha, cliente_id, vendedor, oc, obra, estado, self.monto_total_guardar))

                # Insertamos los detalles nuevos en nube y local
                for fila in range(self.tabla_prod.rowCount()):
                    codigo = self.tabla_prod.item(fila, 0).text()
                    desc = self.tabla_prod.item(fila, 1).text()
                    cantidad = self.tabla_prod.cellWidget(fila, 3).value()
                    um = self.tabla_prod.item(fila, 4).text()
                    precio_u = float(self.tabla_prod.item(fila, 5).text())
                    monto = float(self.tabla_prod.item(fila, 6).text())
                    disponibilidad = self.tabla_prod.cellWidget(fila, 8).currentText()

                    datos_detalle = {
                        "cotizacion_id": id_cotizacion_actual, "codigo_producto": codigo, "descripcion": desc,
                        "cantidad": cantidad, "um": um, "precio_unitario": precio_u, "monto": monto, "disponibilidad": disponibilidad
                    }
                    
                    exito_det, id_det_nube = operacion_crud_nube('cotizaciones_detalle', 'INSERT', datos_detalle)
                    if not exito_det: raise Exception(f"Error en nube (Detalle): {id_det_nube}")

                    cursor.execute("""
                        INSERT INTO cotizaciones_detalle (id, cotizacion_id, codigo_producto, descripcion, cantidad, um, precio_unitario, monto, disponibilidad)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id_det_nube, id_cotizacion_actual, codigo, desc, cantidad, um, precio_u, monto, disponibilidad))

                conexion.commit()
                QMessageBox.information(self, "Éxito", "Cotización guardada y sincronizada correctamente en la nube.")

            else:
                # --- FLUJO OFFLINE (TABLAS EXT) ---
                cursor.execute("SELECT MAX(id_cotizacion) FROM cotizaciones_ext")
                max_id_ext = cursor.fetchone()[0]
                num_ext = (max_id_ext + 1) if max_id_ext else 1
                folio_ext = f"CTE{num_ext:03d}" 

                cursor.execute("""
                    INSERT INTO cotizaciones_ext (folio, fecha, cliente_id, vendedor, oc, obra, estado, monto_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (folio_ext, fecha, cliente_id, vendedor, oc, obra, estado, self.monto_total_guardar))
                
                id_cot_ext = cursor.lastrowid

                for fila in range(self.tabla_prod.rowCount()):
                    codigo = self.tabla_prod.item(fila, 0).text()
                    desc = self.tabla_prod.item(fila, 1).text()
                    cantidad = self.tabla_prod.cellWidget(fila, 3).value() 
                    um = self.tabla_prod.item(fila, 4).text() 
                    precio_u = float(self.tabla_prod.item(fila, 5).text()) 
                    monto = float(self.tabla_prod.item(fila, 6).text()) 
                    disponibilidad = self.tabla_prod.cellWidget(fila, 8).currentText() 

                    cursor.execute("""
                        INSERT INTO cotizaciones_detalle_ext (cotizacion_id, codigo_producto, descripcion, cantidad, um, precio_unitario, monto, disponibilidad)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id_cot_ext, codigo, desc, cantidad, um, precio_u, monto, disponibilidad))

                conexion.commit()
                QMessageBox.warning(self, "Modo Offline", f"No hay conexión a internet.\nLa cotización fue guardada localmente como {folio_ext}.\nRecuerda subirla cuando tengas internet.")

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al guardar:\n{str(e)}")
        finally:
            conexion.close()

    def cargar_cotizacion_existente(self):
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("SELECT folio, fecha, cliente_id, vendedor, oc, obra, estado FROM cotizaciones WHERE id_cotizacion=?", (self.cotizacion_id,))
        encabezado = cursor.fetchone()
        
        if encabezado:
            self.input_folio.setText(encabezado[0])
            self.input_fecha.setDate(QDate.fromString(encabezado[1], "yyyy-MM-dd"))
            
            cursor.execute("SELECT id_cliente, nombre_completo, rfc, direccion, telefono FROM clientes WHERE id_cliente=?", (encabezado[2],))
            cliente = cursor.fetchone()
            if cliente:
                self.set_cliente_seleccionado(cliente)
            
            vendedor_nombre = encabezado[3]
            index = self.combo_vendedor.findText(vendedor_nombre)
            if index >= 0:
                self.combo_vendedor.setCurrentIndex(index)
            
            self.input_oc.setText(encabezado[4] if encabezado[4] else "")
            self.input_obra.setText(encabezado[5] if encabezado[5] else "")
            self.combo_estado.setCurrentText(encabezado[6])

        # 🌟 SOLUCIÓN ANTI-DUPLICADOS (AUTO-REPARACIÓN) 🌟
        # Agregamos "GROUP BY d.codigo_producto" para ignorar clones locales
        # creados por errores en la sincronización de la base de datos.
        query_detalle = """
            SELECT d.codigo_producto, d.descripcion, d.cantidad, d.um, d.precio_unitario, d.disponibilidad, IFNULL(i.stock, 'N/D')
            FROM cotizaciones_detalle d
            LEFT JOIN inventario i ON d.codigo_producto = i.codigo_producto
            WHERE d.cotizacion_id=?
            GROUP BY d.codigo_producto 
        """
        cursor.execute(query_detalle, (self.cotizacion_id,))
        detalles = cursor.fetchall()
        
        for det in detalles:
            cod, desc, cant_guardada, um, precio, disp, stock_inv = det
            
            datos_prod = (cod, desc, stock_inv, um, precio)
            self.agregar_producto_a_tabla(datos_prod, cant_guardada)
            
            fila = self.tabla_prod.rowCount() - 1
            combo = self.tabla_prod.cellWidget(fila, 8) 
            if combo:
                combo.setCurrentText(disp)

        conexion.close()
# ==========================================
# 2. VISTA PRINCIPAL (HISTORIAL)
# ==========================================
class VistaCotizaciones(QWidget):
    
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1200)
        self.viendo_externas = False 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        self.titulo = QLabel("📑 Historial de Cotizaciones")
        self.titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍 Buscar por ID, Folio o Cliente...")
        self.input_buscar.setFixedWidth(350)
        self.input_buscar.setMinimumHeight(40)
        self.input_buscar.textChanged.connect(self.cargar_datos)

        self.btn_externas = QPushButton("⚠️ Cotizaciones Externas")
        self.btn_externas.setStyleSheet("background-color: #DD6B20; color: white; font-weight: bold;")
        self.btn_externas.setMinimumHeight(40)
        self.btn_externas.setVisible(False) 
        self.btn_externas.clicked.connect(self.toggle_vista_externas)

        self.btn_subir_nube = QPushButton("☁️ Subir a la nube")
        self.btn_subir_nube.setStyleSheet("background-color: #3182CE; color: white; font-weight: bold;")
        self.btn_subir_nube.setMinimumHeight(40)
        self.btn_subir_nube.setVisible(False)
        self.btn_subir_nube.clicked.connect(self.subir_externas_a_nube)

        self.btn_crear = QPushButton("➕ Crear Cotización")
        self.btn_crear.setObjectName("botonAgregar")
        self.btn_crear.setMinimumHeight(40)
        self.btn_crear.clicked.connect(self.crear_cotizacion)

        header_layout.addWidget(self.titulo)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_externas)
        header_layout.addWidget(self.btn_subir_nube)
        header_layout.addWidget(self.input_buscar)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.btn_crear)
        layout.addLayout(header_layout)

        self.tabla = QTableWidget()
        columnas = ["ID", "Fecha", "Folio", "Cliente", "Vendedor", "Estado", "Monto Total", "Acciones"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        
        header = self.tabla.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  
        header.setSectionResizeMode(3, QHeaderView.Stretch)           
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  
        
        self.tabla.setColumnWidth(0, 80)
        self.tabla.setColumnWidth(1, 100)
        self.tabla.setColumnWidth(2, 100)
        self.tabla.setColumnWidth(4, 150)
        self.tabla.setColumnWidth(5, 120)
        self.tabla.setColumnWidth(6, 130)
        self.tabla.setColumnWidth(7, 330)
        
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.setAlternatingRowColors(True)
        
        self.tabla.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:!active { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla)

        self.cargar_datos()

    def cargar_datos(self):
        filtro = f"%{self.input_buscar.text().strip()}%"
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM cotizaciones_ext")
            hay_externas = cursor.fetchone()[0] > 0
            if not self.viendo_externas:
                self.btn_externas.setVisible(hay_externas)
        except:
            pass 

        if self.viendo_externas:
            tabla_maestra = "cotizaciones_ext"
            self.titulo.setText("⚠️ Cotizaciones OFFLINE (Pendientes de subir)")
        else:
            tabla_maestra = "cotizaciones"
            self.titulo.setText("📑 Historial de Cotizaciones")

        query = f"""
            SELECT c.id_cotizacion, c.fecha, c.folio, cl.nombre_completo, cl.id_cliente, c.vendedor, c.estado, c.monto_total 
            FROM {tabla_maestra} c
            JOIN clientes cl ON c.cliente_id = cl.id_cliente
            WHERE c.folio LIKE ? OR cl.nombre_completo LIKE ? OR c.id_cotizacion LIKE ?
            ORDER BY c.id_cotizacion DESC
        """
        try:
            cursor.execute(query, (filtro, filtro, filtro))
            cotizaciones = cursor.fetchall()
        except:
            cotizaciones = [] 

        conexion.close()
        self.tabla.setRowCount(len(cotizaciones))
        
        for fila, cot in enumerate(cotizaciones):
            id_cot, fecha, folio, cliente_nombre, cliente_id, vendedor, estado, monto = cot
            items = [
                QTableWidgetItem(f"CT{id_cot:03d}" if not self.viendo_externas else f"EXT{id_cot:03d}"),
                QTableWidgetItem(str(fecha)), QTableWidgetItem(str(folio)),
                QTableWidgetItem(f"{cliente_nombre} ({cliente_id})"), QTableWidgetItem(str(vendedor)),
                QTableWidgetItem(str(estado)), QTableWidgetItem(f"${monto:,.2f}")
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col in [0, 1, 2, 5, 6] else Qt.AlignLeft))
                self.tabla.setItem(fila, col, item)

            widget_acciones = QWidget()
            layout_acciones = QHBoxLayout(widget_acciones)
            layout_acciones.setContentsMargins(15, 0, 15, 0)
            layout_acciones.setSpacing(10)
            
            btn_editar = QPushButton("✏️ Editar")
            btn_editar.setObjectName("botonEditar")
            
            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setObjectName("botonEditar")
            
            btn_eliminar = QPushButton("🗑️ Eliminar")
            btn_eliminar.setObjectName("botonEliminar")
            
            if self.viendo_externas:
                #btn_pdf.setDisabled(True)
                btn_editar.setDisabled(True)
                btn_pdf.setToolTip("Sube la cotización a la nube primero")
                btn_editar.setToolTip("Sube la cotización a la nube primero")
                btn_eliminar.clicked.connect(lambda checked, c_id=id_cot, f=folio: self.eliminar_cotizacion_externa(c_id, f))
                btn_pdf.clicked.connect(lambda checked, f=folio, es_externa=True: self.generar_pdf(f, es_externa))
            else:
                btn_editar.clicked.connect(lambda checked, c_id=id_cot: self.editar_cotizacion(c_id))
                btn_pdf.clicked.connect(lambda checked, f=folio: self.generar_pdf(f))
                btn_eliminar.clicked.connect(lambda checked, c_id=id_cot, f=folio: self.eliminar_cotizacion(c_id, f))

            layout_acciones.addStretch()
            layout_acciones.addWidget(btn_editar)
            layout_acciones.addWidget(btn_pdf)
            layout_acciones.addWidget(btn_eliminar)
            layout_acciones.addStretch()
            
            self.tabla.setCellWidget(fila, 7, widget_acciones)

    def toggle_vista_externas(self):
        self.viendo_externas = not self.viendo_externas
        if self.viendo_externas:
            self.btn_externas.setText("Volver a Cotizaciones Normales")
            self.btn_externas.setStyleSheet("background-color: #4A5568; color: white;")
            self.btn_subir_nube.setVisible(True)
            self.btn_crear.setVisible(False)
        else:
            self.btn_externas.setText("⚠️ Cotizaciones Externas")
            self.btn_externas.setStyleSheet("background-color: #DD6B20; color: white;")
            self.btn_subir_nube.setVisible(False)
            self.btn_crear.setVisible(True)
        self.cargar_datos()

    def subir_externas_a_nube(self):
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin Conexión", "No hay conexión a internet para subir los datos.")
            return

        conexion = obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT * FROM cotizaciones_ext")
            cotizaciones_ext = cursor.fetchall()
            
            if not cotizaciones_ext:
                QMessageBox.information(self, "Info", "No hay cotizaciones pendientes por subir.")
                return

            self.btn_subir_nube.setText("⏳ Subiendo...")
            self.btn_subir_nube.setEnabled(False)
            QApplication.processEvents() # Actualiza la UI para que se vea el cambio de botón

            payload = {"cotizaciones": []}
            
            for cot in cotizaciones_ext:
                c_id, folio, fecha, cli_id, vend, oc, obra, estado, monto = cot
                cursor.execute("SELECT * FROM cotizaciones_detalle_ext WHERE cotizacion_id=?", (c_id,))
                detalles_ext = cursor.fetchall()
                
                lista_detalles = []
                for det in detalles_ext:
                    lista_detalles.append({
                        "codigo_producto": det[2], "descripcion": det[3], "cantidad": det[4],
                        "um": det[5], "precio_unitario": det[6], "monto": det[7], "disponibilidad": det[8]
                    })
                    
                payload["cotizaciones"].append({
                    "folio": folio, "fecha": fecha, "cliente_id": cli_id, "vendedor": vend,
                    "oc": oc, "obra": obra, "estado": estado, "monto_total": monto,
                    "detalles": lista_detalles
                })

            URL_SUBIR_EXT = "https://api-pro-electro.pro-electro.workers.dev/api/subir_cotizaciones_ext"
            resp = requests.post(URL_SUBIR_EXT, json=payload, timeout=15)
            
            if resp.status_code == 200 and resp.json().get("success"):
                # Si se subieron bien, limpiamos las tablas temporales locales
                cursor.execute("DELETE FROM cotizaciones_detalle_ext")
                cursor.execute("DELETE FROM cotizaciones_ext")
                conexion.commit()
                
                # Forzamos la descarga para traer todas las cotizaciones con sus nuevos IDs generados en nube
                forzar_descarga_nube()
                
                QMessageBox.information(self, "Éxito", "Cotizaciones offline subidas e integradas correctamente.")
                self.toggle_vista_externas() # Regresa la pantalla a la normalidad automáticamente
            else:
                QMessageBox.critical(self, "Error de Servidor", f"No se pudo subir a la nube: {resp.text}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error Local", f"Fallo al procesar: {str(e)}")
        finally:
            self.btn_subir_nube.setText("☁️ Subir a la nube")
            self.btn_subir_nube.setEnabled(True)
            conexion.close()
            self.cargar_datos()

    def crear_cotizacion(self):
        # NOTA: Aquí no bloqueamos por internet, porque el usuario sí puede crear cotizaciones offline.
        dialogo = DialogoCotizacion(self)
        if dialogo.exec():
            self.cargar_datos()

    def editar_cotizacion(self, cotizacion_id):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet. Las modificaciones a cotizaciones existentes requieren conexión en tiempo real.")
            return

        dialogo = DialogoCotizacion(self, cotizacion_id)
        if dialogo.exec():
            self.cargar_datos()

    def generar_pdf(self, folio, es_externa=False):
        try:
            # PASAMOS el flag de externa a la función de generación de PDF
            exito, mensaje_o_ruta = generar_pdf_cotizacion(folio, es_externa, parent_widget=self)
            
            if exito:
                if mensaje_o_ruta == "Operación cancelada por el usuario":
                    return
                    
                respuesta = QMessageBox.question(
                    self,
                    "PDF Generado",
                    f"La cotización {folio} se generó correctamente en:\n{mensaje_o_ruta}\n\n¿Deseas abrir el archivo?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if respuesta == QMessageBox.Yes:
                    import os, sys, subprocess
                    try:
                        if sys.platform == "win32":
                            os.startfile(mensaje_o_ruta)
                        elif sys.platform == "darwin":
                            subprocess.run(['open', mensaje_o_ruta])
                        else:
                            subprocess.run(['xdg-open', mensaje_o_ruta])
                    except Exception as e:
                        QMessageBox.warning(self, "Error al abrir", 
                                        f"No se pudo abrir el archivo automáticamente:\n{str(e)}\n\nPuedes encontrarlo en:\n{mensaje_o_ruta}")
            else:
                if mensaje_o_ruta != "Operación cancelada por el usuario":
                    QMessageBox.warning(self, "Error", mensaje_o_ruta)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error Fatal", f"Ocurrió un error al generar el PDF:\n{str(e)}")
    def eliminar_cotizacion(self, c_id, folio):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las eliminaciones requieren conexión en tiempo real.")
            return

        respuesta = QMessageBox.question(self, "Confirmar Eliminación", 
                                         f"¿Eliminar permanentemente la cotización {folio}?",
                                         QMessageBox.Yes | QMessageBox.No)
        if respuesta == QMessageBox.Yes:
            # --- REGLA 3: ONLINE-FIRST (NUBE PRIMERO) ---
            # Solo mandamos borrar el encabezado. La nube (Cloudflare) borrará los detalles en cascada automáticamente.
            exito_c, msj_c = operacion_crud_nube('cotizaciones', 'DELETE', registro_id=c_id)
            
            if not exito_c: 
                QMessageBox.critical(self, "Error en la Nube", f"Fallo en la nube al eliminar: {msj_c}")
                return

            # --- CASCADA LOCAL ---
            # Si la nube tuvo éxito, borramos localmente ambos
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("DELETE FROM cotizaciones_detalle WHERE cotizacion_id=?", (c_id,))
                cursor.execute("DELETE FROM cotizaciones WHERE id_cotizacion=?", (c_id,))
                conexion.commit()
                
                QMessageBox.information(self, "Éxito", "Cotización eliminada correctamente en todos los sistemas.")
            except Exception as e:
                QMessageBox.critical(self, "Error Local", f"No se pudo eliminar:\n{str(e)}")
            finally:
                conexion.close()
            
            self.cargar_datos()

    def eliminar_cotizacion_externa(self, c_id, folio):
        # Aquí NO necesitamos internet, es una tabla puramente local
        respuesta = QMessageBox.question(self, "Confirmar Eliminación", 
                                         f"¿Eliminar la cotización OFFLINE {folio}?\n(Esta acción no se puede deshacer)",
                                         QMessageBox.Yes | QMessageBox.No)
        if respuesta == QMessageBox.Yes:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("DELETE FROM cotizaciones_detalle_ext WHERE cotizacion_id=?", (c_id,))
                cursor.execute("DELETE FROM cotizaciones_ext WHERE id_cotizacion=?", (c_id,))
                conexion.commit()
                QMessageBox.information(self, "Éxito", "Cotización offline eliminada.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar: {str(e)}")
            finally:
                conexion.close()
            self.cargar_datos()