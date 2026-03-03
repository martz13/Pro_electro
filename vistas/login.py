import os
import bcrypt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QSpacerItem, QSizePolicy, 
                               QMessageBox)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QSize
from base_datos.conexion import obtener_conexion
from vistas.main_window import MainWindow

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Electro - Iniciar Sesión")
        self.setFixedSize(450, 580)  # Ligeramente más alto para el nuevo campo
        
        self.layout_principal = QVBoxLayout()
        self.layout_principal.setContentsMargins(40, 40, 40, 40)
        self.layout_principal.setSpacing(15)

        # 1. Logo
        self.logo_label = QLabel()
        ruta_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "logo.png")
        if os.path.exists(ruta_logo):
            pixmap = QPixmap(ruta_logo)
            self.logo_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("[ Imagen del Logo ]")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.layout_principal.addWidget(self.logo_label)

        self.layout_principal.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # 2. Campos de Texto
        self.lbl_correo = QLabel("Correo")
        self.lbl_correo.setObjectName("labelTitulo")
        self.input_correo = QLineEdit()
        self.input_correo.setPlaceholderText("Introduce tu correo")
        self.input_correo.setMinimumHeight(40)
        self.layout_principal.addWidget(self.lbl_correo)
        self.layout_principal.addWidget(self.input_correo)

        self.lbl_password = QLabel("Contraseña")
        self.lbl_password.setObjectName("labelTitulo")
        
        # Contenedor para el campo de contraseña y el botón de mostrar
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(5)
        
        # Campo de contraseña
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Introduce tu contraseña")
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setMinimumHeight(40)
        
        # Botón para mostrar/ocultar contraseña
        self.btn_toggle_password = QPushButton()
        self.btn_toggle_password.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_password.setFixedSize(40, 40)
        self.btn_toggle_password.setCheckable(True)
        self.btn_toggle_password.setObjectName("botonTogglePassword")
        
        # Variable para controlar el estado (True = visible, False = oculto)
        self.password_visible = False
        
        # Configurar iconos (usando emojis como fallback, pero puedes usar iconos reales)
        self.update_password_icon()
        
        # Conectar el botón
        self.btn_toggle_password.clicked.connect(self.toggle_password_visibility)
        
        # Agregar widgets al layout horizontal
        password_layout.addWidget(self.input_password)
        password_layout.addWidget(self.btn_toggle_password)
        
        # Agregar al layout principal
        self.layout_principal.addWidget(self.lbl_password)
        self.layout_principal.addWidget(password_container)

        self.layout_principal.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # 3. Botones
        self.btn_login = QPushButton("Iniciar Sesión")
        self.btn_login.setObjectName("botonPrincipal")
        self.btn_login.setMinimumHeight(45)
        self.btn_login.clicked.connect(self.validar_login)
        self.layout_principal.addWidget(self.btn_login)

        self.btn_olvide = QPushButton("¿Olvidaste tu contraseña?")
        self.btn_olvide.setObjectName("botonEnlace")
        self.btn_olvide.setCursor(Qt.PointingHandCursor)
        self.layout_principal.addWidget(self.btn_olvide, alignment=Qt.AlignCenter)

        self.setLayout(self.layout_principal)
        
        # Aplicar estilos adicionales para el botón de toggle
        self.setStyleSheet("""
            QPushButton#botonTogglePassword {
                background-color: #f0f0f0;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                font-size: 18px;
                padding: 0px;
            }
            QPushButton#botonTogglePassword:hover {
                background-color: #e0e0e0;
                border-color: #3182CE;
            }
            QPushButton#botonTogglePassword:pressed {
                background-color: #d0d0d0;
            }
            QPushButton#botonTogglePassword:checked {
                background-color: #e8f0fe;
                border-color: #3182CE;
            }
        """)

    def update_password_icon(self):
        """Actualiza el icono del botón según el estado"""
        if self.password_visible:
            self.btn_toggle_password.setText("👁️")  # Ojo abierto
            self.btn_toggle_password.setToolTip("Ocultar contraseña")
        else:
            self.btn_toggle_password.setText("👁️‍🗨️")  # Ojo cerrado (o con línea)
            self.btn_toggle_password.setToolTip("Mostrar contraseña")
        
        # Si tienes iconos reales en recursos, puedes usarlos así:
        # ruta_icono = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", 
        #                           "ojo_abierto.png" if self.password_visible else "ojo_cerrado.png")
        # if os.path.exists(ruta_icono):
        #     self.btn_toggle_password.setIcon(QIcon(ruta_icono))
        #     self.btn_toggle_password.setIconSize(QSize(24, 24))
        #     self.btn_toggle_password.setText("")  # Quitar texto si usas iconos

    def toggle_password_visibility(self):
        """Alterna la visibilidad de la contraseña"""
        self.password_visible = not self.password_visible
        
        if self.password_visible:
            self.input_password.setEchoMode(QLineEdit.Normal)
        else:
            self.input_password.setEchoMode(QLineEdit.Password)
        
        self.update_password_icon()

    def validar_login(self):
        correo = self.input_correo.text().strip()
        password = self.input_password.text()  # No hacer strip() para no eliminar espacios
        
        # Validación adicional: verificar que la contraseña no esté vacía después de quitar espacios
        if not password:
            password = ""  # Asegurar que sea string vacío si solo tenía espacios

        if not correo or not password:
            QMessageBox.warning(self, "Campos vacíos", "Por favor, ingresa tu correo y contraseña.")
            return

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("SELECT password, rol FROM usuarios WHERE correo = ?", (correo,))
            usuario = cursor.fetchone()
            conexion.close()

            if usuario:
                hash_guardado = usuario[0]
                # Asegurar que el hash sea bytes
                if isinstance(hash_guardado, str):
                    hash_guardado = hash_guardado.encode('utf-8')
                
                # Comparamos la contraseña ingresada con el hash de la base de datos
                if bcrypt.checkpw(password.encode('utf-8'), hash_guardado):
                    self.main_window = MainWindow(self)
                    self.main_window.show()
                    self.hide()
                else:
                    QMessageBox.warning(self, "Acceso Denegado", "Contraseña incorrecta.")
            else:
                QMessageBox.warning(self, "Acceso Denegado", "El correo ingresado no existe.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Hubo un problema al conectar:\n{str(e)}")