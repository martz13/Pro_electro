from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QHeaderView, QDialog, QMessageBox, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from base_datos.conexion import obtener_conexion, registrar_en_cola_sync

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

        # Separado en tupla para la consulta SQL
        datos_tupla = (
            nombre, self.input_rfc.text().strip(), self.input_direccion.text().strip(),
            self.input_colonia.text().strip(), self.input_poblacion.text().strip(),
            self.input_cp.text().strip(), self.input_telefono.text().strip(),
            self.input_correo.text().strip(), self.input_cfdi.text().strip(),
            self.input_regimen.text().strip(), self.input_contacto.text().strip()
        )
        
        # Diccionario base para la sincronización
        datos_dict = {
            "nombre_completo": datos_tupla[0],
            "rfc": datos_tupla[1],
            "direccion": datos_tupla[2],
            "colonia": datos_tupla[3],
            "poblacion": datos_tupla[4],
            "cp": datos_tupla[5],
            "telefono": datos_tupla[6],
            "correo": datos_tupla[7],
            "cfdi": datos_tupla[8],
            "regimen": datos_tupla[9],
            "contacto": datos_tupla[10]
        }

        conexion = obtener_conexion()
        cursor = conexion.cursor()
        try:
            if self.cliente_id:
                cursor.execute("""
                    UPDATE clientes SET 
                    nombre_completo=?, rfc=?, direccion=?, colonia=?, poblacion=?, 
                    cp=?, telefono=?, correo=?, cfdi=?, regimen=?, contacto=? 
                    WHERE id_cliente=?
                """, (*datos_tupla, self.cliente_id))
                
                conexion.commit()
                registrar_en_cola_sync('clientes', 'UPDATE', self.cliente_id, datos_dict)
                
            else:
                nuevo_id = self.generar_nuevo_id(cursor)
                
                # Para el INSERT es buena idea incluir su propia llave primaria en el dict
                datos_dict["id_cliente"] = nuevo_id
                
                cursor.execute("""
                    INSERT INTO clientes (id_cliente, nombre_completo, rfc, direccion, colonia, 
                    poblacion, cp, telefono, correo, cfdi, regimen, contacto) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nuevo_id, *datos_tupla))
                
                conexion.commit()
                registrar_en_cola_sync('clientes', 'INSERT', nuevo_id, datos_dict)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {str(e)}")
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
        if DialogoCliente(self).exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Cliente registrado.")

    def editar_cliente(self, datos):
        if DialogoCliente(self, datos).exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Cliente actualizado.")

    def eliminar_cliente(self, c_id, nombre):
        if QMessageBox.question(self, "Eliminar", f"¿Eliminar a {nombre}?", 
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("DELETE FROM clientes WHERE id_cliente=?", (c_id,))
                conexion.commit()
                
                # Registro en la cola de sincronización
                registrar_en_cola_sync('clientes', 'DELETE', c_id, None)
                
                self.cargar_datos()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            finally:
                conexion.close()