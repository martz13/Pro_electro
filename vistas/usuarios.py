import bcrypt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QHeaderView, QDialog, QMessageBox, 
                               QComboBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import requests
from base_datos.conexion import obtener_conexion, forzar_descarga_nube, operacion_crud_nube

class DialogoUsuario(QDialog):
    def __init__(self, parent=None, usuario_id=None, nombre="", correo="", rol="Vendedor"):
        super().__init__(parent)
        self.usuario_id = usuario_id
        self.setWindowTitle("Agregar Usuario" if not usuario_id else f"Editar Usuario - {nombre}")
        self.setFixedSize(450, 450)  # Aumentado para dar espacio al nuevo campo
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(35, 35, 35, 35)

        # Campo nombre completo
        lbl_nombre = QLabel("Nombre Completo:")
        lbl_nombre.setObjectName("labelTitulo")
        layout.addWidget(lbl_nombre)
        
        self.input_nombre = QLineEdit(nombre)
        self.input_nombre.setPlaceholderText("Ej: Juan Pérez García")
        self.input_nombre.setMinimumHeight(38)
        layout.addWidget(self.input_nombre)

        # Campo correo
        lbl_correo = QLabel("Correo Electrónico:")
        lbl_correo.setObjectName("labelTitulo")
        layout.addWidget(lbl_correo)
        
        self.input_correo = QLineEdit(correo)
        self.input_correo.setPlaceholderText("ejemplo@correo.com")
        self.input_correo.setMinimumHeight(38)
        layout.addWidget(self.input_correo)

        # Campo contraseña
        lbl_password = QLabel("Contraseña" if not usuario_id else "Nueva Contraseña (opcional):")
        lbl_password.setObjectName("labelTitulo")
        layout.addWidget(lbl_password)
        
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setPlaceholderText("••••••••" if not usuario_id else "Dejar en blanco para mantener actual")
        self.input_password.setMinimumHeight(38)
        layout.addWidget(self.input_password)

        # Campo rol
        lbl_rol = QLabel("Rol:")
        lbl_rol.setObjectName("labelTitulo")
        layout.addWidget(lbl_rol)
        
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(["Vendedor", "Super admin"])
        self.combo_rol.setCurrentText(rol)
        self.combo_rol.setMinimumHeight(38)
        layout.addWidget(self.combo_rol)

        layout.addStretch()

        # Botón guardar
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_guardar.setObjectName("botonPrincipal")
        self.btn_guardar.setMinimumHeight(45)
        self.btn_guardar.clicked.connect(self.guardar)
        layout.addWidget(self.btn_guardar)

    def guardar(self):
        nombre = self.input_nombre.text().strip()
        correo = self.input_correo.text().strip()
        password = self.input_password.text().strip()
        rol = self.combo_rol.currentText()

        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre completo es obligatorio.")
            return
        if not correo:
            QMessageBox.warning(self, "Error", "El correo electrónico es obligatorio.")
            return
        if not self.usuario_id and not password:
            QMessageBox.warning(self, "Error", "La contraseña es obligatoria para nuevos usuarios.")
            return

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # --- REGLA 2: Prevención de Colisiones (Verificar antes de Guardar) ---
        try:
            resp = requests.get("https://api-pro-electro.pro-electro.workers.dev/api/estado_tabla?tabla=usuarios", timeout=3)
            if resp.status_code == 200:
                total_nube = resp.json().get("total", 0)
                
                cursor.execute("SELECT COUNT(*) FROM usuarios")
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
            if self.usuario_id: # EDITAR
                if password:
                    hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cursor.execute("""
                        UPDATE usuarios 
                        SET nombre_completo=?, correo=?, password=?, rol=? 
                        WHERE id=?
                    """, (nombre, correo, hash_pw, rol, self.usuario_id))
                    
                    datos_dict = {
                        "id": self.usuario_id,
                        "nombre_completo": nombre,
                        "correo": correo,
                        "password": hash_pw,
                        "rol": rol
                    }
                else:
                    cursor.execute("""
                        UPDATE usuarios 
                        SET nombre_completo=?, correo=?, rol=? 
                        WHERE id=?
                    """, (nombre, correo, rol, self.usuario_id))
                    
                    datos_dict = {
                        "id": self.usuario_id,
                        "nombre_completo": nombre,
                        "correo": correo,
                        "rol": rol
                    }
                
                conexion.commit()
                
                # --- REGLA 3 (UPDATE): Nube Primero ---
                exito, msj = operacion_crud_nube('usuarios', 'UPDATE', datos_dict, self.usuario_id)
                if not exito: 
                    raise Exception(f"Error en la nube: {msj}")
                
            else: # NUEVO
                hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("""
                    INSERT INTO usuarios (nombre_completo, correo, password, rol) 
                    VALUES (?, ?, ?, ?)
                """, (nombre, correo, hash_pw, rol))
                
                nuevo_id = cursor.lastrowid
                datos_dict = {
                    "id": nuevo_id,
                    "nombre_completo": nombre,
                    "correo": correo,
                    "password": hash_pw,
                    "rol": rol
                }
                
                conexion.commit()
                
                # --- REGLA 3 (INSERT): Nube Primero ---
                exito, nuevo_id_nube = operacion_crud_nube('usuarios', 'INSERT', datos_dict)
                if not exito: 
                    raise Exception(f"Error en la nube: {nuevo_id_nube}")
            
            # SOLO UN MENSAJE DE ÉXITO AL FINAL
            QMessageBox.information(self, "Éxito", "Usuario guardado correctamente.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {str(e)}")
        finally:
            conexion.close()
            
