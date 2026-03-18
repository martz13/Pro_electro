from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QHeaderView, QDialog, QMessageBox, 
                               QGridLayout, QComboBox, QDateEdit, QGroupBox,
                               QScrollArea, QFrame, QSizePolicy, QSpinBox, QDoubleSpinBox)
from PySide6.QtCore import Qt, QDate, QLocale

import requests

from base_datos.conexion import obtener_conexion, operacion_crud_nube, forzar_descarga_nube
from utilidades.generador_pdf_OC import generar_pdf_orden_compra
# ==========================================
# DIÁLOGOS DE SELECCIÓN (PROVEEDOR Y PRODUCTO)
# ==========================================
class DialogoSeleccionarProveedor(QDialog):
    def __init__(self, parent=None, resultados=[]):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Proveedor")
        self.setFixedSize(600, 350)
        self.setModal(True)
        self.proveedor_seleccionado = None
        self.resultados = resultados

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        lbl_info = QLabel("Se encontraron múltiples coincidencias. Selecciona el proveedor correcto:")
        lbl_info.setObjectName("labelTitulo")
        layout.addWidget(lbl_info)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["ID", "Empresa"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; font-size: 14px;}
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:!active { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla)

        self.tabla.setRowCount(len(resultados))
        for fila, prov in enumerate(resultados):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(prov[0])))
            self.tabla.setItem(fila, 1, QTableWidgetItem(str(prov[1])))

        btn = QPushButton("Seleccionar Proveedor")
        btn.setObjectName("botonPrincipal")
        btn.setMinimumHeight(45)
        btn.clicked.connect(self.seleccionar)
        layout.addWidget(btn)

    def seleccionar(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.proveedor_seleccionado = self.resultados[fila]
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Selecciona un proveedor de la lista.")

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
        
        lbl_info = QLabel("Múltiples coincidencias. Selecciona el producto a agregar:")
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
            QTableWidget { alternate-background-color: #F9FAFB; font-size: 14px;}
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:!active { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla)

        self.tabla.setRowCount(len(resultados))
        for fila, prod in enumerate(resultados):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(prod[0])))
            self.tabla.setItem(fila, 1, QTableWidgetItem(str(prod[1])))

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
            QMessageBox.warning(self, "Aviso", "Selecciona un producto de la lista.")


