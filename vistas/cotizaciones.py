from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QHeaderView, QDialog, QMessageBox, 
                               QGridLayout, QComboBox, QDateEdit, QDoubleSpinBox, QGroupBox,
                               QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor
from base_datos.conexion import obtener_conexion
from utilidades.generador_pdf import generar_pdf_cotizacion

# ==========================================
# 0. DIÁLOGO PARA SELECCIONAR PRODUCTO (BÚSQUEDA MÚLTIPLE)
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
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(["Código", "Descripción", "Stock", "UM", "Precio"])
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
            self.tabla.setItem(fila, 1, QTableWidgetItem(str(prod[1])))
            self.tabla.setItem(fila, 2, QTableWidgetItem(str(prod[2])))
            self.tabla.setItem(fila, 3, QTableWidgetItem(str(prod[3])))
            self.tabla.setItem(fila, 4, QTableWidgetItem(f"${prod[4]:.2f}"))

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

        # 1. LAYOUT BASE
        layout_base = QVBoxLayout(self)
        layout_base.setContentsMargins(0, 0, 0, 0) 

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) 
        scroll_area.setFrameShape(QFrame.NoFrame) 
        # Permitir scroll horizontal automático cuando sea necesario
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

        self.cargar_clientes()
        self.cargar_vendedores()  # Nuevo método para cargar usuarios

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

        lbl_cliente = QLabel("Seleccionar Cliente:"); lbl_cliente.setObjectName("labelTitulo")
        lbl_fecha = QLabel("Fecha:"); lbl_fecha.setObjectName("labelTitulo")
        lbl_folio = QLabel("Folio (Auto):"); lbl_folio.setObjectName("labelTitulo")
        lbl_vendedor = QLabel("Vendedor:"); lbl_vendedor.setObjectName("labelTitulo")
        lbl_oc = QLabel("OC (Orden Compra):"); lbl_oc.setObjectName("labelTitulo")
        lbl_obra = QLabel("Obra:"); lbl_obra.setObjectName("labelTitulo")

        grid.addWidget(lbl_cliente, 0, 0)
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumHeight(42)
        self.combo_cliente.currentIndexChanged.connect(self.mostrar_datos_cliente)
        grid.addWidget(self.combo_cliente, 0, 1, 1, 3)

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
        # Reemplazamos QLineEdit por QComboBox
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
        
        # Agregamos columna "Disponibilidad" después de "Quitar"
        columnas = ["Código", "Descripción", "Cantidad", "UM", "Precio Unitario", "Monto", "Quitar", "Disponibilidad"]
        self.tabla_prod.setColumnCount(len(columnas))
        self.tabla_prod.setHorizontalHeaderLabels(columnas)
        
        # Ajuste de anchos
        self.tabla_prod.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Descripción se estira
        self.tabla_prod.setColumnWidth(0, 150) 
        self.tabla_prod.setColumnWidth(2, 140) 
        self.tabla_prod.setColumnWidth(3, 100) 
        self.tabla_prod.setColumnWidth(4, 150) 
        self.tabla_prod.setColumnWidth(5, 150) 
        self.tabla_prod.setColumnWidth(6, 120)  # Quitar
        self.tabla_prod.setColumnWidth(7, 130)  # Disponibilidad
        
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
    
    def cargar_clientes(self):
        self.combo_cliente.clear()
        self.combo_cliente.addItem("--- Selecciona un cliente ---", userData=None)
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id_cliente, nombre_completo, rfc, direccion, telefono FROM clientes")
        for c in cursor.fetchall():
            texto = f"{c[0]} - {c[1]}"
            self.combo_cliente.addItem(texto, userData=c)
        conexion.close()

    def cargar_vendedores(self):
        """Carga los nombres de los usuarios (vendedores) desde la tabla usuarios"""
        self.combo_vendedor.clear()
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_completo FROM usuarios WHERE rol IN ('Vendedor', 'Super admin') ORDER BY nombre_completo")
        for uid, nombre in cursor.fetchall():
            self.combo_vendedor.addItem(nombre, userData=uid)
        conexion.close()
        if self.combo_vendedor.count() == 0:
            self.combo_vendedor.addItem("No hay vendedores registrados")

    def mostrar_datos_cliente(self):
        datos = self.combo_cliente.currentData()
        if datos:
            self.lbl_info_cliente.setText(f"Nombre: {datos[1]} | RFC: {datos[2]}\nDirección: {datos[3]} | Tel: {datos[4]}")
        else:
            self.lbl_info_cliente.setText("Nombre: -\nRFC: -\nDirección: -")

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
        codigo, desc, stock_maximo, um, precio = datos_prod[0], datos_prod[1], float(datos_prod[2]), datos_prod[3], float(datos_prod[4])
        
        if stock_maximo <= 0:
            QMessageBox.warning(self, "Sin Stock", f"El producto '{desc}' se encuentra agotado en inventario.")
            return

        for fila in range(self.tabla_prod.rowCount()):
            if self.tabla_prod.item(fila, 0).text() == codigo:
                spin = self.tabla_prod.cellWidget(fila, 2)
                nueva_cant = spin.value() + float(cantidad_inicial)
                if nueva_cant > stock_maximo:
                    QMessageBox.warning(self, "Stock Insuficiente", f"Solo hay {stock_maximo} disponibles. No se puede agregar más.")
                    spin.setValue(stock_maximo)
                else:
                    spin.setValue(nueva_cant)
                return

        fila = self.tabla_prod.rowCount()
        self.tabla_prod.insertRow(fila)

        # Items de texto
        items = [
            QTableWidgetItem(str(codigo)),
            QTableWidgetItem(str(desc)),
            None,  # placeholder para spin de cantidad
            QTableWidgetItem(str(um)),
            QTableWidgetItem(f"{precio:.2f}"),
            QTableWidgetItem("0.00"),
            None,  # placeholder para botón quitar
            None   # placeholder para combo disponibilidad
        ]

        for col, item in enumerate(items):
            if item:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col in [0, 3, 4, 5] else Qt.AlignLeft))
                self.tabla_prod.setItem(fila, col, item)

        # SpinBox para cantidad
        spin_cantidad = QDoubleSpinBox()
        spin_cantidad.setMinimumHeight(40) 
        spin_cantidad.setStyleSheet("font-size: 15px;")
        spin_cantidad.setRange(0.01, 99999.00) 
        val_inicial = float(cantidad_inicial)
        if val_inicial > stock_maximo: val_inicial = stock_maximo
        spin_cantidad.setValue(val_inicial)
        spin_cantidad.valueChanged.connect(lambda val, sp=spin_cantidad, mx=stock_maximo: self.validar_stock_y_actualizar(sp, mx))
        self.tabla_prod.setCellWidget(fila, 2, spin_cantidad)

        # Botón Quitar
        btn_quitar = QPushButton("❌ Quitar")
        btn_quitar.setObjectName("botonEliminar")
        btn_quitar.setMinimumHeight(35)
        btn_quitar.clicked.connect(lambda checked, f=fila: self.eliminar_fila(f))
        widget_btn = QWidget()
        layout_btn = QHBoxLayout(widget_btn)
        layout_btn.setContentsMargins(10, 5, 10, 5)
        layout_btn.addWidget(btn_quitar)
        self.tabla_prod.setCellWidget(fila, 6, widget_btn)

        # Combo para disponibilidad
        combo_disponibilidad = QComboBox()
        combo_disponibilidad.addItems(["Disponible", "Sobrepedido"])
        combo_disponibilidad.setCurrentText("Disponible")
        combo_disponibilidad.setMinimumHeight(35)
        self.tabla_prod.setCellWidget(fila, 7, combo_disponibilidad)

        self.actualizar_fila_y_totales(fila)

    def validar_stock_y_actualizar(self, spin, max_stock):
        spin.blockSignals(True)
        if spin.value() > max_stock:
            QMessageBox.warning(self, "Stock Excedido", f"El inventario actual solo cuenta con {max_stock} unidades de este producto.")
            spin.setValue(max_stock)
        spin.blockSignals(False)
        
        for fila in range(self.tabla_prod.rowCount()):
            if self.tabla_prod.cellWidget(fila, 2) == spin:
                self.actualizar_fila_y_totales(fila)
                break

    def actualizar_fila_y_totales(self, fila):
        try:
            precio = float(self.tabla_prod.item(fila, 4).text())
            cantidad = self.tabla_prod.cellWidget(fila, 2).value()
            monto = precio * cantidad
            self.tabla_prod.item(fila, 5).setText(f"{monto:.2f}")
            self.calcular_totales()
        except Exception:
            pass

    def eliminar_fila(self, fila):
        self.tabla_prod.removeRow(fila)
        self.calcular_totales()

    def calcular_totales(self):
        subtotal = 0.0
        for fila in range(self.tabla_prod.rowCount()):
            monto_str = self.tabla_prod.item(fila, 5).text()
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

        cliente_datos = self.combo_cliente.currentData()
        if not cliente_datos:
            QMessageBox.warning(self, "Error", "Debes seleccionar un cliente.")
            return

        fecha = self.input_fecha.date().toString("yyyy-MM-dd")
        folio = self.input_folio.text()
        cliente_id = cliente_datos[0]
        vendedor = self.combo_vendedor.currentText()  # Nombre del vendedor seleccionado
        oc = self.input_oc.text().strip()
        obra = self.input_obra.text().strip()
        estado = self.combo_estado.currentText()

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        try:
            if self.cotizacion_id:
                # Restaurar stock de productos anteriores
                cursor.execute("SELECT codigo_producto, cantidad FROM cotizaciones_detalle WHERE cotizacion_id=?", (self.cotizacion_id,))
                viejos_productos = cursor.fetchall()
                for v_cod, v_cant in viejos_productos:
                    cursor.execute("UPDATE inventario SET stock = stock + ? WHERE codigo_producto=?", (v_cant, v_cod))

                cursor.execute("""
                    UPDATE cotizaciones SET fecha=?, cliente_id=?, vendedor=?, oc=?, obra=?, estado=?, monto_total=?
                    WHERE id_cotizacion=?
                """, (fecha, cliente_id, vendedor, oc, obra, estado, self.monto_total_guardar, self.cotizacion_id))
                
                cursor.execute("DELETE FROM cotizaciones_detalle WHERE cotizacion_id=?", (self.cotizacion_id,))
                id_cotizacion_actual = self.cotizacion_id
            else:
                cursor.execute("""
                    INSERT INTO cotizaciones (folio, fecha, cliente_id, vendedor, oc, obra, estado, monto_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (folio, fecha, cliente_id, vendedor, oc, obra, estado, self.monto_total_guardar))
                id_cotizacion_actual = cursor.lastrowid

            # Insertar nuevo detalle
            for fila in range(self.tabla_prod.rowCount()):
                codigo = self.tabla_prod.item(fila, 0).text()
                desc = self.tabla_prod.item(fila, 1).text()
                cantidad = self.tabla_prod.cellWidget(fila, 2).value()
                um = self.tabla_prod.item(fila, 3).text()
                precio_u = float(self.tabla_prod.item(fila, 4).text())
                monto = float(self.tabla_prod.item(fila, 5).text())
                disponibilidad = self.tabla_prod.cellWidget(fila, 7).currentText()  # Obtener valor del combo

                cursor.execute("""
                    INSERT INTO cotizaciones_detalle (cotizacion_id, codigo_producto, descripcion, cantidad, um, precio_unitario, monto, disponibilidad)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (id_cotizacion_actual, codigo, desc, cantidad, um, precio_u, monto, disponibilidad))

                cursor.execute("UPDATE inventario SET stock = stock - ? WHERE codigo_producto=?", (cantidad, codigo))

            conexion.commit()
            QMessageBox.information(self, "Éxito", "Cotización guardada y stock actualizado correctamente.")
            
            # Emitir señal para actualizar inventario
            parent = self.parent()
            while parent:
                if hasattr(parent, 'productos_actualizados'):
                    parent.productos_actualizados.emit()
                    break
                parent = parent.parent()
                
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
            
            # Seleccionar cliente
            for i in range(self.combo_cliente.count()):
                datos = self.combo_cliente.itemData(i)
                if datos and datos[0] == encabezado[2]:
                    self.combo_cliente.setCurrentIndex(i)
                    break
            
            # Seleccionar vendedor por nombre
            vendedor_nombre = encabezado[3]
            index = self.combo_vendedor.findText(vendedor_nombre)
            if index >= 0:
                self.combo_vendedor.setCurrentIndex(index)
            
            self.input_oc.setText(encabezado[4] if encabezado[4] else "")
            self.input_obra.setText(encabezado[5] if encabezado[5] else "")
            self.combo_estado.setCurrentText(encabezado[6])

        # Cargar detalle incluyendo disponibilidad
        query_detalle = """
            SELECT d.codigo_producto, d.descripcion, d.cantidad, d.um, d.precio_unitario, IFNULL(i.stock, 0), d.disponibilidad
            FROM cotizaciones_detalle d
            LEFT JOIN inventario i ON d.codigo_producto = i.codigo_producto
            WHERE d.cotizacion_id=?
        """
        cursor.execute(query_detalle, (self.cotizacion_id,))
        detalles = cursor.fetchall()
        
        for det in detalles:
            cod, desc, cant_guardada, um, precio, stock_actual, disp = det
            stock_maximo_real = float(stock_actual) + float(cant_guardada)
            
            datos_prod = (cod, desc, stock_maximo_real, um, precio)
            self.agregar_producto_a_tabla(datos_prod, cant_guardada)
            
            # Establecer la disponibilidad en el combo (última fila agregada)
            fila = self.tabla_prod.rowCount() - 1
            combo = self.tabla_prod.cellWidget(fila, 7)
            if combo:
                combo.setCurrentText(disp)

        conexion.close()

