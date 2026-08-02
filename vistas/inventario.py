from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QDialog, QMessageBox, QGridLayout, QComboBox, QListWidget, QListWidgetItem,
    QApplication, QCompleter, QDateEdit, QDoubleSpinBox, QSpinBox, QGroupBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QLocale, QStringListModel
import requests
from base_datos.conexion import obtener_conexion,forzar_descarga_nube,operacion_crud_nube


# ────────────────────────────────────────────────
# Diálogo para crear nueva Unidad de Medida
# ────────────────────────────────────────────────
class DialogoNuevaUM(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Unidad de Medida")
        self.setFixedSize(380, 310)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(30, 30, 30, 30)

        lbl_sigla = QLabel("Sigla (ej. m, pza, kg):")
        layout.addWidget(lbl_sigla)

        self.input_sigla = QLineEdit()
        self.input_sigla.setMinimumHeight(38)
        layout.addWidget(self.input_sigla)

        lbl_desc = QLabel("Descripción (opcional):")
        layout.addWidget(lbl_desc)

        self.input_desc = QLineEdit()
        self.input_desc.setMinimumHeight(38)
        layout.addWidget(self.input_desc)

        lbl_sat = QLabel("Clave SAT Unidad (ej. MTR, H87, E48):")
        layout.addWidget(lbl_sat)

        self.input_clave_sat = QLineEdit()
        self.input_clave_sat.setMinimumHeight(38)
        self.input_clave_sat.setPlaceholderText("Requerida para facturación CFDI 4.0")
        layout.addWidget(self.input_clave_sat)

        layout.addStretch()

        btn = QPushButton("Guardar")
        btn.setMinimumHeight(45)
        btn.clicked.connect(self.guardar)
        layout.addWidget(btn)

    def guardar(self):
        sigla = self.input_sigla.text().strip().upper()
        desc  = self.input_desc.text().strip()
        clave_sat = self.input_clave_sat.text().strip().upper() or None

        if not sigla:
            QMessageBox.warning(self, "Requerido", "La sigla es obligatoria.")
            return

        conn = obtener_conexion()
        
        # --- REGLA 2: Prevención de Colisiones (catalogo_um) ---
        try:
            resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=catalogo_um", timeout=3)
            if resp.status_code == 200:
                total_nube = resp.json().get("total", 0)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM catalogo_um")
                total_local = cursor.fetchone()[0]
                
                if total_nube > total_local:
                    QMessageBox.information(self, "Sincronizando...", "Se detectaron nuevos datos en la nube. Actualizando sistema...")
                    forzar_descarga_nube()
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Error de Red", "Se perdió la conexión. No se puede guardar.")
            conn.close()
            return
        # -------------------------------------------------------

        try:
            datos_dict = {
                "sigla": sigla,
                "descripcion": desc,
                "clave_sat_unidad": clave_sat
            }

            # --- REGLA 3: NUBE PRIMERO (Genera el ID) ---
            exito, nuevo_id_nube = operacion_crud_nube('catalogo_um', 'INSERT', datos_dict)
            if not exito: raise Exception(f"Error en la nube: {nuevo_id_nube}")

            # --- LOCAL USANDO EL ID MAESTRO DE LA NUBE ---
            cursor = conn.cursor()
            cursor.execute("INSERT INTO catalogo_um (id, sigla, descripcion, clave_sat_unidad) VALUES (?, ?, ?, ?)", (nuevo_id_nube, sigla, desc, clave_sat))
            
            conn.commit()
            self.accept()
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                QMessageBox.warning(self, "Duplicado", f"La sigla '{sigla}' ya existe.")
            else:
                QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()
# ────────────────────────────────────────────────
# Diálogo para buscar clave SAT con campo de búsqueda propio
# ────────────────────────────────────────────────
class DialogoBuscarClaveSAT(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar Clave SAT del Producto")
        self.setFixedSize(750, 500)
        self.setModal(True)
        self.clave_seleccionada = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        lbl_info = QLabel("Escribe un término genérico para buscar la clave SAT:")
        lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_info)

        lbl_tip = QLabel("💡 Usa palabras simples: cable, interruptor, tubo, conector, motor, etc.")
        lbl_tip.setStyleSheet("color: #718096; font-size: 11px; font-style: italic;")
        layout.addWidget(lbl_tip)

        # Campo de búsqueda
        buscar_layout = QHBoxLayout()
        self.input_busqueda = QLineEdit()
        self.input_busqueda.setMinimumHeight(40)
        self.input_busqueda.setPlaceholderText("Escribe aquí para buscar... (Ej: cable, interruptor, contacto)")
        self.input_busqueda.returnPressed.connect(self.ejecutar_busqueda)
        buscar_layout.addWidget(self.input_busqueda, stretch=1)

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.setMinimumHeight(40)
        btn_buscar.setMinimumWidth(100)
        btn_buscar.clicked.connect(self.ejecutar_busqueda)
        buscar_layout.addWidget(btn_buscar)
        layout.addLayout(buscar_layout)

        # Tabla de resultados
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["Clave", "Descripción"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
        """)
        self.tabla.doubleClicked.connect(self.seleccionar)
        layout.addWidget(self.tabla)

        # Label de estado
        self.lbl_estado = QLabel("")
        self.lbl_estado.setStyleSheet("color: #718096;")
        layout.addWidget(self.lbl_estado)

        # Botón seleccionar
        btn_seleccionar = QPushButton("✅ Seleccionar")
        btn_seleccionar.setObjectName("botonPrincipal")
        btn_seleccionar.setMinimumHeight(45)
        btn_seleccionar.clicked.connect(self.seleccionar)
        layout.addWidget(btn_seleccionar)

        # Enfocar el campo de búsqueda al abrir
        self.input_busqueda.setFocus()

    def ejecutar_busqueda(self):
        """Ejecuta la búsqueda en la API de Facturama"""
        termino = self.input_busqueda.text().strip()
        if not termino:
            return

        self.lbl_estado.setText("Buscando...")
        self.tabla.setRowCount(0)
        QApplication.processEvents()

        FACTURAMA_USER = "ProElectro"
        FACTURAMA_PASS = "Proelectro123"
        FACTURAMA_URL = "https://apisandbox.facturama.mx"

        try:
            url = f"{FACTURAMA_URL}/api/Catalogs/ProductsOrServices?keyword={termino}"
            resp = requests.get(url, auth=(FACTURAMA_USER, FACTURAMA_PASS), timeout=10)

            if resp.status_code == 200:
                resultados = resp.json()
                if not resultados:
                    self.lbl_estado.setText(f"Sin resultados para '{termino}'. Intenta con otro término.")
                    return

                # Mostrar máximo 50
                mostrar = resultados[:50]
                self.tabla.setRowCount(len(mostrar))
                for fila, item in enumerate(mostrar):
                    clave = item.get("Value", "")
                    desc = item.get("Name", "")
                    self.tabla.setItem(fila, 0, QTableWidgetItem(str(clave)))
                    item_desc = QTableWidgetItem(str(desc))
                    item_desc.setToolTip(str(desc))
                    self.tabla.setItem(fila, 1, item_desc)

                self.lbl_estado.setText(f"{len(resultados)} resultado(s) encontrados." + 
                                       (" Mostrando los primeros 50." if len(resultados) > 50 else ""))
            elif resp.status_code == 401:
                self.lbl_estado.setText("Error de autenticación. Contacta al desarrollador.")
            else:
                self.lbl_estado.setText(f"Error del servidor ({resp.status_code}).")
        except requests.exceptions.RequestException:
            self.lbl_estado.setText("Sin conexión. Verifica tu internet.")

    def seleccionar(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.clave_seleccionada = self.tabla.item(fila, 0).text()
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Selecciona una clave de la lista.")


# ────────────────────────────────────────────────
# Diálogo para seleccionar clave SAT del catálogo
# ────────────────────────────────────────────────
class DialogoSeleccionarClaveSAT(QDialog):
    def __init__(self, parent=None, resultados=[]):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Clave SAT del Producto")
        self.setFixedSize(700, 450)
        self.setModal(True)
        self.clave_seleccionada = None
        self.resultados = resultados

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        lbl_info = QLabel("Selecciona la clave SAT que mejor describa tu producto:")
        lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_info)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["Clave", "Descripción"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("""
            QTableWidget { alternate-background-color: #F9FAFB; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
        """)
        layout.addWidget(self.tabla)

        # Llenar tabla (máximo 50 resultados para no saturar)
        mostrar = resultados[:50]
        self.tabla.setRowCount(len(mostrar))
        for fila, item in enumerate(mostrar):
            clave = item.get("Value", "") if isinstance(item, dict) else str(item[0]) if isinstance(item, (list, tuple)) else ""
            desc = item.get("Name", "") if isinstance(item, dict) else str(item[1]) if isinstance(item, (list, tuple)) else ""
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(clave)))
            item_desc = QTableWidgetItem(str(desc))
            item_desc.setToolTip(str(desc))
            self.tabla.setItem(fila, 1, item_desc)

        if len(resultados) > 50:
            lbl_nota = QLabel(f"Mostrando 50 de {len(resultados)} resultados. Usa una búsqueda más específica.")
            lbl_nota.setStyleSheet("color: #718096; font-style: italic;")
            layout.addWidget(lbl_nota)

        btn_seleccionar = QPushButton("✅ Seleccionar")
        btn_seleccionar.setObjectName("botonPrincipal")
        btn_seleccionar.setMinimumHeight(45)
        btn_seleccionar.clicked.connect(self.seleccionar)
        layout.addWidget(btn_seleccionar)

    def seleccionar(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.clave_seleccionada = self.tabla.item(fila, 0).text()
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Selecciona una clave de la lista.")


# ────────────────────────────────────────────────
# Diálogo para asignar clave SAT a múltiples productos
# ────────────────────────────────────────────────
class DialogoAsignarClaveMasiva(QDialog):
    def __init__(self, parent=None, clave_sat=""):
        super().__init__(parent)
        self.clave_sat = clave_sat
        self.setWindowTitle(f"Asignar Clave SAT: {clave_sat}")
        self.setFixedSize(750, 550)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        lbl_titulo = QLabel(f"Asignar clave SAT '{clave_sat}' a múltiples productos")
        lbl_titulo.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_titulo)

        # Buscador
        buscar_layout = QHBoxLayout()
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍 Buscar por código o descripción...")
        self.input_buscar.setMinimumHeight(38)
        self.input_buscar.textChanged.connect(self.filtrar_productos)
        buscar_layout.addWidget(self.input_buscar)

        btn_seleccionar_todos = QPushButton("☑️ Seleccionar todos")
        btn_seleccionar_todos.setFixedHeight(38)
        btn_seleccionar_todos.clicked.connect(self.seleccionar_todos)
        buscar_layout.addWidget(btn_seleccionar_todos)
        layout.addLayout(buscar_layout)

        # Tabla con checkboxes
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["✓", "Código", "Descripción", "Clave SAT Actual"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("QTableWidget { alternate-background-color: #F9FAFB; }")
        layout.addWidget(self.tabla)

        # Botón guardar
        btn_guardar = QPushButton(f"💾 Asignar clave '{clave_sat}' a los seleccionados")
        btn_guardar.setObjectName("botonPrincipal")
        btn_guardar.setMinimumHeight(48)
        btn_guardar.clicked.connect(self.guardar_masivo)
        layout.addWidget(btn_guardar)

        # Cargar productos sin clave SAT o con clave diferente
        self.todos_productos = []
        self.cargar_productos()

    def cargar_productos(self):
        """Carga productos que NO tienen esta clave SAT asignada"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, codigo_producto, descripcion, clave_sat_producto 
            FROM inventario 
            WHERE clave_sat_producto IS NULL OR clave_sat_producto != ?
            ORDER BY descripcion
        """, (self.clave_sat,))
        self.todos_productos = cursor.fetchall()
        conn.close()
        self.mostrar_productos(self.todos_productos)

    def mostrar_productos(self, productos):
        self.tabla.setRowCount(len(productos))
        for fila, (pid, codigo, desc, clave_actual) in enumerate(productos):
            # Checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked)
            chk.setData(Qt.UserRole, pid)
            self.tabla.setItem(fila, 0, chk)

            self.tabla.setItem(fila, 1, QTableWidgetItem(codigo))
            item_desc = QTableWidgetItem(desc)
            item_desc.setToolTip(desc)
            self.tabla.setItem(fila, 2, item_desc)
            self.tabla.setItem(fila, 3, QTableWidgetItem(clave_actual or "— Sin clave —"))

    def filtrar_productos(self):
        texto = self.input_buscar.text().strip().lower()
        if not texto:
            self.mostrar_productos(self.todos_productos)
        else:
            filtrados = [p for p in self.todos_productos if texto in p[1].lower() or texto in p[2].lower()]
            self.mostrar_productos(filtrados)

    def seleccionar_todos(self):
        for fila in range(self.tabla.rowCount()):
            self.tabla.item(fila, 0).setCheckState(Qt.Checked)

    def guardar_masivo(self):
        """Asigna la clave SAT a todos los productos seleccionados"""
        seleccionados = []
        for fila in range(self.tabla.rowCount()):
            item = self.tabla.item(fila, 0)
            if item.checkState() == Qt.Checked:
                pid = item.data(Qt.UserRole)
                seleccionados.append(pid)

        if not seleccionados:
            QMessageBox.warning(self, "Aviso", "Selecciona al menos un producto.")
            return

        respuesta = QMessageBox.question(self, "Confirmar",
            f"¿Asignar la clave SAT '{self.clave_sat}' a {len(seleccionados)} producto(s)?",
            QMessageBox.Yes | QMessageBox.No)
        
        if respuesta == QMessageBox.No:
            return

        conn = obtener_conexion()
        cursor = conn.cursor()
        errores = []

        for pid in seleccionados:
            try:
                # Actualizar en la nube
                exito, msj = operacion_crud_nube('inventario', 'UPDATE', {"clave_sat_producto": self.clave_sat}, pid)
                if not exito:
                    errores.append(f"Producto ID {pid}: {msj}")
                    continue
                # Actualizar local
                cursor.execute("UPDATE inventario SET clave_sat_producto = ? WHERE id = ?", (self.clave_sat, pid))
            except Exception as e:
                errores.append(f"Producto ID {pid}: {str(e)}")

        conn.commit()
        conn.close()

        if errores:
            QMessageBox.warning(self, "Parcialmente completado",
                f"Se asignaron {len(seleccionados) - len(errores)} de {len(seleccionados)} productos.\n\nErrores:\n" + "\n".join(errores[:5]))
        else:
            QMessageBox.information(self, "Éxito", f"✅ Clave SAT '{self.clave_sat}' asignada a {len(seleccionados)} producto(s).")
        
        self.accept()


# ────────────────────────────────────────────────
# Diálogo para agregar / editar producto
# ────────────────────────────────────────────────
class DialogoProducto(QDialog):
    def __init__(self, parent=None, producto_datos=None):
        super().__init__(parent)
        self.producto_id = producto_datos[0] if producto_datos else None
        titulo = "Editar Producto" if self.producto_id else "Nuevo Producto"
        self.setWindowTitle(titulo)
        self.setFixedSize(850, 540)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(35, 30, 35, 30)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)

        campos = [
            ("Código:",          "input_codigo",   0, 0, producto_datos[1] if producto_datos else ""),
            ("Descripción:",     "input_desc",     0, 2, producto_datos[2] if producto_datos else ""),
            ("Stock:",           "input_stock",    1, 0, str(int(producto_datos[3])) if producto_datos else "0"),
            ("Marca:",           "input_marca",     2, 0, producto_datos[6] if producto_datos else ""),
            ("Precio Compra ($):","input_compra",   3, 0, str(producto_datos[7]) if producto_datos else "0.00"),
            ("Precio Venta ($):", "input_venta",    3, 2, str(producto_datos[8]) if producto_datos else "0.00"),
        ]

        for texto, attr, r, c, valor in campos:
            lbl = QLabel(texto)
            lbl.setObjectName("labelTitulo")
            grid.addWidget(lbl, r, c)

            edit = QLineEdit(valor)
            edit.setMinimumHeight(38)
            setattr(self, attr, edit)
            grid.addWidget(edit, r, c + 1)

        # Unidad de Medida + botón nueva
        lbl_um = QLabel("Unidad de Medida:")
        lbl_um.setObjectName("labelTitulo")
        grid.addWidget(lbl_um, 1, 2)

        um_layout = QHBoxLayout()
        um_layout.setSpacing(10)

        self.combo_um = QComboBox()
        self.combo_um.setMinimumHeight(38)
        self.cargar_unidades_medida()
        if producto_datos and producto_datos[4]:
            index = self.combo_um.findText(producto_datos[4], Qt.MatchFixedString)
            if index >= 0:
                self.combo_um.setCurrentIndex(index)

        btn_gestion = QPushButton("Gestionar UM")
        btn_gestion.setFixedHeight(38)
        btn_gestion.setMinimumWidth(140)
        btn_gestion.clicked.connect(lambda: self.abrir_gestion_um())

        um_layout.addWidget(self.combo_um, stretch=1)
        um_layout.addWidget(btn_gestion)
        grid.addLayout(um_layout, 1, 3)

        # Proveedor
        lbl_prov = QLabel("Proveedor:")
        lbl_prov.setObjectName("labelTitulo")
        grid.addWidget(lbl_prov, 2, 2)

        self.combo_prov = QComboBox()
        self.combo_prov.setMinimumHeight(38)
        self.cargar_proveedores()
        if producto_datos and producto_datos[5]:
            idx = self.combo_prov.findData(producto_datos[5])
            if idx >= 0:
                self.combo_prov.setCurrentIndex(idx)
        grid.addWidget(self.combo_prov, 2, 3)

        # Clave SAT Producto (para facturación CFDI 4.0)
        lbl_sat = QLabel("Clave SAT Producto:")
        lbl_sat.setObjectName("labelTitulo")
        grid.addWidget(lbl_sat, 4, 0)

        sat_layout = QHBoxLayout()
        sat_layout.setSpacing(8)
        self.input_clave_sat = QLineEdit(producto_datos[9] if producto_datos and len(producto_datos) > 9 and producto_datos[9] else "")
        self.input_clave_sat.setMinimumHeight(38)
        self.input_clave_sat.setMinimumWidth(200)
        self.input_clave_sat.setMaxLength(8)
        self.input_clave_sat.setPlaceholderText("8 dígitos. Ej: 26121600")
        sat_layout.addWidget(self.input_clave_sat, stretch=1)

        btn_buscar_sat = QPushButton("🔍 Buscar")
        btn_buscar_sat.setFixedHeight(38)
        btn_buscar_sat.setMinimumWidth(90)
        btn_buscar_sat.setToolTip("Buscar clave SAT por descripción del producto")
        btn_buscar_sat.clicked.connect(self.buscar_clave_sat)
        sat_layout.addWidget(btn_buscar_sat)

        btn_asignar_masivo = QPushButton("📋 Asignar a otros")
        btn_asignar_masivo.setFixedHeight(38)
        btn_asignar_masivo.setMinimumWidth(120)
        btn_asignar_masivo.setToolTip("Asignar esta misma clave SAT a otros productos")
        btn_asignar_masivo.clicked.connect(self.asignar_clave_masiva)
        sat_layout.addWidget(btn_asignar_masivo)

        grid.addLayout(sat_layout, 4, 1, 1, 3)

        # Combo de categorías SAT pre-cargadas (material eléctrico) con búsqueda
        lbl_cat_sat = QLabel("Categoría SAT:")
        lbl_cat_sat.setObjectName("labelTitulo")
        grid.addWidget(lbl_cat_sat, 5, 0)

        self.combo_categoria_sat = QComboBox()
        self.combo_categoria_sat.setMinimumHeight(38)
        self.combo_categoria_sat.setEditable(True)
        self.combo_categoria_sat.setInsertPolicy(QComboBox.NoInsert)
        self.combo_categoria_sat.lineEdit().setPlaceholderText("Escribe para buscar categoría...")
        self.combo_categoria_sat.addItem("", "")
        
        # Catálogo de categorías SAT para material eléctrico (Pro Electro)
        categorias_sat = [
            ("26121600", "Cables eléctricos y accesorios"),
            ("26121500", "Alambre eléctrico"),
            ("39122200", "Interruptores eléctricos y accesorios"),
            ("39121529", "Contactores"),
            ("39121500", "Conmutadores, controles, relés y accesorios"),
            ("39121100", "Centros de control, distribución y accesorios"),
            ("39121001", "Transformadores de distribución de potencia"),
            ("39121700", "Ferretería eléctrica y suministros"),
            ("39121400", "Conectores, terminales y lengüetas eléctricas"),
            ("39131714", "Canaletas para cables"),
            ("39131715", "Conducto/manguera flexible (Liquid Tight)"),
            ("39101600", "Lámparas y bombillas"),
            ("39111611", "Reflectores de iluminación"),
            ("26111700", "Motores eléctricos"),
            ("39121300", "Cuadros, registros y fusibles eléctricos"),
            ("31161700", "Tuercas y rondanas"),
            ("31161500", "Tornillos"),
            ("27112100", "Abrazaderas y herramientas de sujeción"),
            ("31201500", "Cinta adhesiva/aislante"),
            ("39121400", "Enchufes, clavijas y contactos"),
            ("30191800", "Gabinetes y cajas eléctricas"),
            ("40171500", "Tuberías (conduit, PVC)"),
            ("26131700", "Cajas de conexión y registro"),
            ("39121111", "Tableros de fusibles"),
            ("41113600", "Instrumentos de medición (multímetros)"),
            ("27111700", "Herramientas manuales"),
            ("31162906", "Abrazaderas de manguera o tubo"),
            ("31162800", "Varillas roscadas"),
            ("39101900", "Balastos y transformadores de lámparas"),
            ("26101600", "Generadores eléctricos"),
        ]
        
        for clave, descripcion in categorias_sat:
            self.combo_categoria_sat.addItem(f"{clave} - {descripcion}", clave)
        
        # Habilitar filtrado mientras se escribe
        items_texto = [f"{c} - {d}" for c, d in categorias_sat]
        completer = QCompleter(items_texto)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.combo_categoria_sat.setCompleter(completer)
        
        self.combo_categoria_sat.currentIndexChanged.connect(self.seleccionar_categoria_sat)
        grid.addWidget(self.combo_categoria_sat, 5, 1, 1, 3)

        layout.addLayout(grid)
        layout.addStretch()

        btn_guardar = QPushButton("Guardar Cambios" if self.producto_id else "Crear Producto")
        btn_guardar.setObjectName("botonPrincipal")
        btn_guardar.setMinimumHeight(48)
        btn_guardar.clicked.connect(self.guardar)
        layout.addWidget(btn_guardar, alignment=Qt.AlignCenter)

    def seleccionar_categoria_sat(self, index):
        """Al seleccionar una categoría del combo, llena automáticamente el campo de clave SAT"""
        clave = self.combo_categoria_sat.currentData()
        if clave:
            self.input_clave_sat.setText(clave)

    def buscar_clave_sat(self):
        """Abre diálogo de búsqueda de claves SAT con su propio campo de texto"""
        dialogo = DialogoBuscarClaveSAT(self)
        if dialogo.exec():
            self.input_clave_sat.setText(dialogo.clave_seleccionada)

    def asignar_clave_masiva(self):
        """Abre un diálogo para asignar la clave SAT actual a múltiples productos"""
        clave = self.input_clave_sat.text().strip()
        if not clave or len(clave) != 8:
            QMessageBox.warning(self, "Aviso", "Primero ingresa o busca una clave SAT válida (8 dígitos) para poder asignarla a otros productos.")
            return
        
        dialogo = DialogoAsignarClaveMasiva(self, clave)
        dialogo.exec()

    def cargar_unidades_medida(self):
        """Carga las unidades de medida en el combobox"""
        self.combo_um.clear()
        conn = obtener_conexion()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT sigla FROM catalogo_um ORDER BY sigla")
            siglas = [row[0] for row in cursor.fetchall()]
            
            # Agregar opción "S/U" (Sin Unidad) como primera opción
            self.combo_um.addItem("S/U")
            
            # Agregar las unidades registradas
            for sigla in siglas:
                self.combo_um.addItem(sigla)
            
            print(f"📊 Unidades cargadas: {siglas}")  # Depuración
            
            # Si no hay unidades registradas
            if not siglas:
                self.combo_um.addItem("— Sin unidades —")
                
        except Exception as e:
            print(f"❌ Error cargando UM: {e}")
            self.combo_um.addItem("S/U")  # Opción por defecto
        finally:
            conn.close()
    def abrir_gestion_um(self):
        """Abre el diálogo de gestión de unidades de medida"""
        dialogo = DialogoGestionUM(self)
        if dialogo.exec():
            self.cargar_unidades_medida()

    def abrir_dialogo_nueva_um(self):
        if DialogoNuevaUM(self).exec():
            self.cargar_unidades_medida()

    def cargar_proveedores(self):
        self.combo_prov.clear()
        
        # --- OPCIÓN POR DEFECTO ---
        self.combo_prov.addItem("— Sin Proveedor —", None)
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id_prov, nombre_empresa FROM proveedores ORDER BY nombre_empresa")
        for pid, nombre in cursor.fetchall():
            self.combo_prov.addItem(f"{nombre}  ({pid})", pid)
        conn.close()
        
    def guardar(self):
        codigo = self.input_codigo.text().strip()
        desc   = self.input_desc.text().strip()
        if not codigo or not desc:
            QMessageBox.warning(self, "Requeridos", "Código y Descripción son obligatorios.")
            return

        stock = int(float(self.input_stock.text().strip() or 0)) 
        compra = float(self.input_compra.text().strip() or 0)
        venta  = float(self.input_venta.text().strip() or 0)
        um = self.combo_um.currentText()
        prov_id = self.combo_prov.currentData()
        marca = self.input_marca.text().strip()
        clave_sat = self.input_clave_sat.text().strip() or None

        datos_dict = {"codigo_producto": codigo, "descripcion": desc, "stock": stock, "um": um, "proveedor_id": prov_id, "marca": marca, "precio_compra": compra, "precio_venta": venta, "clave_sat_producto": clave_sat}

        conn = obtener_conexion()
        cursor = conn.cursor()
        
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except:
            QMessageBox.warning(self, "Error de Red", "Se perdió la conexión.")
            conn.close()
            return

        # --- REGLA 2: Prevención de Colisiones ---
        try:
            resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=inventario", timeout=3)
            if resp.status_code == 200:
                total_nube = resp.json().get("total", 0)
                cursor.execute("SELECT COUNT(*) FROM inventario")
                total_local = cursor.fetchone()[0]
                if total_nube > total_local:
                    QMessageBox.information(self, "Sincronizando...", "Se detectaron nuevos datos en la nube. Actualizando...")
                    forzar_descarga_nube()
        except:
            pass
        # -----------------------------------------

        try:
            if self.producto_id:
                exito, msj = operacion_crud_nube('inventario', 'UPDATE', datos_dict, self.producto_id)
                if not exito: raise Exception(msj)

                cursor.execute("PRAGMA foreign_keys = OFF;")
                
                cursor.execute("SELECT codigo_producto FROM inventario WHERE id=?", (self.producto_id,))
                codigo_viejo = cursor.fetchone()[0]
                if codigo_viejo != codigo:
                    cursor.execute("UPDATE cotizaciones_detalle SET codigo_producto=? WHERE codigo_producto=?", (codigo, codigo_viejo))

                cursor.execute("UPDATE inventario SET codigo_producto=?, descripcion=?, stock=?, um=?, proveedor_id=?, marca=?, precio_compra=?, precio_venta=?, clave_sat_producto=? WHERE id=?", 
                               (codigo, desc, stock, um, prov_id, marca, compra, venta, clave_sat, self.producto_id))
                
                cursor.execute("PRAGMA foreign_keys = ON;")
            else:
                exito, nuevo_id = operacion_crud_nube('inventario', 'INSERT', datos_dict)
                if not exito: raise Exception(nuevo_id)
                cursor.execute("INSERT INTO inventario (id, codigo_producto, descripcion, stock, um, proveedor_id, marca, precio_compra, precio_venta, clave_sat_producto) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                               (nuevo_id, codigo, desc, stock, um, prov_id, marca, compra, venta, clave_sat))
                
            conn.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()

# Diálogo para gestionar (ver + eliminar) UM
# ────────────────────────────────────────────────
# ────────────────────────────────────────────────
# Diálogo para gestionar (ver + editar + eliminar) UM
# ────────────────────────────────────────────────
class DialogoGestionUM(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Unidades de Medida")
        self.resize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Botón nueva UM arriba
        btn_nueva = QPushButton("➕ Nueva Unidad de Medida")
        btn_nueva.setMinimumHeight(42)
        btn_nueva.setObjectName("botonAgregar")
        btn_nueva.clicked.connect(self.agregar_nueva_um)
        layout.addWidget(btn_nueva)

        # Tabla para mostrar las UM
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["Sigla", "Descripción", "Editar", "Eliminar"])
        
        # Configurar la tabla
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().setDefaultSectionSize(50)
        self.tabla.setAlternatingRowColors(True)
        
        self.tabla.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
        """)
        
        layout.addWidget(self.tabla, stretch=1)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setMinimumHeight(42)
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.cargar_tabla()

    def cargar_tabla(self):
        """Carga las unidades de medida en la tabla con botones de editar y eliminar"""
        self.tabla.setRowCount(0)
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sigla, descripcion, clave_sat_unidad 
            FROM catalogo_um 
            ORDER BY sigla
        """)
        unidades = cursor.fetchall()
        conn.close()

        self.tabla.setRowCount(len(unidades))

        for fila, (uid, sigla, descripcion, clave_sat) in enumerate(unidades):
            # Item de Sigla
            item_sigla = QTableWidgetItem(sigla)
            item_sigla.setFlags(item_sigla.flags() & ~Qt.ItemIsEditable)
            item_sigla.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, 0, item_sigla)
            
            # Item de Descripción
            item_desc = QTableWidgetItem(descripcion if descripcion else "")
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 1, item_desc)
            
            # Botón Editar
            btn_editar = QPushButton("✏️ Editar")
            btn_editar.setObjectName("botonEditar")
            btn_editar.setFixedSize(90, 32)
            btn_editar.clicked.connect(lambda checked, u=uid, s=sigla, d=descripcion, c=clave_sat: 
                                      self.editar_um(u, s, d, c))
            self.tabla.setCellWidget(fila, 2, btn_editar)
            
            # Botón Eliminar
            btn_eliminar = QPushButton("🗑️ Eliminar")
            btn_eliminar.setObjectName("botonEliminar")
            btn_eliminar.setFixedSize(90, 32)
            btn_eliminar.clicked.connect(lambda checked, u=uid, s=sigla: 
                                        self.eliminar_um(u, s))
            self.tabla.setCellWidget(fila, 3, btn_eliminar)

    def agregar_nueva_um(self):
        """Abre el diálogo para crear nueva unidad de medida"""
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar.")
            return
        # ------------------------------------------
        dialogo = DialogoNuevaUM(self)
        if dialogo.exec():
            self.cargar_tabla()
            

    def editar_um(self, uid, sigla_actual, descripcion_actual, clave_sat_actual=""):
        """Abre diálogo para editar una unidad de medida"""
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar.")
            return
        # ------------------------------------------
        dialogo = DialogoEditarUM(self, uid, sigla_actual, descripcion_actual, clave_sat_actual or "")
        if dialogo.exec():
            self.cargar_tabla()
            

    def eliminar_um(self, uid, sigla):
        """Elimina una unidad de medida y actualiza productos afectados usando Online-First"""
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar.")
            return

        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM inventario WHERE um = ?", (sigla,))
        count_productos = cursor.fetchone()[0]
        conn.close()
        
        mensaje = f"¿Eliminar la unidad '{sigla}'?"
        if count_productos > 0:
            mensaje += f"\n\n📊 {count_productos} producto(s) utilizan esta UM.\nSe establecerán con valor 'S/U' (Sin Unidad)."
        
        if QMessageBox.question(self, "Confirmar eliminación", mensaje, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            # --- ONLINE FIRST ---
            conn = obtener_conexion()
            cursor = conn.cursor()
            try:
                # 1. Actualizar productos en la nube
                cursor.execute("SELECT id FROM inventario WHERE um = ?", (sigla,))
                productos_afectados = cursor.fetchall()
                
                for (p_id,) in productos_afectados:
                    # Mandamos un UPDATE parcial solo del campo 'um'
                    exito_p, msj_p = operacion_crud_nube('inventario', 'UPDATE', {"um": "S/U"}, p_id)
                    if not exito_p: raise Exception(f"Fallo en nube al actualizar prod {p_id}: {msj_p}")
                
                # 2. Eliminar UM en la nube
                exito, mensaje_api = operacion_crud_nube('catalogo_um', 'DELETE', registro_id=uid)
                if not exito: raise Exception(f"Fallo en nube al eliminar UM: {mensaje_api}")
                
                # --- CASCADA LOCAL ---
                cursor.execute("UPDATE inventario SET um = 'S/U' WHERE um = ?", (sigla,))
                cursor.execute("DELETE FROM catalogo_um WHERE id = ?", (uid,))
                conn.commit()
                self.cargar_tabla()
                QMessageBox.information(self, "Éxito", f"Unidad '{sigla}' eliminada.\n{count_productos} producto(s) actualizados a 'S/U'.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            finally:
                conn.close()

# ────────────────────────────────────────────────
# Diálogo para editar Unidad de Medida
# ────────────────────────────────────────────────
class DialogoEditarUM(QDialog):
    def __init__(self, parent=None, uid=None, sigla_actual="", descripcion_actual="", clave_sat_actual=""):
        super().__init__(parent)
        self.uid = uid
        self.sigla_actual = sigla_actual
        self.setWindowTitle(f"Editar Unidad de Medida: {sigla_actual}")
        self.setFixedSize(380, 330)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(30, 30, 30, 30)

        # Sigla
        lbl_sigla = QLabel("Sigla:")
        lbl_sigla.setObjectName("labelTitulo")
        layout.addWidget(lbl_sigla)

        self.input_sigla = QLineEdit(sigla_actual)
        self.input_sigla.setMinimumHeight(38)
        self.input_sigla.setPlaceholderText("ej. m, pza, kg")
        layout.addWidget(self.input_sigla)

        # Descripción
        lbl_desc = QLabel("Descripción:")
        lbl_desc.setObjectName("labelTitulo")
        layout.addWidget(lbl_desc)

        self.input_desc = QLineEdit(descripcion_actual if descripcion_actual else "")
        self.input_desc.setMinimumHeight(38)
        self.input_desc.setPlaceholderText("Descripción opcional")
        layout.addWidget(self.input_desc)

        # Clave SAT Unidad
        lbl_sat = QLabel("Clave SAT Unidad:")
        lbl_sat.setObjectName("labelTitulo")
        layout.addWidget(lbl_sat)

        self.input_clave_sat = QLineEdit(clave_sat_actual if clave_sat_actual else "")
        self.input_clave_sat.setMinimumHeight(38)
        self.input_clave_sat.setPlaceholderText("Ej: MTR, H87, E48 (para facturación)")
        layout.addWidget(self.input_clave_sat)

        layout.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setMinimumHeight(40)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_guardar = QPushButton("Guardar Cambios")
        btn_guardar.setObjectName("botonPrincipal")
        btn_guardar.setMinimumHeight(40)
        btn_guardar.clicked.connect(self.guardar)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)
        layout.addLayout(btn_layout)

    def guardar(self):
        nueva_sigla = self.input_sigla.text().strip().upper()
        nueva_desc = self.input_desc.text().strip()
        nueva_clave_sat = self.input_clave_sat.text().strip().upper() or None

        if not nueva_sigla:
            QMessageBox.warning(self, "Requerido", "La sigla es obligatoria.")
            return

        conn = obtener_conexion()

        # --- REGLA 2: Prevención de Colisiones ---
        try:
            resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=catalogo_um", timeout=3)
            if resp.status_code == 200:
                total_nube = resp.json().get("total", 0)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM catalogo_um")
                total_local = cursor.fetchone()[0]
                
                if total_nube > total_local:
                    QMessageBox.information(self, "Sincronizando...", "Se detectaron nuevos datos en la nube. Actualizando sistema...")
                    forzar_descarga_nube()
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Error de Red", "Se perdió la conexión. No se puede guardar.")
            conn.close()
            return
        # -----------------------------------------

        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM catalogo_um WHERE sigla = ? AND id != ?", 
                          (nueva_sigla, self.uid))
            if cursor.fetchone():
                QMessageBox.warning(self, "Duplicado", f"La sigla '{nueva_sigla}' ya existe.")
                return

            cursor.execute("""
                SELECT id, codigo_producto, descripcion, stock, proveedor_id, marca, precio_compra, precio_venta 
                FROM inventario WHERE um = ?
            """, (self.sigla_actual,))
            productos_afectados = cursor.fetchall()

            # --- REGLA 3: NUBE PRIMERO (Cascada) ---
            # 1. Actualizar la tabla catalogo_um en la nube
            um_dict = {"sigla": nueva_sigla, "descripcion": nueva_desc, "clave_sat_unidad": nueva_clave_sat}
            exito_um, msj_um = operacion_crud_nube('catalogo_um', 'UPDATE', um_dict, self.uid)
            if not exito_um: raise Exception(f"Error actualizando UM en la nube: {msj_um}")

            # 2. Actualizar productos afectados en la nube
            for prod in productos_afectados:
                p_id, p_codigo, p_desc, p_stock, p_prov_id, p_marca, p_compra, p_venta = prod
                prod_dict = {
                    "codigo_producto": p_codigo, "descripcion": p_desc, "stock": p_stock,
                    "um": nueva_sigla, "proveedor_id": p_prov_id, "marca": p_marca,
                    "precio_compra": p_compra, "precio_venta": p_venta
                }
                exito_p, msj_p = operacion_crud_nube('inventario', 'UPDATE', prod_dict, p_id)
                if not exito_p: raise Exception(f"Error actualizando prod. {p_codigo} en la nube: {msj_p}")

            # --- LOCAL DESPUÉS DEL ÉXITO EN LA NUBE ---
            cursor.execute("""
                UPDATE catalogo_um SET sigla = ?, descripcion = ?, clave_sat_unidad = ? WHERE id = ?
            """, (nueva_sigla, nueva_desc, nueva_clave_sat, self.uid))
            
            cursor.execute("""
                UPDATE inventario SET um = ? WHERE um = ?
            """, (nueva_sigla, self.sigla_actual))
            
            conn.commit()
            self.accept()
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()

class DialogoSeleccionarProveedor(QDialog):
    def __init__(self, parent=None, resultados=[]):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Proveedor")
        self.setFixedSize(600, 350)
        self.setModal(True)
        self.proveedor_seleccionado = None
        self.resultados = resultados

        layout = QVBoxLayout(self)
        lbl_info = QLabel("Selecciona el proveedor correcto:")
        layout.addWidget(lbl_info)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["ID", "Empresa"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.tabla)

        self.tabla.setRowCount(len(resultados))
        for fila, prov in enumerate(resultados):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(prov[0])))
            self.tabla.setItem(fila, 1, QTableWidgetItem(str(prov[1])))

        btn = QPushButton("Seleccionar")
        btn.clicked.connect(self.seleccionar)
        layout.addWidget(btn)

    def seleccionar(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.proveedor_seleccionado = self.resultados[fila]
            self.accept()

class DialogoAgregarHistorial(QDialog):
    def __init__(self, parent=None, cod_prod="", desc_prod="", hist_id=None, usuario_actual=""):
        super().__init__(parent)
        self.hist_id = hist_id
        self.cod_prod = cod_prod
        self.usuario_actual = usuario_actual
        self.setWindowTitle("Nuevo Historial de Compra" if not hist_id else "Editar Historial")
        self.setFixedSize(650, 500)
        self.setModal(True)
        self.proveedor_seleccionado = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # Info del Producto
        lbl_prod = QLabel(f"<b>Producto:</b> {cod_prod} - {desc_prod}")
        lbl_prod.setStyleSheet("font-size: 14px; color: #2B6CB0; background-color: #EBF8FF; padding: 10px; border-radius: 5px;")
        layout.addWidget(lbl_prod)

        grid = QGridLayout()
        grid.setSpacing(15)

        # Buscador Proveedor
        grid.addWidget(QLabel("Buscar Proveedor (Enter):"), 0, 0)
        lay_prov = QHBoxLayout()
        self.input_buscar_prov = QLineEdit()
        self.input_buscar_prov.setPlaceholderText("ID o Nombre...")
        self.input_buscar_prov.setMinimumHeight(38)
        self.input_buscar_prov.returnPressed.connect(self.buscar_proveedor)
        btn_buscar_prov = QPushButton("Buscar")
        btn_buscar_prov.setAutoDefault(False)
        btn_buscar_prov.clicked.connect(self.buscar_proveedor)
        lay_prov.addWidget(self.input_buscar_prov)
        lay_prov.addWidget(btn_buscar_prov)
        grid.addLayout(lay_prov, 0, 1)

        self.lbl_info_prov = QLabel("ID: - | Empresa: -")
        self.lbl_info_prov.setStyleSheet("color: #4A5568; font-weight: bold;")
        grid.addWidget(self.lbl_info_prov, 1, 0, 1, 2)

        # Campos
        grid.addWidget(QLabel("Precio de Compra:"), 2, 0)
        self.spin_precio = QDoubleSpinBox()
        self.spin_precio.setRange(0.0, 999999.99)
        self.spin_precio.setMinimumHeight(38)
        self.spin_precio.valueChanged.connect(self.calcular_total)
        grid.addWidget(self.spin_precio, 2, 1)

        grid.addWidget(QLabel("Cantidad:"), 3, 0)
        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, 999999)
        self.spin_cant.setSingleStep(1)
        self.spin_cant.setMinimumHeight(38)
        self.spin_cant.valueChanged.connect(self.calcular_total)
        grid.addWidget(self.spin_cant, 3, 1)
        self.spin_precio.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))


        grid.addWidget(QLabel("Fecha de Compra:"), 4, 0)
        self.input_fecha = QDateEdit()
        self.input_fecha.setCalendarPopup(True)
        self.input_fecha.setDate(QDate.currentDate())
        self.input_fecha.setMinimumHeight(38)
        grid.addWidget(self.input_fecha, 4, 1)

        grid.addWidget(QLabel("Monto Total:"), 5, 0)
        self.lbl_total = QLabel("$0.00")
        self.lbl_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #2F855A;")
        grid.addWidget(self.lbl_total, 5, 1)

        grid.addWidget(QLabel("Registrado por:"), 6, 0)
        self.label_admin = QLabel(self.usuario_actual)
        self.label_admin.setStyleSheet("font-weight: bold; color: #2B6CB0; padding: 8px; background-color: #EBF8FF; border-radius: 4px;")
        self.label_admin.setMinimumHeight(38)
        grid.addWidget(self.label_admin, 6, 1)

        layout.addLayout(grid)
        layout.addStretch()

        btn_guardar = QPushButton("Guardar Historial")
        btn_guardar.setObjectName("botonPrincipal")
        btn_guardar.setMinimumHeight(45)
        btn_guardar.clicked.connect(self.guardar)
        layout.addWidget(btn_guardar)

        if self.hist_id:
            self.cargar_datos_existentes()


    def buscar_proveedor(self):
        txt = self.input_buscar_prov.text().strip()
        conn = obtener_conexion()
        res = conn.cursor().execute("SELECT id_prov, nombre_empresa FROM proveedores WHERE id_prov LIKE ? OR nombre_empresa LIKE ?", (f"%{txt}%", f"%{txt}%")).fetchall()
        conn.close()
        if len(res) == 1:
            self.set_proveedor(res[0])
        elif len(res) > 1:
            d = DialogoSeleccionarProveedor(self, res)
            if d.exec() and d.proveedor_seleccionado:
                self.set_proveedor(d.proveedor_seleccionado)

    def set_proveedor(self, prov):
        self.proveedor_seleccionado = prov
        self.lbl_info_prov.setText(f"ID: {prov[0]} | Empresa: {prov[1]}")

    def calcular_total(self):
        self.monto_total = self.spin_precio.value() * self.spin_cant.value()
        self.lbl_total.setText(f"${self.monto_total:,.2f}")

    def cargar_datos_existentes(self):
        conn = obtener_conexion()
        d = conn.cursor().execute("SELECT proveedor_id, proveedor_nombre, precio_compra, cantidad, fecha, usuario FROM historial_compras WHERE id=?", (self.hist_id,)).fetchone()
        conn.close()
        if d:
            self.set_proveedor((d[0], d[1]))
            self.spin_precio.setValue(d[2])
            self.spin_cant.setValue(d[3])
            self.input_fecha.setDate(QDate.fromString(d[4], "yyyy-MM-dd"))
            self.label_admin.setText(d[5])
            self.calcular_total()

    def guardar(self):
        if not self.proveedor_seleccionado:
            QMessageBox.warning(self, "Error", "Selecciona un proveedor.")
            return

        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except:
            QMessageBox.warning(self, "Sin conexión", "Se requiere internet.")
            return
        if self.hist_id:
            usuario = self.label_admin.text()   # el que ya estaba registrado
        else:
            usuario = self.usuario_actual


        datos = {
            "codigo_producto": self.cod_prod,
            "proveedor_id": self.proveedor_seleccionado[0],
            "proveedor_nombre": self.proveedor_seleccionado[1],
            "precio_compra": self.spin_precio.value(),
            "cantidad": self.spin_cant.value(),
            "fecha": self.input_fecha.date().toString("yyyy-MM-dd"),
            "monto_total": self.monto_total,
            "usuario": usuario
        }

        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            if self.hist_id:
                exito, msj = operacion_crud_nube('historial_compras', 'UPDATE', datos, self.hist_id)
                if not exito: raise Exception(msj)
                cursor.execute("UPDATE historial_compras SET proveedor_id=?, proveedor_nombre=?, precio_compra=?, cantidad=?, fecha=?, monto_total=? WHERE id=?",
                               (datos["proveedor_id"], datos["proveedor_nombre"], datos["precio_compra"], datos["cantidad"], datos["fecha"], datos["monto_total"], self.hist_id))
            else:
                exito, nuevo_id = operacion_crud_nube('historial_compras', 'INSERT', datos)
                if not exito: raise Exception(nuevo_id)
                cursor.execute("INSERT INTO historial_compras (id, codigo_producto, proveedor_id, proveedor_nombre, precio_compra, cantidad, fecha, monto_total, usuario) VALUES (?,?,?,?,?,?,?,?,?)",
                               (nuevo_id, datos["codigo_producto"], datos["proveedor_id"], datos["proveedor_nombre"], datos["precio_compra"], datos["cantidad"], datos["fecha"], datos["monto_total"], datos["usuario"]))
                
                # 🌟 MAGIA: Si es registro nuevo y la fecha es hoy, sumamos al inventario local y nube
                if datos["fecha"] == QDate.currentDate().toString("yyyy-MM-dd"):
                    prod = cursor.execute("SELECT id, stock FROM inventario WHERE codigo_producto=?", (self.cod_prod,)).fetchone()
                    if prod:
                        nuevo_stock = prod[1] + datos["cantidad"]
                        exito_s, msj_s = operacion_crud_nube('inventario', 'UPDATE', {"stock": nuevo_stock}, prod[0])
                        if exito_s:
                            cursor.execute("UPDATE inventario SET stock=? WHERE id=?", (nuevo_stock, prod[0]))

            conn.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()

class DialogoHistorialCompras(QDialog):
    def __init__(self, parent=None, cod_prod="", desc_prod="", usuario_actual=""):
        super().__init__(parent)
        self.cod_prod = cod_prod
        self.desc_prod = desc_prod
        self.usuario_actual = usuario_actual
        self.setWindowTitle(f"Historial de Compras - {cod_prod}")
        self.setFixedSize(850, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QHBoxLayout()
        lbl_titulo = QLabel(f"📦 {cod_prod} - {desc_prod}")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        header.addWidget(lbl_titulo)
        
        btn_nuevo = QPushButton("➕ Nueva Compra")
        btn_nuevo.setObjectName("botonAgregar")
        btn_nuevo.setMinimumHeight(35)
        btn_nuevo.clicked.connect(self.nuevo_historial)
        header.addStretch()
        header.addWidget(btn_nuevo)
        layout.addLayout(header)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Proveedor", "Cant.", "P. Compra", "Total", "Registró", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("QTableWidget { alternate-background-color: #F9FAFB; }")
        layout.addWidget(self.tabla)

        self.cargar_datos()

    def cargar_datos(self):
        conn = obtener_conexion()
        filas = conn.cursor().execute("SELECT id, fecha, proveedor_nombre, cantidad, precio_compra, monto_total, usuario FROM historial_compras WHERE codigo_producto=? ORDER BY date(fecha) DESC, id DESC", (self.cod_prod,)).fetchall()
        conn.close()

        self.tabla.setRowCount(len(filas))
        for i, f in enumerate(filas):
            self.tabla.setItem(i, 0, QTableWidgetItem(f[1]))
            self.tabla.setItem(i, 1, QTableWidgetItem(f[2]))
            self.tabla.setItem(i, 2, QTableWidgetItem(f"{f[3]:g}"))
            self.tabla.setItem(i, 3, QTableWidgetItem(f"${f[4]:.2f}"))
            self.tabla.setItem(i, 4, QTableWidgetItem(f"${f[5]:.2f}"))
            self.tabla.setItem(i, 5, QTableWidgetItem(f[6]))

            w = QWidget()
            lo = QHBoxLayout(w)
            lo.setContentsMargins(5, 0, 5, 0)
            btn_e = QPushButton("✏️"); btn_e.clicked.connect(lambda _, x=f[0]: self.editar(x))
            btn_d = QPushButton("🗑️"); btn_d.clicked.connect(lambda _, x=f[0]: self.eliminar(x))
            lo.addWidget(btn_e); lo.addWidget(btn_d)
            self.tabla.setCellWidget(i, 6, w)

    def nuevo_historial(self):
        if DialogoAgregarHistorial(self, self.cod_prod, self.desc_prod, usuario_actual=self.usuario_actual).exec(): self.cargar_datos()

    def editar(self, h_id):
        if DialogoAgregarHistorial(self, self.cod_prod, self.desc_prod, h_id, self.usuario_actual).exec(): self.cargar_datos()

    def eliminar(self, h_id):
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except:
            QMessageBox.warning(self, "Sin conexión", "Se requiere internet.")
            return

        if QMessageBox.question(self, "Eliminar", "¿Borrar este registro del historial?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            exito, msj = operacion_crud_nube('historial_compras', 'DELETE', registro_id=h_id)
            if exito:
                conn = obtener_conexion()
                conn.cursor().execute("DELETE FROM historial_compras WHERE id=?", (h_id,))
                conn.commit(); conn.close()
                self.cargar_datos()

# ────────────────────────────────────────────────
# Vista principal de Inventario
# ────────────────────────────────────────────────
class VistaInventario(QWidget):
    def __init__(self, rol="Super admin", usuario_actual=""):
        super().__init__()
        self.rol = rol
        self.usuario_actual = usuario_actual
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Cabecera
        header = QHBoxLayout()
        titulo = QLabel("📦 Gestión de Inventario")
        titulo.setStyleSheet("font-size: 26px; font-weight: bold; color: #2c3e50;")

        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar por código o descripción...")
        self.buscar.setMinimumHeight(42)
        self.buscar.setMaximumWidth(420)
        self.buscar.textChanged.connect(self.cargar_datos)

        btn_nuevo = QPushButton("➕ Nuevo Producto")
        btn_nuevo.setObjectName("botonAgregar")
        btn_nuevo.setMinimumHeight(42)
        btn_nuevo.setMinimumWidth(170)
        btn_nuevo.clicked.connect(self.agregar_producto)
        
        if self.rol == "Vendedor":
            btn_nuevo.setVisible(False)

        header.addWidget(titulo)
        header.addStretch()
        header.addWidget(self.buscar)
        header.addSpacing(16)
        header.addWidget(btn_nuevo)
        layout.addLayout(header)

        # Tabla
        self.tabla = QTableWidget()
        columnas = ["ID", "Código", "Descripción", "Stock", "UM", "Proveedor", "Marca", "Costo", "Venta", "Acciones"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)

        header = self.tabla.horizontalHeader()

        # Columnas fijas
        fixed = {
            0:  55,   # ID
            1: 100,   # Código
            3:  80,   # Stock
            4:  65,   # UM
            7: 100,   # Costo
            8: 100,   # Venta
            9: 320    # Acciones
        }

        for col, ancho in fixed.items():
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.tabla.setColumnWidth(col, ancho)

        # Columnas dinámicas (las importantes)
        header.setSectionResizeMode(2, QHeaderView.Stretch)   # Descripción (crece)
        header.setSectionResizeMode(6, QHeaderView.Stretch)   # Marca (crece)

        # Ajuste automático de contenido
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Proveedor

        # Permitir mover columnas
        header.setSectionsMovable(True)

        # 🔥 CLAVE: elimina el espacio vacío
        header.setStretchLastSection(True)
        

        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(58)
        self.tabla.setAlternatingRowColors(True)

        self.tabla.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        if self.rol == "Vendedor":
            self.tabla.setColumnHidden(7, True) # Oculta la columna "Costo"
            self.tabla.setColumnHidden(9, True) # Oculta la columna "Acciones" (botones de editar/eliminar)
        else:
            # Solo los Super admin pueden editar con doble clic
            self.tabla.cellDoubleClicked.connect(self.editar_con_doble_clic)
        layout.addWidget(self.tabla)

        self.cargar_datos()

    def crear_botones_accion(self, prod):
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(5)
        lay.setAlignment(Qt.AlignCenter)

        # Botón Editar
        btn_edit = QPushButton("✏️ Editar")
        btn_edit.setObjectName("botonEditar")  # Usa el estilo de la hoja global
        
        btn_edit.setMinimumHeight(28)
        
        btn_edit.setFixedSize(100, 30)
        btn_edit.clicked.connect(lambda _, p=prod: self.editar_producto(p))

        # Botón Eliminar
        btn_del = QPushButton("🗑️ Eliminar")
        btn_del.setObjectName("botonEliminar")  # Usa el estilo de la hoja global
        btn_del.setFixedSize(100, 30)
        
        btn_del.setMinimumHeight(28)
        
        btn_del.clicked.connect(lambda _, pid=prod[0], d=prod[2]: self.eliminar_producto(pid, d))

        btn_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_del.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        lay.addWidget(btn_edit)
        # Botón Historial (solo Super admin)
        if self.rol == "Super admin":
            btn_hist = QPushButton("📜 Historial")
            btn_hist.setFixedSize(100, 30)
            btn_hist.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # Usar mismo estilo que botón editar/eliminar
            
            btn_hist.setMinimumHeight(28)
            
            btn_hist.setObjectName("botonEditar")
            btn_hist.clicked.connect(lambda _, c=prod[1], d=prod[2]: self.abrir_historial(c, d))
            lay.addWidget(btn_hist)

        
        lay.addWidget(btn_del)

        return widget

    def abrir_historial(self, codigo, descripcion):
        DialogoHistorialCompras(self, codigo, descripcion, self.usuario_actual).exec()
        self.cargar_datos()

    def cargar_datos(self):
        texto = f"%{self.buscar.text().strip()}%"
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, codigo_producto, descripcion, stock, um, proveedor_id, marca,
                   precio_compra, precio_venta, clave_sat_producto
            FROM inventario
            WHERE codigo_producto LIKE ? OR descripcion LIKE ?
            ORDER BY id DESC
        """, (texto, texto))
        rows = cursor.fetchall()
        conn.close()

        self.tabla.setRowCount(len(rows))

        for i, row in enumerate(rows):
            id_fmt = f"{row[0]:02d}"

            item_id = QTableWidgetItem(id_fmt)
            item_id.setTextAlignment(Qt.AlignCenter)
            item_id.setData(Qt.UserRole, row)

            stock_txt = str(int(row[3])) 
            compra_txt = f"${row[7]:.2f}"
            venta_txt  = f"${row[8]:.2f}"

            valores = [
                item_id,
                QTableWidgetItem(row[1]),
                QTableWidgetItem(row[2]),
                QTableWidgetItem(stock_txt),
                QTableWidgetItem(row[4] or ""),
                QTableWidgetItem(str(row[5] or "")),
                QTableWidgetItem(row[6] or ""),
                QTableWidgetItem(compra_txt),
                QTableWidgetItem(venta_txt)
            ]

            for col, item in enumerate(valores):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col != 0:
                    align = Qt.AlignCenter if col in (3,4,7,8) else Qt.AlignLeft | Qt.AlignVCenter
                    item.setTextAlignment(align)
                self.tabla.setItem(i, col, item)

            self.tabla.setCellWidget(i, 9, self.crear_botones_accion(row))

    def editar_con_doble_clic(self, row, col):
        item = self.tabla.item(row, 0)
        if item:
            self.editar_producto(item.data(Qt.UserRole))

    def agregar_producto(self):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        if DialogoProducto(self).exec():
            self.cargar_datos()

    def editar_producto(self, datos):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        if DialogoProducto(self, datos).exec():
            self.cargar_datos()
    def eliminar_producto(self, pid, descripcion):
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar.")
            return

        if QMessageBox.question(self, "Confirmar", f"¿Eliminar el producto?\n\n{descripcion}", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            exito, mensaje = operacion_crud_nube('inventario', 'DELETE', registro_id=pid)
            if not exito:
                QMessageBox.critical(self, "Error Nube", f"No se pudo eliminar:\n{mensaje}")
                return 
            
            # --- CASCADA Y RECÁLCULO LOCAL ---
            conn = obtener_conexion()
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = OFF;")
                
                cursor.execute("SELECT codigo_producto FROM inventario WHERE id=?", (pid,))
                cod = cursor.fetchone()[0]
                
                # Obtener qué cotizaciones se verán afectadas
                cursor.execute("SELECT DISTINCT cotizacion_id FROM cotizaciones_detalle WHERE codigo_producto=?", (cod,))
                cots_afectadas = [row[0] for row in cursor.fetchall()]
                
                cursor.execute("DELETE FROM cotizaciones_detalle WHERE codigo_producto=?", (cod,))
                
                # Recalcular el total de cada cotización afectada
                for cid in cots_afectadas:
                    cursor.execute("SELECT SUM(monto) FROM cotizaciones_detalle WHERE cotizacion_id=?", (cid,))
                    subtotal = cursor.fetchone()[0] or 0.0
                    total = subtotal * 1.16 # Sumamos el IVA
                    cursor.execute("UPDATE cotizaciones SET monto_total=? WHERE id_cotizacion=?", (total, cid))
                
                cursor.execute("DELETE FROM inventario WHERE id=?", (pid,))
                
                cursor.execute("PRAGMA foreign_keys = ON;")
                conn.commit()
                self.cargar_datos()
            except Exception as e:
                QMessageBox.critical(self, "Error Local", str(e))
            finally:
                conn.close()
# Opcional: botón para abrir gestión de UM desde algún lugar (puedes agregarlo donde prefieras)
# Por ejemplo en la cabecera o en el diálogo de producto