# ==========================================
# MODAL PARA AGREGAR / EDITAR ORDEN DE COMPRA
# ==========================================
class DialogoOrdenCompra(QDialog):
    def __init__(self, parent=None, orden_id=None):
        super().__init__(parent)
        self.orden_id = orden_id
        self.setWindowTitle("Nueva Orden de Compra" if not orden_id else f"Editar OC - {orden_id}")
        self.setMinimumSize(1000, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setWindowState(Qt.WindowMaximized)
        self.setModal(True)
        
        self.proveedor_seleccionado = None
        self.total_final = 0.0

        layout_base = QVBoxLayout(self)
        layout_base.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        contenedor = QWidget()
        self.layout_principal = QVBoxLayout(contenedor)
        self.layout_principal.setContentsMargins(20, 20, 20, 20)
        self.layout_principal.setSpacing(20)

        # 1. ENCABEZADO
        self.grupo_encabezado = self.crear_encabezado()
        self.layout_principal.addWidget(self.grupo_encabezado)

        # 2. DETALLE PRODUCTOS
        self.grupo_detalle = self.crear_detalle()
        self.tabla.installEventFilter(self) 
        self.layout_principal.addWidget(self.grupo_detalle)

        # 3. PIE Y TOTALES
        self.layout_totales = self.crear_totales()
        self.layout_principal.addLayout(self.layout_totales)

        scroll_area.setWidget(contenedor)
        layout_base.addWidget(scroll_area)

        self.cargar_super_admins()

        if self.orden_id:
            self.cargar_orden_existente()
        else:
            self.input_folio.setText("OC-Auto")

    def crear_encabezado(self):
        grupo = QGroupBox("1. Datos del Proveedor y Envío")
        grupo.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 16px; border: 1px solid #CBD5E0; border-radius: 6px; margin-top: 15px; } 
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2B6CB0; }
        """)
        grid = QGridLayout(grupo)
        grid.setContentsMargins(25, 35, 25, 25)
        grid.setSpacing(20)

        # Buscador Proveedor
        lbl_prov = QLabel("Buscar Proveedor:"); lbl_prov.setObjectName("labelTitulo")
        grid.addWidget(lbl_prov, 0, 0)
        
        lay_prov = QHBoxLayout()
        self.input_buscar_prov = QLineEdit()
        self.input_buscar_prov.setPlaceholderText("🔍 Buscar por ID o Nombre (Enter)...")
        self.input_buscar_prov.setMinimumHeight(42)
        self.input_buscar_prov.returnPressed.connect(self.buscar_proveedor)
        btn_buscar_prov = QPushButton("Buscar")
        btn_buscar_prov.setObjectName("botonAgregar")
        btn_buscar_prov.setMinimumHeight(42)
        btn_buscar_prov.setAutoDefault(False) # 🌟 MAGIA: Evita que el "Enter" presione este botón por accidente
        btn_buscar_prov.clicked.connect(self.buscar_proveedor)
        lay_prov.addWidget(self.input_buscar_prov)
        lay_prov.addWidget(btn_buscar_prov)
        grid.addLayout(lay_prov, 0, 1, 1, 3)

        # Info del proveedor seleccionado
        self.lbl_info_prov = QLabel("Empresa: -\nID: -\nTeléfono: -")
        self.lbl_info_prov.setStyleSheet("color: #4A5568; font-size: 14px; background-color: #F7FAFC; padding: 12px; border-radius: 6px; border: 1px dashed #CBD5E0;")
        grid.addWidget(self.lbl_info_prov, 1, 0, 1, 4)

        # Dirección y Teléfono
        lbl_dir = QLabel("Dirección de Envío:"); lbl_dir.setObjectName("labelTitulo")
        grid.addWidget(lbl_dir, 2, 0)
        self.input_direccion = QLineEdit()
        self.input_direccion.setMinimumHeight(42)
        grid.addWidget(self.input_direccion, 2, 1, 1, 3)

        lbl_tel = QLabel("Teléfono Envío:"); lbl_tel.setObjectName("labelTitulo")
        grid.addWidget(lbl_tel, 3, 0)
        self.input_telefono = QLineEdit()
        self.input_telefono.setMinimumHeight(42)
        grid.addWidget(self.input_telefono, 3, 1)

        # Representante, Referencia, Fecha, Folio
        lbl_admin = QLabel("Representante:"); lbl_admin.setObjectName("labelTitulo")
        grid.addWidget(lbl_admin, 3, 2)
        self.combo_admin = QComboBox()
        self.combo_admin.setMinimumHeight(42)
        grid.addWidget(self.combo_admin, 3, 3)

        lbl_ref = QLabel("Referencia:"); lbl_ref.setObjectName("labelTitulo")
        grid.addWidget(lbl_ref, 4, 0)
        self.input_referencia = QLineEdit()
        self.input_referencia.setMinimumHeight(42)
        grid.addWidget(self.input_referencia, 4, 1)

        lbl_fecha = QLabel("Fecha:"); lbl_fecha.setObjectName("labelTitulo")
        grid.addWidget(lbl_fecha, 4, 2)
        self.input_fecha = QDateEdit()
        self.input_fecha.setMinimumHeight(42)
        self.input_fecha.setCalendarPopup(True)
        self.input_fecha.setDate(QDate.currentDate())
        grid.addWidget(self.input_fecha, 4, 3)

        lbl_folio = QLabel("Folio:"); lbl_folio.setObjectName("labelTitulo")
        grid.addWidget(lbl_folio, 5, 0)
        self.input_folio = QLineEdit()
        self.input_folio.setMinimumHeight(42)
        self.input_folio.setReadOnly(True)
        self.input_folio.setStyleSheet("background-color: #E2E8F0; color: #4A5568; font-weight: bold;")
        grid.addWidget(self.input_folio, 5, 1)

        return grupo
    def crear_detalle(self):
        grupo = QGroupBox("2. Detalle de Productos")
        grupo.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 16px; border: 1px solid #CBD5E0; border-radius: 6px; margin-top: 15px; } 
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2B6CB0; }
        """)
        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(25, 35, 25, 25)
        layout.setSpacing(15)

        # Buscador de productos
        busc_layout = QHBoxLayout()
        self.input_buscar_prod = QLineEdit()
        self.input_buscar_prod.setPlaceholderText("🔍 Buscar producto por Código o Descripción...")
        self.input_buscar_prod.setMinimumHeight(45)
        # 🌟 ELIMINAMOS la línea 'returnPressed' para desactivar el Enter
        def bloquear_enter(event):
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                pass # El Enter muere aquí, no hace absolutamente nada
            else:
                QLineEdit.keyPressEvent(self.input_buscar_prod, event)
        
        self.input_buscar_prod.keyPressEvent = bloquear_enter
        
        self.combo_productos_prov = QComboBox()
        self.combo_productos_prov.setMinimumHeight(45)
        self.combo_productos_prov.setMinimumWidth(300)
        
        btn_agregar_prod = QPushButton("Buscar / Agregar")
        btn_agregar_prod.setObjectName("botonAgregar")
        btn_agregar_prod.setMinimumHeight(45)
        btn_agregar_prod.setMinimumWidth(180)
        btn_agregar_prod.setAutoDefault(False) # 🌟 Evitar clics accidentales
        btn_agregar_prod.clicked.connect(self.buscar_producto_txt)
        
        btn_agregar_combo = QPushButton("Agregar de Lista")
        btn_agregar_combo.setObjectName("botonAgregar")
        btn_agregar_combo.setMinimumHeight(45)
        btn_agregar_combo.setMinimumWidth(150)
        btn_agregar_combo.setAutoDefault(False) # 🌟 Evitar clics accidentales
        btn_agregar_combo.clicked.connect(self.agregar_desde_combo)
        
        busc_layout.addWidget(self.input_buscar_prod)
        busc_layout.addWidget(btn_agregar_prod)
        busc_layout.addSpacing(20)
        busc_layout.addWidget(self.combo_productos_prov)
        busc_layout.addWidget(btn_agregar_combo)
        layout.addLayout(busc_layout)

        # Tabla interactiva
        self.tabla = QTableWidget()
        self.tabla.setMinimumHeight(400)
        columnas = ["Código", "Descripción", "Cantidad", "UM", "Precio Unitario", "Monto", "Quitar"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setColumnWidth(0, 150) 
        self.tabla.setColumnWidth(2, 110) 
        self.tabla.setColumnWidth(3, 80)  
        self.tabla.setColumnWidth(4, 150) 
        self.tabla.setColumnWidth(5, 150) 
        self.tabla.setColumnWidth(6, 100) 
        
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(60) 
        self.tabla.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; font-size: 15px; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:!active { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla)
        return grupo

    def crear_totales(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addStretch()

        self.lbl_subtotal = QLabel("Subtotal: $0.00")
        self.lbl_iva = QLabel("IVA (16%): $0.00")
        self.lbl_total = QLabel("Total: $0.00")
        
        self.lbl_subtotal.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A5568;")
        self.lbl_iva.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A5568;")
        self.lbl_total.setStyleSheet("font-size: 24px; font-weight: bold; color: #2B6CB0; background-color: #EBF8FF; padding: 10px 20px; border-radius: 6px;")

        layout.addWidget(self.lbl_subtotal)
        layout.addSpacing(30)
        layout.addWidget(self.lbl_iva)
        layout.addSpacing(30)
        layout.addWidget(self.lbl_total)

        self.btn_guardar = QPushButton("Guardar Orden")
        self.btn_guardar.setObjectName("botonPrincipal")
        self.btn_guardar.setMinimumHeight(55)
        self.btn_guardar.setMinimumWidth(250)
        self.btn_guardar.setAutoDefault(False) # 🌟 Evita que el Enter guarde la orden a medias
        self.btn_guardar.clicked.connect(self.guardar)
        
        layout.addSpacing(40)
        layout.addWidget(self.btn_guardar)
        return layout

    def cargar_super_admins(self):
        self.combo_admin.clear()
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre_completo FROM usuarios WHERE rol='Super admin'")
        for r in cursor.fetchall():
            self.combo_admin.addItem(r[0])
        conn.close()
        
    def eventFilter(self, obj, event):
        # Manejar eventos de teclado en los spinboxes de cantidad
        if event.type() == event.Type.KeyPress and isinstance(obj, SpinBoxSinRueda):
            key = event.key()
            if key in (Qt.Key_Up, Qt.Key_Down):
                # Encontrar la fila a la que pertenece este spinbox
                for fila in range(self.tabla.rowCount()):
                    if self.tabla.cellWidget(fila, 2) == obj:  # Columna 2 es Cantidad
                        current_row = fila
                        break
                else:
                    return super().eventFilter(obj, event)

                if key == Qt.Key_Up and current_row > 0:
                    nuevo_spin = self.tabla.cellWidget(current_row - 1, 2)
                    if nuevo_spin:
                        self.tabla.setCurrentCell(current_row - 1, 2)
                        nuevo_spin.setFocus()
                        return True
                elif key == Qt.Key_Down and current_row < self.tabla.rowCount() - 1:
                    nuevo_spin = self.tabla.cellWidget(current_row + 1, 2)
                    if nuevo_spin:
                        self.tabla.setCurrentCell(current_row + 1, 2)
                        nuevo_spin.setFocus()
                        return True

        # Manejar eventos de teclado en la tabla (para navegación general)
        elif obj == self.tabla and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key_Up, Qt.Key_Down):
                current_row = self.tabla.currentRow()
                if key == Qt.Key_Up and current_row > 0:
                    self.tabla.setCurrentCell(current_row - 1, 2)
                    spin = self.tabla.cellWidget(current_row - 1, 2)
                    if spin:
                        spin.setFocus()
                    return True
                elif key == Qt.Key_Down and current_row < self.tabla.rowCount() - 1:
                    self.tabla.setCurrentCell(current_row + 1, 2)
                    spin = self.tabla.cellWidget(current_row + 1, 2)
                    if spin:
                        spin.setFocus()
                    return True

        return super().eventFilter(obj, event)

    def buscar_proveedor(self):
        txt = self.input_buscar_prov.text().strip()
        if not txt:
            QMessageBox.warning(self, "Aviso", "Ingresa un ID o Nombre para buscar al proveedor.")
            return
            
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id_prov, nombre_empresa, num_telefono FROM proveedores WHERE id_prov LIKE ? OR nombre_empresa LIKE ?", (f"%{txt}%", f"%{txt}%"))
        res = cursor.fetchall()
        conn.close()

        if len(res) == 1:
            self.set_proveedor(res[0])
        elif len(res) > 1:
            d = DialogoSeleccionarProveedor(self, res)
            if d.exec() and d.proveedor_seleccionado:
                self.set_proveedor(d.proveedor_seleccionado)
        else:
            QMessageBox.warning(self, "Sin resultados", "No se encontró ningún proveedor.")

    def set_proveedor(self, prov):
        self.proveedor_seleccionado = prov
        self.input_buscar_prov.setText(prov[1])
        telefono = prov[2] if prov[2] else "N/D"
        self.lbl_info_prov.setText(f"Empresa: {prov[1]}\nID: {prov[0]}\nTeléfono: {telefono}")
        
        # Llenar combo de productos de este proveedor
        self.combo_productos_prov.clear()
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_producto, descripcion, um, precio_compra FROM inventario WHERE proveedor_id=?", (prov[0],))
        for p in cursor.fetchall():
            self.combo_productos_prov.addItem(f"{p[0]} - {p[1]}", p) # Pasamos 'p' (cod, desc, um, compra) como Data
        conn.close()
        
        # Limpiamos la tabla de productos porque cambiamos de proveedor
        self.tabla.setRowCount(0)
        self.calcular_totales()

    def agregar_desde_combo(self):
        if not self.proveedor_seleccionado:
            QMessageBox.warning(self, "Error", "Selecciona un proveedor primero.")
            return
            
        data = self.combo_productos_prov.currentData()
        if data: 
            # Seguridad: si el precio viene Nulo de la BD, lo convierte a 0.0
            precio = float(data[3]) if data[3] is not None else 0.0 
            self.agregar_fila(data[0], data[1], data[2], 1, precio)

    def buscar_producto_txt(self):
        if not self.proveedor_seleccionado:
            QMessageBox.warning(self, "Error", "Selecciona un proveedor primero.")
            return
            
        txt = self.input_buscar_prod.text().strip()
        if not txt:
            QMessageBox.warning(self, "Aviso", "Ingresa un código o descripción del producto a buscar.")
            return
            
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT codigo_producto, descripcion, um, precio_compra 
            FROM inventario 
            WHERE proveedor_id=? AND (codigo_producto LIKE ? OR descripcion LIKE ?)
        """, (self.proveedor_seleccionado[0], f"%{txt}%", f"%{txt}%"))
        res = cursor.fetchall()
        conn.close()
        
        if not res:
            QMessageBox.warning(self, "Sin resultados", "No se encontró este producto para el proveedor seleccionado.")
        elif len(res) == 1:
            precio = float(res[0][3]) if res[0][3] is not None else 0.0
            self.agregar_fila(res[0][0], res[0][1], res[0][2], 1, precio)
            self.input_buscar_prod.clear()
        else:
            d = DialogoSeleccionarProducto(self, res)
            if d.exec() and d.producto_seleccionado:
                prod = d.producto_seleccionado
                precio = float(prod[3]) if prod[3] is not None else 0.0
                self.agregar_fila(prod[0], prod[1], prod[2], 1, precio)
                self.input_buscar_prod.clear()


    def agregar_fila(self, codigo, desc, um, cant, precio):
        # 🌟 SUMAR CANTIDAD SI EL PRODUCTO YA ESTÁ EN LA TABLA
        for fila in range(self.tabla.rowCount()):
            if self.tabla.item(fila, 0).text() == codigo:
                spin_cant = self.tabla.cellWidget(fila, 2) # Columna 2 es Cantidad
                spin_cant.setValue(spin_cant.value() + int(cant))
                return # Salimos de la función sin crear nueva fila

        # SI NO EXISTE, CREAMOS LA FILA NUEVA
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)

        # Configuración de los Items de Texto
        item_cod = QTableWidgetItem(str(codigo))
        item_desc = QTableWidgetItem(str(desc))
        item_desc.setToolTip(str(desc))
        item_um = QTableWidgetItem(str(um))
        item_monto = QTableWidgetItem("0.00")
        
        for col, item in zip([0, 1, 3, 5], [item_cod, item_desc, item_um, item_monto]):
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if col == 1 else Qt.AlignCenter))
            self.tabla.setItem(fila, col, item)

        # SpinBox entero para Cantidad (Columna 2)
        spin_cant = SpinBoxSinRueda()
        spin_cant.setMinimumHeight(40)
        spin_cant.setStyleSheet("font-size: 15px;")
        spin_cant.setRange(1, 999999)
        spin_cant.setValue(int(cant))
        spin_cant.valueChanged.connect(self.calcular_totales)
        spin_cant.installEventFilter(self)
        self.tabla.setCellWidget(fila, 2, spin_cant)

        # Enfocar el spinbox de la nueva fila
        self.tabla.setCurrentCell(fila, 2)
        spin_cant.setFocus()

        # DoubleSpinBox editable para Precio Unitario (Columna 4)
        spin_precio = QDoubleSpinBox()
        spin_precio.setLocale(QLocale(QLocale.English, QLocale.UnitedStates)) # 🌟 FUERZA EL USO DE PUNTO (.) DECIMAL
        spin_precio.setMinimumHeight(40)
        spin_precio.setStyleSheet("font-size: 15px;")
        spin_precio.setRange(0.0, 9999999.99)
        spin_precio.setValue(float(precio))
        spin_precio.setDecimals(2)
        spin_precio.valueChanged.connect(self.calcular_totales)
        self.tabla.setCellWidget(fila, 4, spin_precio)

        # Botón Quitar (Columna 6)
        btn_q = QPushButton("❌ Quitar")
        btn_q.setObjectName("botonEliminar")
        btn_q.setMinimumHeight(35)
        btn_q.clicked.connect(lambda _, f=fila: self.quitar_fila(f))
        
        widget_btn = QWidget()
        layout_btn = QHBoxLayout(widget_btn)
        layout_btn.setContentsMargins(10, 5, 10, 5)
        layout_btn.addWidget(btn_q)
        self.tabla.setCellWidget(fila, 6, widget_btn)

        self.calcular_totales()

    def quitar_fila(self, fila):
        self.tabla.removeRow(fila)
        self.calcular_totales()
        # Reconectar botones porque los índices cambiaron
        for i in range(self.tabla.rowCount()):
            # Reconectar SpinBoxes
            spin_c = self.tabla.cellWidget(i, 2)
            spin_p = self.tabla.cellWidget(i, 4)
            spin_c.valueChanged.disconnect()
            spin_p.valueChanged.disconnect()
            spin_c.valueChanged.connect(self.calcular_totales)
            spin_p.valueChanged.connect(self.calcular_totales)
            
            # Reconectar botón Eliminar
            btn_w = self.tabla.cellWidget(i, 6)
            btn = btn_w.layout().itemAt(0).widget()
            btn.clicked.disconnect()
            btn.clicked.connect(lambda _, f=i: self.quitar_fila(f))

    def calcular_totales(self):
        subtotal = 0.0
        for i in range(self.tabla.rowCount()):
            try:
                cant = self.tabla.cellWidget(i, 2).value()
                precio = self.tabla.cellWidget(i, 4).value()
                importe = cant * precio
                self.tabla.item(i, 5).setText(f"{importe:.2f}")
                subtotal += importe
            except:
                pass

        iva = subtotal * 0.16
        self.total_final = subtotal + iva
        self.lbl_subtotal.setText(f"Subtotal: ${subtotal:,.2f}")
        self.lbl_iva.setText(f"IVA (16%): ${iva:,.2f}")
        self.lbl_total.setText(f"Total: ${self.total_final:,.2f}")

    def guardar(self):
        if not self.proveedor_seleccionado or self.tabla.rowCount() == 0:
            QMessageBox.warning(self, "Error", "Faltan datos o productos.")
            return

        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
            # REGLA 2: Colisiones
            resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=ordenes_compra", timeout=3)
            if resp.status_code == 200:
                conn = obtener_conexion()
                if resp.json().get("total", 0) > conn.cursor().execute("SELECT COUNT(*) FROM ordenes_compra").fetchone()[0]:
                    QMessageBox.information(self, "Aviso", "Datos nuevos en la nube. Sincronizando...")
                    forzar_descarga_nube()
                conn.close()
        except:
            QMessageBox.warning(self, "Sin internet", "Se requiere conexión para guardar Órdenes de Compra.")
            return

        encabezado = {
            "fecha": self.input_fecha.date().toString("yyyy-MM-dd"),
            "proveedor_id": self.proveedor_seleccionado[0],
            "representante": self.combo_admin.currentText(),
            "referencia": self.input_referencia.text().strip(),
            "direccion_envio": self.input_direccion.text().strip(),
            "telefono_envio": self.input_telefono.text().strip(),
            "monto_total": self.total_final
        }

        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            if self.orden_id:
                # UPDATE
                exito, msj = operacion_crud_nube('ordenes_compra', 'UPDATE', encabezado, self.orden_id)
                if not exito: raise Exception(msj)
                
                # Borrar detalles viejos en la nube
                for d in cursor.execute("SELECT id FROM ordenes_compra_detalle WHERE orden_id=?", (self.orden_id,)).fetchall():
                    operacion_crud_nube('ordenes_compra_detalle', 'DELETE', registro_id=d[0])
                cursor.execute("DELETE FROM ordenes_compra_detalle WHERE orden_id=?", (self.orden_id,))
                
                cursor.execute("UPDATE ordenes_compra SET fecha=?, proveedor_id=?, representante=?, referencia=?, direccion_envio=?, telefono_envio=?, monto_total=? WHERE id_orden=?",
                               (encabezado["fecha"], encabezado["proveedor_id"], encabezado["representante"], encabezado["referencia"], encabezado["direccion_envio"], encabezado["telefono_envio"], encabezado["monto_total"], self.orden_id))
                id_actual = self.orden_id
            else:
                # INSERT
                encabezado["folio"] = "TEMP"
                exito, nuevo_id = operacion_crud_nube('ordenes_compra', 'INSERT', encabezado)
                if not exito: raise Exception(nuevo_id)
                id_actual = nuevo_id
                folio_real = f"OC{id_actual:04d}"
                cursor.execute("INSERT INTO ordenes_compra (id_orden, folio, fecha, proveedor_id, representante, referencia, direccion_envio, telefono_envio, monto_total) VALUES (?,?,?,?,?,?,?,?,?)",
                               (id_actual, folio_real, encabezado["fecha"], encabezado["proveedor_id"], encabezado["representante"], encabezado["referencia"], encabezado["direccion_envio"], encabezado["telefono_envio"], encabezado["monto_total"]))

            # Insertar Detalles
            for i in range(self.tabla.rowCount()):
                det = {
                    "orden_id": id_actual,
                    "codigo_producto": self.tabla.item(i, 0).text(),
                    "descripcion": self.tabla.item(i, 1).text(),
                    "cantidad": self.tabla.cellWidget(i, 2).value(), # Ahora es la col 2
                    "um": self.tabla.item(i, 3).text(),              # Ahora es la col 3
                    "precio_unitario": self.tabla.cellWidget(i, 4).value(),
                    "monto": float(self.tabla.item(i, 5).text())
                }
                exito_d, id_det = operacion_crud_nube('ordenes_compra_detalle', 'INSERT', det)
                if not exito_d: raise Exception(id_det)
                cursor.execute("INSERT INTO ordenes_compra_detalle (id, orden_id, codigo_producto, descripcion, cantidad, um, precio_unitario, monto) VALUES (?,?,?,?,?,?,?,?)",
                               (id_det, det["orden_id"], det["codigo_producto"], det["descripcion"], det["cantidad"], det["um"], det["precio_unitario"], det["monto"]))

            conn.commit()
            QMessageBox.information(self, "Éxito", "Orden de Compra guardada correctamente en la nube.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al guardar:\n{str(e)}")
        finally:
            conn.close()

    def cargar_orden_existente(self):
        conn = obtener_conexion()
        cursor = conn.cursor()
        c = cursor.execute("SELECT folio, fecha, proveedor_id, representante, referencia, direccion_envio, telefono_envio FROM ordenes_compra WHERE id_orden=?", (self.orden_id,)).fetchone()
        
        self.input_folio.setText(c[0])
        self.input_fecha.setDate(QDate.fromString(c[1], "yyyy-MM-dd"))
        
        prov = cursor.execute("SELECT id_prov, nombre_empresa FROM proveedores WHERE id_prov=?", (c[2],)).fetchone()
        
        if prov:
            # Replicamos el comportamiento de `set_proveedor` pero manual para evitar limpiar la tabla
            self.proveedor_seleccionado = prov
            self.input_buscar_prov.setText(prov[1])
            self.lbl_info_prov.setText(f"Empresa: {prov[1]}\nID: {prov[0]}\nTeléfono: N/D")
            
            # Llenar combo de productos de este proveedor
            self.combo_productos_prov.clear()
            cursor.execute("SELECT codigo_producto, descripcion, um, precio_compra FROM inventario WHERE proveedor_id=?", (prov[0],))
            for p in cursor.fetchall():
                self.combo_productos_prov.addItem(f"{p[0]} - {p[1]}", p)

        self.combo_admin.setCurrentText(c[3])
        self.input_referencia.setText(c[4])
        self.input_direccion.setText(c[5])
        self.input_telefono.setText(c[6])

        # ORDER BY id ASC para respetar el orden de inserción visual original
        detalles = cursor.execute("SELECT codigo_producto, descripcion, um, cantidad, precio_unitario FROM ordenes_compra_detalle WHERE orden_id=? ORDER BY id ASC", (self.orden_id,)).fetchall()
        for d in detalles:
            self.agregar_fila(d[0], d[1], d[2], d[3], d[4])
        conn.close()

class SpinBoxSinRueda(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)

    def wheelEvent(self, event):
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            event.ignore()
        else:
            super().keyPressEvent(event)
# ==========================================
# VISTA PRINCIPAL (HISTORIAL)
# ==========================================
class VistaOrdenesCompra(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Cabecera
        header_layout = QHBoxLayout()
        self.titulo = QLabel("🛒 Historial de Órdenes de Compra")
        self.titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("🔍 Buscar por Folio o Referencia...")
        self.buscador.setFixedWidth(350)
        self.buscador.setMinimumHeight(40)
        self.buscador.textChanged.connect(self.cargar_datos)
        
        self.btn_nueva = QPushButton("➕ Crear Orden de Compra")
        self.btn_nueva.setObjectName("botonAgregar")
        self.btn_nueva.setMinimumHeight(40)
        self.btn_nueva.clicked.connect(self.nueva_orden)
        
        header_layout.addWidget(self.titulo)
        header_layout.addStretch()
        header_layout.addWidget(self.buscador)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.btn_nueva)
        layout.addLayout(header_layout)

        # Tabla
        self.tabla = QTableWidget()
        columnas = ["Folio", "Proveedor", "Referencia", "Fecha", "Monto Total", "Acciones"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        
        header = self.tabla.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        
        self.tabla.setColumnWidth(5, 330) # Espacio para 3 botones (Editar, PDF, Eliminar)
        
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
        txt = f"%{self.buscador.text().strip()}%"
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id_orden, o.folio, p.nombre_empresa, o.referencia, o.fecha, o.monto_total 
            FROM ordenes_compra o 
            JOIN proveedores p ON o.proveedor_id = p.id_prov
            WHERE o.folio LIKE ? OR o.referencia LIKE ? ORDER BY o.id_orden DESC
        """, (txt, txt))
        filas = cursor.fetchall()
        conn.close()

        self.tabla.setRowCount(len(filas))
        for i, (id_ord, fol, prov, ref, fec, monto) in enumerate(filas):
            items = [
                QTableWidgetItem(fol),
                QTableWidgetItem(prov),
                QTableWidgetItem(ref or ""),
                QTableWidgetItem(fec),
                QTableWidgetItem(f"${monto:,.2f}")
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col in [0, 3, 4] else Qt.AlignLeft))
                self.tabla.setItem(i, col, item)

            widget_acciones = QWidget()
            layout_acciones = QHBoxLayout(widget_acciones)
            layout_acciones.setContentsMargins(15, 0, 15, 0)
            layout_acciones.setSpacing(10)
            
            btn_editar = QPushButton("✏️ Editar")
            btn_editar.setObjectName("botonEditar")
            btn_editar.clicked.connect(lambda _, x=id_ord: self.editar(x))
            
            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setObjectName("botonEditar")
            btn_pdf.clicked.connect(lambda _, f=fol: self.generar_pdf(f))
            
            btn_eliminar = QPushButton("🗑️ Eliminar")
            btn_eliminar.setObjectName("botonEliminar")
            btn_eliminar.clicked.connect(lambda _, x=id_ord, f=fol: self.eliminar(x, f))
            
            layout_acciones.addStretch()
            layout_acciones.addWidget(btn_editar)
            layout_acciones.addWidget(btn_pdf)
            layout_acciones.addWidget(btn_eliminar)
            layout_acciones.addStretch()
            
            self.tabla.setCellWidget(i, 5, widget_acciones)

    def nueva_orden(self):
        # Bloqueo offline básico por seguridad
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Se requiere internet para las Órdenes de Compra.")
            return

        if DialogoOrdenCompra(self).exec(): 
            self.cargar_datos()

    def editar(self, id_ord):
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Se requiere internet para editar las Órdenes de Compra.")
            return

        if DialogoOrdenCompra(self, id_ord).exec(): 
            self.cargar_datos()

    def eliminar(self, id_ord, folio):
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except:
            QMessageBox.warning(self, "Sin internet", "Requieres conexión para eliminar.")
            return
        
        if QMessageBox.question(self, "Eliminar", f"¿Borrar la orden {folio} permanentemente?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            exito, msj = operacion_crud_nube('ordenes_compra', 'DELETE', registro_id=id_ord)
            if not exito:
                QMessageBox.critical(self, "Error Nube", msj)
                return
            
            conn = obtener_conexion()
            conn.execute("DELETE FROM ordenes_compra_detalle WHERE orden_id=?", (id_ord,))
            conn.execute("DELETE FROM ordenes_compra WHERE id_orden=?", (id_ord,))
            conn.commit()
            conn.close()
            
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Orden de compra eliminada correctamente.")

    def generar_pdf(self, folio):
        try:
            exito, mensaje_o_ruta = generar_pdf_orden_compra(folio, parent_widget=self)
            if not exito and mensaje_o_ruta != "Operación cancelada por el usuario":
                QMessageBox.warning(self, "Error", mensaje_o_ruta)
        except Exception as e:
            QMessageBox.critical(self, "Error Fatal", f"Ocurrió un error al generar el PDF:\n{str(e)}")