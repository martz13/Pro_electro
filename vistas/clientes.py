from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QHeaderView, QDialog, QMessageBox, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import requests
from base_datos.conexion import obtener_conexion, forzar_descarga_nube, operacion_crud_nube

class DialogoCliente(QDialog):
    def __init__(self, parent=None, cliente_datos=None):
        super().__init__(parent)
        self.cliente_id = cliente_datos[0] if cliente_datos else None
        self.setWindowTitle("Agregar Cliente" if not self.cliente_id else f"Editar Cliente - {self.cliente_id}")
        self.setFixedSize(650, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(35, 35, 35, 35)
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)

        # Campos del formulario con estilos del QSS
        campos = [
            ("Nombre Completo:", "input_nombre", 0, 0, cliente_datos[1] if cliente_datos else ""),
            ("RFC:", "input_rfc", 0, 2, cliente_datos[2] if cliente_datos else ""),
            ("Dirección:", "input_direccion", 1, 0, cliente_datos[3] if cliente_datos else ""),
            ("Colonia:", "input_colonia", 1, 2, cliente_datos[4] if cliente_datos else ""),
            ("Población:", "input_poblacion", 2, 0, cliente_datos[5] if cliente_datos else ""),
            ("C.P.:", "input_cp", 2, 2, cliente_datos[6] if cliente_datos else ""),
            ("Teléfono:", "input_telefono", 3, 0, cliente_datos[7] if cliente_datos else ""),
            ("Correo:", "input_correo", 3, 2, cliente_datos[8] if cliente_datos else ""),
            ("CFDI:", "input_cfdi", 4, 0, cliente_datos[9] if cliente_datos else ""),
            ("Régimen:", "input_regimen", 4, 2, cliente_datos[10] if cliente_datos else ""),
            ("Contacto:", "input_contacto", 5, 0, cliente_datos[11] if cliente_datos else ""),
        ]

        for label_text, attr_name, row, col, value in campos:
            lbl = QLabel(label_text)
            lbl.setObjectName("labelTitulo")
            grid.addWidget(lbl, row, col)
            
            edit = QLineEdit(str(value))
            edit.setMinimumHeight(38)
            setattr(self, attr_name, edit)
            grid.addWidget(edit, row, col + 1)

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
        cursor.execute("SELECT MAX(id_cliente) FROM clientes")
        max_id = cursor.fetchone()[0]
        if max_id:
            num = int(max_id[1:]) + 1
            return f"C{num:04d}"
        return "C0001"

    def guardar(self):
        nombre = self.input_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El Nombre Completo es obligatorio.")
            return

        # Construimos el diccionario de datos primero
        datos_dict = {
            "nombre_completo": nombre,
            "rfc": self.input_rfc.text().strip(),
            "direccion": self.input_direccion.text().strip(),
            "colonia": self.input_colonia.text().strip(),
            "poblacion": self.input_poblacion.text().strip(),
            "cp": self.input_cp.text().strip(),
            "telefono": self.input_telefono.text().strip(),
            "correo": self.input_correo.text().strip(),
            "cfdi": self.input_cfdi.text().strip(),
            "regimen": self.input_regimen.text().strip(),
            "contacto": self.input_contacto.text().strip()
        }

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # --- REGLA 2: Prevención de Colisiones (Verificar antes de Guardar) ---
        try:
            resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=clientes", timeout=3)
            if resp.status_code == 200:
                total_nube = resp.json().get("total", 0)
                
                cursor.execute("SELECT COUNT(*) FROM clientes")
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
            if self.cliente_id: # UPDATE
                # --- REGLA 3: NUBE PRIMERO ---
                exito, msj = operacion_crud_nube('clientes', 'UPDATE', datos_dict, self.cliente_id)
                if not exito: raise Exception(f"Error en la nube: {msj}")
                
                # --- LOCAL DESPUÉS DEL ÉXITO EN LA NUBE ---
                cursor.execute("""
                    UPDATE clientes SET 
                    nombre_completo=?, rfc=?, direccion=?, colonia=?, poblacion=?, 
                    cp=?, telefono=?, correo=?, cfdi=?, regimen=?, contacto=? 
                    WHERE id_cliente=?
                """, (
                    datos_dict["nombre_completo"], datos_dict["rfc"], datos_dict["direccion"],
                    datos_dict["colonia"], datos_dict["poblacion"], datos_dict["cp"],
                    datos_dict["telefono"], datos_dict["correo"], datos_dict["cfdi"],
                    datos_dict["regimen"], datos_dict["contacto"], self.cliente_id
                ))
                
            else: # INSERT
                # 1. Generar el ID personalizado localmente ANTES de ir a la nube
                nuevo_id = self.generar_nuevo_id(cursor)
                
                # 2. Agregar el ID al diccionario para que la API lo reciba
                datos_dict["id_cliente"] = nuevo_id
                
                # --- REGLA 3: NUBE PRIMERO ---
                exito, nuevo_id_nube = operacion_crud_nube('clientes', 'INSERT', datos_dict)
                if not exito: raise Exception(f"Error en la nube: {nuevo_id_nube}")
                
                # --- LOCAL USANDO EL ID QUE ENVIAMOS/RECIBIMOS ---
                cursor.execute("""
                    INSERT INTO clientes (id_cliente, nombre_completo, rfc, direccion, colonia, 
                    poblacion, cp, telefono, correo, cfdi, regimen, contacto) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nuevo_id_nube, datos_dict["nombre_completo"], datos_dict["rfc"], 
                    datos_dict["direccion"], datos_dict["colonia"], datos_dict["poblacion"], 
                    datos_dict["cp"], datos_dict["telefono"], datos_dict["correo"], 
                    datos_dict["cfdi"], datos_dict["regimen"], datos_dict["contacto"]
                ))
                
            conexion.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{str(e)}")
        finally:
            conexion.close()


class VistaClientes(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- CABECERA ---
        header_layout = QHBoxLayout()
        
        titulo = QLabel("👥 Gestión de Clientes")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍 Buscar por ID o Nombre...")
        self.input_buscar.setFixedWidth(350)
        self.input_buscar.setMinimumHeight(40)
        self.input_buscar.textChanged.connect(self.cargar_datos)

        self.btn_agregar = QPushButton("➕ Agregar Cliente")
        self.btn_agregar.setObjectName("botonAgregar")
        self.btn_agregar.setMinimumHeight(40)
        self.btn_agregar.clicked.connect(self.agregar_cliente)

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(self.input_buscar)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.btn_agregar)
        layout.addLayout(header_layout)

        # --- TABLA ---
        self.tabla = QTableWidget()
        columnas = ["ID", "Nombre Completo", "RFC", "Dirección", "Colonia", "Población", 
                   "C.P.", "Teléfono", "Correo", "CFDI", "Régimen", "Contacto", "Acciones"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        
        # SOLUCIÓN 2: Anchos de columna bien definidos y más amplios (Evitamos que se corten)
        self.tabla.setColumnWidth(0, 80)   # ID
        self.tabla.setColumnWidth(1, 280)  # Nombre Completo (¡Se amplió para que no se corte!)
        self.tabla.setColumnWidth(2, 130)  # RFC
        self.tabla.setColumnWidth(3, 220)  # Dirección
        self.tabla.setColumnWidth(4, 150)  # Colonia
        self.tabla.setColumnWidth(5, 150)  # Población
        self.tabla.setColumnWidth(6, 80)   # C.P.
        self.tabla.setColumnWidth(7, 120)  # Teléfono
        self.tabla.setColumnWidth(8, 200)  # Correo
        self.tabla.setColumnWidth(9, 100)  # CFDI
        self.tabla.setColumnWidth(10, 150) # Régimen
        self.tabla.setColumnWidth(11, 150) # Contacto
        self.tabla.setColumnWidth(12, 220) # Acciones
        
        # Configuraciones de comportamiento
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(60) # Altura de fila
        self.tabla.setAlternatingRowColors(True)
        
        # SOLUCIÓN 1: Evitar que el texto desaparezca (se vuelva blanco sobre blanco) al abrir el modal
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

    def crear_widget_acciones(self, cliente_datos):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Espaciado perfecto y centrado de los botones de estilos.qss
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10) 
        
        btn_editar = QPushButton("✏️ Editar")
        btn_editar.setObjectName("botonEditar")
        
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.setObjectName("botonEliminar")
        
        c_id, nombre = cliente_datos[0], cliente_datos[1]
        
        # Uso seguro de lambdas: pasando variables por defecto (c=cliente_datos) para evitar errores de enlace 
        btn_editar.clicked.connect(lambda checked, c=cliente_datos: self.editar_cliente(c))
        btn_eliminar.clicked.connect(lambda checked, i=c_id, n=nombre: self.eliminar_cliente(i, n))
        
        layout.addStretch()
        layout.addWidget(btn_editar)
        layout.addWidget(btn_eliminar)
        layout.addStretch()
        
        return widget

    def cargar_datos(self):
        filtro = self.input_buscar.text().strip()
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        query = "SELECT * FROM clientes WHERE id_cliente LIKE ? OR nombre_completo LIKE ? ORDER BY id_cliente DESC"
        cursor.execute(query, (f"%{filtro}%", f"%{filtro}%"))
        clientes = cursor.fetchall()
        conexion.close()

        self.tabla.setRowCount(len(clientes))
        
        for fila, cliente in enumerate(clientes):
            for col in range(12):
                item = QTableWidgetItem(str(cliente[col] if cliente[col] else ""))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col in [0, 2, 6, 9] else Qt.AlignLeft))
                self.tabla.setItem(fila, col, item)

            # Insertar el widget de acciones
            self.tabla.setCellWidget(fila, 12, self.crear_widget_acciones(cliente))

    def on_cell_double_clicked(self, row, column):
        cliente_datos = []
        for col in range(12):
            item = self.tabla.item(row, col)
            cliente_datos.append(item.text() if item else "")
        self.editar_cliente(cliente_datos)

    def agregar_cliente(self):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        if DialogoCliente(self).exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Cliente registrado.")

    def editar_cliente(self, datos):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        if DialogoCliente(self, datos).exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Cliente actualizado.")

    def eliminar_cliente(self, c_id, nombre):
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar.")
            return

        if QMessageBox.question(self, "Eliminar", f"¿Eliminar a {nombre} y todas sus cotizaciones?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            exito, mensaje = operacion_crud_nube('clientes', 'DELETE', registro_id=c_id)
            if not exito:
                QMessageBox.critical(self, "Error en la Nube", f"No se pudo eliminar:\n{mensaje}")
                return 
            
            # --- CASCADA LOCAL ---
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("SELECT id_cotizacion FROM cotizaciones WHERE cliente_id=?", (c_id,))
                cots = cursor.fetchall()
                for cot in cots:
                    cursor.execute("DELETE FROM cotizaciones_detalle WHERE cotizacion_id=?", (cot[0],))
                cursor.execute("DELETE FROM cotizaciones WHERE cliente_id=?", (c_id,))
                cursor.execute("DELETE FROM clientes WHERE id_cliente=?", (c_id,))
                conexion.commit()
                self.cargar_datos()
                QMessageBox.information(self, "Éxito", "Cliente y cotizaciones eliminados correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error Local", str(e))
            finally:
                conexion.close()
        