class VistaUsuarios(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1200)  # Aumentado para dar espacio a la nueva columna
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- CABECERA ---
        header_layout = QHBoxLayout()
        
        titulo = QLabel("👥 Gestión de Usuarios")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍 Buscar por nombre o correo...")
        self.input_buscar.setFixedWidth(350)
        self.input_buscar.setMinimumHeight(40)
        self.input_buscar.textChanged.connect(self.cargar_datos)

        self.btn_agregar = QPushButton("➕ Agregar Usuario")
        self.btn_agregar.setObjectName("botonAgregar")
        self.btn_agregar.setMinimumHeight(40)
        self.btn_agregar.setMinimumWidth(160)
        self.btn_agregar.clicked.connect(self.agregar_usuario)

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(self.input_buscar)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.btn_agregar)
        layout.addLayout(header_layout)

        # --- TABLA ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)  # Aumentado a 5 columnas
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre Completo", "Correo Electrónico", "Rol", "Acciones"])
        
        # Configurar el ancho de las columnas
        self.tabla.setColumnWidth(0, 80)    # ID
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Nombre
        self.tabla.setColumnWidth(2, 280)   # Correo
        self.tabla.setColumnWidth(3, 130)   # Rol
        self.tabla.setColumnWidth(4, 280)   # Acciones
        
        # Configurar la tabla
        self.tabla.setAlternatingRowColors(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(True)
        
        # Establecer colores de selección
        self.tabla.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F5F5F5;
                selection-background-color: #3498db;
                selection-color: white;
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
        
        # Altura de las filas
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        
        # Conectar doble clic para editar
        self.tabla.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        layout.addWidget(self.tabla)

        self.cargar_datos()

    def on_cell_double_clicked(self, row, column):
        """Maneja el evento de doble clic en una celda"""
        # Obtener los datos del usuario de la fila seleccionada
        item_id = self.tabla.item(row, 0)
        item_nombre = self.tabla.item(row, 1)
        item_correo = self.tabla.item(row, 2)
        item_rol = self.tabla.item(row, 3)
        
        if item_id and item_nombre and item_correo and item_rol:
            # Extraer el ID numérico del formato "U001"
            uid_text = item_id.text()
            uid = int(uid_text[1:])  # Quita la 'U' y convierte a entero
            nombre = item_nombre.text()
            correo = item_correo.text()
            rol = item_rol.text()
            
            # Abrir diálogo de edición
            self.editar_usuario(uid, nombre, correo, rol)

    def crear_widget_acciones(self, uid, nombre, correo, rol):
        """Crea un widget con los botones de acción bien espaciados"""
        widget = QWidget()
        
        # IMPORTANTE: Establecer atributos para que el widget no interfiera con la selección
        widget.setAttribute(Qt.WA_TranslucentBackground)
        widget.setAutoFillBackground(False)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(15)
        
        # Botón Editar
        btn_editar = QPushButton("✏️ Editar")
        btn_editar.setObjectName("botonEditar")
        btn_editar.setMinimumWidth(90)
        btn_editar.setMinimumHeight(36)
        
        # Botón Eliminar
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.setObjectName("botonEliminar")
        btn_eliminar.setMinimumWidth(90)
        btn_eliminar.setMinimumHeight(36)
        
        # Conectar señales
        btn_editar.clicked.connect(lambda checked, id=uid, n=nombre, c=correo, r=rol: 
                                  self.editar_usuario(id, n, c, r))
        btn_eliminar.clicked.connect(lambda checked, id=uid, n=nombre: 
                                    self.eliminar_usuario(id, n))
        
        # Centrar los botones
        layout.addStretch()
        layout.addWidget(btn_editar)
        layout.addWidget(btn_eliminar)
        layout.addStretch()
        
        # Asegurar que el widget propague los eventos de ratón a la tabla
        widget.setFocusPolicy(Qt.NoFocus)
        
        return widget

    def cargar_datos(self):
        filtro = self.input_buscar.text().strip()
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        query = """
            SELECT id, nombre_completo, correo, rol 
            FROM usuarios 
            WHERE nombre_completo LIKE ? OR correo LIKE ? 
            ORDER BY id DESC
        """
        cursor.execute(query, (f"%{filtro}%", f"%{filtro}%"))
        usuarios = cursor.fetchall()
        conexion.close()

        self.tabla.setRowCount(len(usuarios))
        
        for fila, (uid, nombre, correo, rol) in enumerate(usuarios):
            # ID con formato
            item_id = QTableWidgetItem(f"U{uid:03d}")
            item_id.setTextAlignment(Qt.AlignCenter)
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 0, item_id)
            
            # Nombre Completo
            item_nombre = QTableWidgetItem(nombre)
            item_nombre.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            item_nombre.setFlags(item_nombre.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 1, item_nombre)
            
            # Correo
            item_correo = QTableWidgetItem(correo)
            item_correo.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            item_correo.setFlags(item_correo.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 2, item_correo)
            
            # Rol
            item_rol = QTableWidgetItem(rol)
            item_rol.setTextAlignment(Qt.AlignCenter)
            item_rol.setFlags(item_rol.flags() & ~Qt.ItemIsEditable)
            if rol == "Super admin":
                item_rol.setForeground(QColor(200, 0, 0))  # Rojo oscuro
                font = QFont("Arial", 10, QFont.Bold)
                item_rol.setFont(font)
            self.tabla.setItem(fila, 3, item_rol)

            # Widget de acciones
            widget_acciones = self.crear_widget_acciones(uid, nombre, correo, rol)
            self.tabla.setCellWidget(fila, 4, widget_acciones)

    def agregar_usuario(self):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        dialogo = DialogoUsuario(self)
        if dialogo.exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Usuario agregado correctamente.")

    def editar_usuario(self, uid, nombre, correo, rol):
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------

        dialogo = DialogoUsuario(self, uid, nombre, correo, rol)
        if dialogo.exec():
            self.cargar_datos()
            QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente.")

    def eliminar_usuario(self, uid, nombre):
        # Prevenir eliminar al último Super Admin
        if nombre == "Administrador Principal":
            QMessageBox.warning(self, "Acción no permitida", 
                              "No se puede eliminar al administrador principal.")
            return
            
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar. Las modificaciones requieren conexión en tiempo real.")
            return
        # ------------------------------------------
            
        respuesta = QMessageBox.question(
            self, 
            "Confirmar Eliminación", 
            f"¿Estás seguro de que deseas eliminar al usuario '{nombre}'?\n\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            # --- REGLA 3: ONLINE-FIRST (NUBE PRIMERO) ---
            exito, mensaje = operacion_crud_nube('usuarios', 'DELETE', registro_id=uid)
            
            if not exito:
                QMessageBox.critical(self, "Error en la Nube", f"No se pudo eliminar en el servidor:\n{mensaje}")
                return # Detenemos todo, no borramos el local
            
            # --- LOCAL DESPUÉS DEL ÉXITO EN LA NUBE ---
            try:
                conexion = obtener_conexion()
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM usuarios WHERE id=?", (uid,))
                conexion.commit()
                conexion.close()
                
                self.cargar_datos()
                QMessageBox.information(self, "Éxito", "Usuario eliminado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error Local", f"No se pudo eliminar: {str(e)}")