# ==========================================
# 2. VISTA PRINCIPAL (HISTORIAL)
# ==========================================
class VistaCotizaciones(QWidget):
    productos_actualizados = Signal() 
    
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        titulo = QLabel("📑 Historial de Cotizaciones")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍 Buscar por ID, Folio o Cliente...")
        self.input_buscar.setFixedWidth(350)
        self.input_buscar.setMinimumHeight(40)
        self.input_buscar.textChanged.connect(self.cargar_datos)

        self.btn_crear = QPushButton("➕ Crear Cotización")
        self.btn_crear.setObjectName("botonAgregar")
        self.btn_crear.setMinimumHeight(40)
        self.btn_crear.setMinimumWidth(180)
        self.btn_crear.clicked.connect(self.crear_cotizacion)

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(self.input_buscar)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.btn_crear)
        layout.addLayout(header_layout)

        self.tabla = QTableWidget()
        columnas = ["ID", "Fecha", "Folio", "Cliente", "Vendedor", "Estado", "Monto Total", "Acciones"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        
        # Configurar el estiramiento de columnas para adaptarse al ancho de la pantalla
        header = self.tabla.horizontalHeader()
        header.setStretchLastSection(False)
        # Asignar modos de redimensionamiento
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID se ajusta al contenido
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Fecha
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Folio
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Cliente ocupa espacio extra
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Vendedor
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Estado
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Monto Total
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Acciones
        
        # Anchos mínimos para evitar que se achiquen demasiado
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

        query = """
            SELECT c.id_cotizacion, c.fecha, c.folio, cl.nombre_completo, cl.id_cliente, c.vendedor, c.estado, c.monto_total 
            FROM cotizaciones c
            JOIN clientes cl ON c.cliente_id = cl.id_cliente
            WHERE c.folio LIKE ? OR cl.nombre_completo LIKE ? OR c.id_cotizacion LIKE ?
            ORDER BY c.id_cotizacion DESC
        """
        cursor.execute(query, (filtro, filtro, filtro))
        cotizaciones = cursor.fetchall()
        conexion.close()

        self.tabla.setRowCount(len(cotizaciones))
        
        for fila, cot in enumerate(cotizaciones):
            id_cot, fecha, folio, cliente_nombre, cliente_id, vendedor, estado, monto = cot
            
            items = [
                QTableWidgetItem(f"CT{id_cot:03d}"),
                QTableWidgetItem(str(fecha)),
                QTableWidgetItem(str(folio)),
                QTableWidgetItem(f"{cliente_nombre} ({cliente_id})"),
                QTableWidgetItem(str(vendedor)),
                QTableWidgetItem(str(estado)),
                QTableWidgetItem(f"${monto:,.2f}")
            ]
            
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col in [0, 1, 2, 5, 6] else Qt.AlignLeft))
                self.tabla.setItem(fila, col, item)

            # Widget de Acciones
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
            
            btn_editar.clicked.connect(lambda checked, c_id=id_cot: self.editar_cotizacion(c_id))
            btn_pdf.clicked.connect(lambda checked, f=folio: self.generar_pdf(f))
            btn_eliminar.clicked.connect(lambda checked, c_id=id_cot, f=folio: self.eliminar_cotizacion(c_id, f))

            layout_acciones.addStretch()
            layout_acciones.addWidget(btn_editar)
            layout_acciones.addWidget(btn_pdf)
            layout_acciones.addWidget(btn_eliminar)
            layout_acciones.addStretch()
            
            self.tabla.setCellWidget(fila, 7, widget_acciones)

    def crear_cotizacion(self):
        dialogo = DialogoCotizacion(self)
        if dialogo.exec():
            self.cargar_datos()

    def editar_cotizacion(self, cotizacion_id):
        dialogo = DialogoCotizacion(self, cotizacion_id)
        if dialogo.exec():
            self.cargar_datos()

    def generar_pdf(self, folio):
        try:
            exito, mensaje_o_ruta = generar_pdf_cotizacion(folio, parent_widget=self)
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
                        QMessageBox.warning(self, "Error al abrir", f"No se pudo abrir el archivo automáticamente:\n{str(e)}\n\nPuedes encontrarlo en:\n{mensaje_o_ruta}")
            else:
                if mensaje_o_ruta != "Operación cancelada por el usuario":
                    QMessageBox.warning(self, "Error", mensaje_o_ruta)
        except Exception as e:
            QMessageBox.critical(self, "Error Fatal", f"Ocurrió un error al generar el PDF:\n{str(e)}")

    def eliminar_cotizacion(self, c_id, folio):
        respuesta = QMessageBox.question(self, "Confirmar Eliminación", 
                                         f"¿Eliminar permanentemente la cotización {folio} y RESTAURAR el stock?",
                                         QMessageBox.Yes | QMessageBox.No)
        if respuesta == QMessageBox.Yes:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("SELECT codigo_producto, cantidad FROM cotizaciones_detalle WHERE cotizacion_id=?", (c_id,))
                productos_a_devolver = cursor.fetchall()
                for cod, cant in productos_a_devolver:
                    cursor.execute("UPDATE inventario SET stock = stock + ? WHERE codigo_producto=?", (cant, cod))

                cursor.execute("DELETE FROM cotizaciones_detalle WHERE cotizacion_id=?", (c_id,))
                cursor.execute("DELETE FROM cotizaciones WHERE id_cotizacion=?", (c_id,))
                conexion.commit()
                
                self.productos_actualizados.emit()
                QMessageBox.information(self, "Éxito", "Cotización eliminada y stock restaurado.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar: {str(e)}")
            finally:
                conexion.close()
            self.cargar_datos()