from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QHeaderView, QDialog, QMessageBox, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import requests
from base_datos.conexion import obtener_conexion,forzar_descarga_nube,operacion_crud_nube

class DialogoProveedor(QDialog):
    def __init__(self, parent=None, proveedor_datos=None):
        super().__init__(parent)
        self.proveedor_id = proveedor_datos[0] if proveedor_datos else None
        self.setWindowTitle("Agregar Proveedor" if not self.proveedor_id else f"Editar Proveedor - {self.proveedor_id}")
        self.setFixedSize(650, 400) # Se aumentó el tamaño para respirar mejor
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(35, 35, 35, 35) # Márgenes consistentes
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)

        # --- Campos del formulario aplicando estilos ---
        # Fila 0
        lbl_empresa = QLabel("Nombre Completo (Empresa):")
        lbl_empresa.setObjectName("labelTitulo")
        grid.addWidget(lbl_empresa, 0, 0, 1, 4)
        
        self.input_nombre_empresa = QLineEdit(proveedor_datos[1] if proveedor_datos else "")
        self.input_nombre_empresa.setMinimumHeight(38)
        grid.addWidget(self.input_nombre_empresa, 1, 0, 1, 4)

        # Fila 2
        lbl_vendedor = QLabel("Vendedor (Contacto):")
        lbl_vendedor.setObjectName("labelTitulo")
        grid.addWidget(lbl_vendedor, 2, 0, 1, 2)
        
        self.input_vendedor = QLineEdit(proveedor_datos[2] if proveedor_datos else "")
        self.input_vendedor.setMinimumHeight(38)
        grid.addWidget(self.input_vendedor, 3, 0, 1, 2)

        lbl_telefono = QLabel("Num Teléfono:")
        lbl_telefono.setObjectName("labelTitulo")
        grid.addWidget(lbl_telefono, 2, 2, 1, 2)
        
        self.input_telefono = QLineEdit(proveedor_datos[3] if proveedor_datos else "")
        self.input_telefono.setMinimumHeight(38)
        grid.addWidget(self.input_telefono, 3, 2, 1, 2)

        # Fila 4
        lbl_correo = QLabel("Correo:")
        lbl_correo.setObjectName("labelTitulo")
        grid.addWidget(lbl_correo, 4, 0, 1, 2)
        
        self.input_correo = QLineEdit(proveedor_datos[4] if proveedor_datos else "")
        self.input_correo.setMinimumHeight(38)
        grid.addWidget(self.input_correo, 5, 0, 1, 2)

        lbl_tel_tienda = QLabel("Tel. Tienda Física:")
        lbl_tel_tienda.setObjectName("labelTitulo")
        grid.addWidget(lbl_tel_tienda, 4, 2, 1, 2)
        
        self.input_tel_tienda = QLineEdit(proveedor_datos[6] if proveedor_datos else "")
        self.input_tel_tienda.setMinimumHeight(38)
        grid.addWidget(self.input_tel_tienda, 5, 2, 1, 2)

        # Fila 6
        lbl_direccion = QLabel("Dirección:")
        lbl_direccion.setObjectName("labelTitulo")
        grid.addWidget(lbl_direccion, 6, 0, 1, 4)
        
        self.input_direccion = QLineEdit(proveedor_datos[5] if proveedor_datos else "")
        self.input_direccion.setMinimumHeight(38)
        grid.addWidget(self.input_direccion, 7, 0, 1, 4)

        layout.addLayout(grid)
        layout.addStretch()

        # Botón guardar
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_guardar.setObjectName("botonPrincipal")
        self.btn_guardar.setMinimumHeight(45)
        self.btn_guardar.clicked.connect(self.guardar)
        
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.btn_guardar)
        layout.addLayout(btn_container)

    def generar_nuevo_id(self, cursor):
        cursor.execute("SELECT MAX(id_prov) FROM proveedores")
        max_id = cursor.fetchone()[0]
        if max_id:
            num = int(max_id[2:]) + 1
            return f"PE{num:02d}"
        return "PE01"

    def guardar(self):
        nombre_empresa = self.input_nombre_empresa.text().strip()
        if not nombre_empresa:
            QMessageBox.warning(self, "Error", "El Nombre de la Empresa es obligatorio.")
            return

        # Armamos el diccionario con los nombres exactos de las columnas
        datos_dict = {
            "nombre_empresa": nombre_empresa,
            "vendedor_contacto": self.input_vendedor.text().strip(),
            "num_telefono": self.input_telefono.text().strip(),
            "correo": self.input_correo.text().strip(),
            "direccion": self.input_direccion.text().strip(),
            "tel_tienda_fisica": self.input_tel_tienda.text().strip()
        }

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # --- REGLA 2: Prevención de Colisiones (Verificar antes de Guardar) ---
        try:
            resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=proveedores", timeout=3)
            if resp.status_code == 200:
                total_nube = resp.json().get("total", 0)
                
                cursor.execute("SELECT COUNT(*) FROM proveedores")
                total_local = cursor.fetchone()[0]
                
                if total_nube > total_local:
                    QMessageBox.information(self, "Sincronizando...", "Se detectaron nuevos datos en la nube de otros usuarios. Actualizando sistema...")
                    forzar_descarga_nube()
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Error de Red", "Se perdió la conexión. No se puede guardar.")
            conexion.close()
            return
        # ----------------------------------------------------------------------

        try:
            if self.proveedor_id: # UPDATE
                # --- REGLA 3: NUBE PRIMERO ---
                exito, msj = operacion_crud_nube('proveedores', 'UPDATE', datos_dict, self.proveedor_id)
                if not exito: raise Exception(f"Error en la nube: {msj}")
                
                # --- LOCAL DESPUÉS DEL ÉXITO EN LA NUBE ---
                cursor.execute("""
                    UPDATE proveedores SET 
                    nombre_empresa=?, vendedor_contacto=?, num_telefono=?, correo=?, 
                    direccion=?, tel_tienda_fisica=? 
                    WHERE id_prov=?
                """, (
                    datos_dict["nombre_empresa"], datos_dict["vendedor_contacto"], 
                    datos_dict["num_telefono"], datos_dict["correo"], 
                    datos_dict["direccion"], datos_dict["tel_tienda_fisica"], 
                    self.proveedor_id
                ))
                
            else: # INSERT
                # --- REGLA 3: NUBE PRIMERO (Genera el ID) ---
                nuevo_id = self.generar_nuevo_id(cursor)
                datos_dict["id_prov"] = nuevo_id
                exito, nuevo_id_nube = operacion_crud_nube('proveedores', 'INSERT', datos_dict)
                if not exito: raise Exception(f"Error en la nube: {nuevo_id_nube}")
                
                # --- LOCAL USANDO EL ID MAESTRO DE LA NUBE ---
                cursor.execute("""
                    INSERT INTO proveedores (
                    id_prov, nombre_empresa, vendedor_contacto, num_telefono, 
                    correo, direccion, tel_tienda_fisica
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    nuevo_id_nube, datos_dict["nombre_empresa"], datos_dict["vendedor_contacto"],
                    datos_dict["num_telefono"], datos_dict["correo"],
                    datos_dict["direccion"], datos_dict["tel_tienda_fisica"]
                ))
                
            conexion.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{str(e)}")
        finally:
            conexion.close()
class VistaProveedores(QWidget):
    def __init__(self):
        super().__init__()
        # Quitamos el setMinimumWidth rígido para que se adapte fluidamente
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- CABECERA ---
        header_layout = QHBoxLayout()
        
        titulo = QLabel("🏢 Gestión de Proveedores")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍 Buscar por ID o Nombre...")
        self.input_buscar.setFixedWidth(350)
        self.input_buscar.setMinimumHeight(40)
        self.input_buscar.textChanged.connect(self.cargar_datos)

        self.btn_agregar = QPushButton("➕ Agregar Proveedor")
        self.btn_agregar.setObjectName("botonAgregar")
        self.btn_agregar.setMinimumHeight(40)
        self.btn_agregar.setMinimumWidth(160)
        self.btn_agregar.clicked.connect(self.agregar_proveedor)

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(self.input_buscar)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.btn_agregar)
        layout.addLayout(header_layout)

        # --- TABLA ---
        self.tabla = QTableWidget()
        columnas = ["ID_Prov", "Empresa", "Vendedor (Contacto)", "Num Teléfono", "Correo", "Dirección", "Tel. Tienda", "Acciones"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        
        # 🌟 EL SECRETO DE LA ADAPTACIÓN FLUIDA 🌟
        header = self.tabla.horizontalHeader()
        
        # 1. Fijamos las columnas que no deben cambiar de tamaño
        header.setSectionResizeMode(0, QHeaderView.Fixed) # ID
        self.tabla.setColumnWidth(0, 80)
        
        header.setSectionResizeMode(3, QHeaderView.Fixed) # Num Teléfono
        self.tabla.setColumnWidth(3, 120)
        
        header.setSectionResizeMode(6, QHeaderView.Fixed) # Tel Tienda
        self.tabla.setColumnWidth(6, 120)
        
        header.setSectionResizeMode(7, QHeaderView.Fixed) # Acciones (Evita que los botones se estiren o encojan de más)
        self.tabla.setColumnWidth(7, 220)
        
        # 2. Hacemos que el resto de las columnas se estiren para rellenar la pantalla (Interactive/Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Empresa
        header.setSectionResizeMode(2, QHeaderView.Stretch) # Vendedor
        header.setSectionResizeMode(4, QHeaderView.Stretch) # Correo
        header.setSectionResizeMode(5, QHeaderView.Stretch) # Dirección
        
        # Configuraciones de comportamiento
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(60) # Altura de fila
        self.tabla.setAlternatingRowColors(True)
        
        self.tabla.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #F9FAFB;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTableWidget::item:selected:!active {
                background-color: #3498db;
                color: white;
            }
        """)
        
        self.tabla.cellDoubleClicked.connect(self.on_cell_double_clicked)
        layout.addWidget(self.tabla)

        self.cargar_datos()

    def crear_widget_acciones(self, proveedor_datos):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Espaciado perfecto y centrado de los botones
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10) 
        
        btn_editar = QPushButton("✏️ Editar")
        btn_editar.setObjectName("botonEditar")
        
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.setObjectName("botonEliminar")
        
        p_id, nombre = proveedor_datos[0], proveedor_datos[1]
        
        # Uso seguro de lambdas
        btn_editar.clicked.connect(lambda checked, p=proveedor_datos: self.editar_proveedor(p))
        btn_eliminar.clicked.connect(lambda checked, i=p_id, n=nombre: self.eliminar_proveedor(i, n))
        
        layout.addStretch()
        layout.addWidget(btn_editar)
        layout.addWidget(btn_eliminar)
        layout.addStretch()
        
        return widget

    def cargar_datos(self):
        filtro = self.input_buscar.text().strip()
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        query = "SELECT * FROM proveedores WHERE id_prov LIKE ? OR nombre_empresa LIKE ? ORDER BY id_prov DESC"
        cursor.execute(query, (f"%{filtro}%", f"%{filtro}%"))
        proveedores = cursor.fetchall()
        conexion.close()

        self.tabla.setRowCount(len(proveedores))
        
        for fila, proveedor in enumerate(proveedores):
            for col in range(7):
                item = QTableWidgetItem(str(proveedor[col] if proveedor[col] else ""))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col in [0, 3, 6] else Qt.AlignLeft))
                self.tabla.setItem(fila, col, item)

            # Insertar el widget de acciones
            self.tabla.setCellWidget(fila, 7, self.crear_widget_acciones(proveedor))

    def on_cell_double_clicked(self, row, column):
        proveedor_datos = []
        for col in range(7):
            item = self.tabla.item(row, col)
            proveedor_datos.append(item.text() if item else "")
        self.editar_proveedor(proveedor_datos)

    def agregar_proveedor(self):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        if DialogoProveedor(self).exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Proveedor registrado.")

    def editar_proveedor(self, datos):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        if DialogoProveedor(self, datos).exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Proveedor actualizado.")

    def eliminar_proveedor(self, p_id, nombre):
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar.")
            return

        if QMessageBox.question(self, "Eliminar", f"¿Eliminar al proveedor '{nombre}' y todos sus productos?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            exito, mensaje = operacion_crud_nube('proveedores', 'DELETE', registro_id=p_id)
            if not exito:
                QMessageBox.critical(self, "Error en la Nube", f"No se pudo eliminar:\n{mensaje}")
                return 
            
            # --- CASCADA Y RECÁLCULO LOCAL ---
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys = OFF;")
                
                cursor.execute("SELECT codigo_producto FROM inventario WHERE proveedor_id=?", (p_id,))
                prods = cursor.fetchall()
                
                for p in prods:
                    cod = p[0]
                    # Buscar y recalcular para cada producto del proveedor
                    cursor.execute("SELECT DISTINCT cotizacion_id FROM cotizaciones_detalle WHERE codigo_producto=?", (cod,))
                    cots_afectadas = [row[0] for row in cursor.fetchall()]
                    
                    cursor.execute("DELETE FROM cotizaciones_detalle WHERE codigo_producto=?", (cod,))
                    
                    for cid in cots_afectadas:
                        cursor.execute("SELECT SUM(monto) FROM cotizaciones_detalle WHERE cotizacion_id=?", (cid,))
                        subtotal = cursor.fetchone()[0] or 0.0
                        total = subtotal * 1.16
                        cursor.execute("UPDATE cotizaciones SET monto_total=? WHERE id_cotizacion=?", (total, cid))
                
                cursor.execute("DELETE FROM inventario WHERE proveedor_id=?", (p_id,))
                cursor.execute("DELETE FROM proveedores WHERE id_prov=?", (p_id,))
                
                cursor.execute("PRAGMA foreign_keys = ON;")
                conexion.commit()
                
                self.cargar_datos()
                QMessageBox.information(self, "Éxito", "Proveedor y productos eliminados. Cotizaciones recalculadas.")
            except Exception as e:
                QMessageBox.critical(self, "Error Local", str(e))
            finally:
                conexion.close()
        