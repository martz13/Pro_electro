import os
import bcrypt
import smtplib
import random
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QSpacerItem, QSizePolicy, 
                               QMessageBox, QInputDialog)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QSize
from base_datos.conexion import obtener_conexion
from vistas.main_window import MainWindow

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Electro - Iniciar Sesión")
        self.setFixedSize(450, 580)
        
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
        
        self.password_visible = False
        self.update_password_icon()
        self.btn_toggle_password.clicked.connect(self.toggle_password_visibility)
        
        password_layout.addWidget(self.input_password)
        password_layout.addWidget(self.btn_toggle_password)
        
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
        self.btn_olvide.clicked.connect(self.recuperar_password) # Conectamos el nuevo método
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
        if self.password_visible:
            self.btn_toggle_password.setText("👁️")
            self.btn_toggle_password.setToolTip("Ocultar contraseña")
        else:
            self.btn_toggle_password.setText("👁️‍🗨️")
            self.btn_toggle_password.setToolTip("Mostrar contraseña")

    def toggle_password_visibility(self):
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.input_password.setEchoMode(QLineEdit.Normal)
        else:
            self.input_password.setEchoMode(QLineEdit.Password)
        self.update_password_icon()

    def validar_login(self):
        correo = self.input_correo.text().strip()
        password = self.input_password.text()
        
        if not password:
            password = "" 

        if not correo or not password:
            QMessageBox.warning(self, "Campos vacíos", "Por favor, ingresa tu correo y contraseña.")
            return
        
        URL_API = "https://api-pro-electro.pro-electro.workers.dev/api/login"
        
        hash_guardado = None
        rol_usuario = None
        origen_login = "Local"

        try:
            # 1. INTENTAR CONECTAR A LA NUBE PRIMERO
            # Ponemos un timeout corto (3 segs) para que la app no se congele si no hay internet
            respuesta = requests.post(URL_API, json={"correo": correo}, timeout=3)
            
            if respuesta.status_code == 200:
                datos = respuesta.json()
                if datos.get("success"):
                    hash_guardado = datos["usuario"]["password"]
                    rol_usuario = datos["usuario"]["rol"]
                    origen_login = "Nube"
        except requests.exceptions.RequestException:
            # Si hay error de conexión, timeout o no hay internet, ignoramos y pasamos al local
            pass

        # 2. SI LA NUBE FALLÓ O NO ENCONTRÓ AL USUARIO, BUSCAR EN LOCAL
        if not hash_guardado:
            try:
                conexion = obtener_conexion()
                cursor = conexion.cursor()
                cursor.execute("SELECT password, rol FROM usuarios WHERE correo = ?", (correo,))
                usuario = cursor.fetchone()
                conexion.close()

                if usuario:
                    hash_guardado = usuario[0]
                    rol_usuario = usuario[1]
                    origen_login = "Local"
            except Exception as e:
                QMessageBox.critical(self, "Error de Base de Datos", f"Hubo un problema al conectar localmente:\n{str(e)}")
                return

        # 3. VERIFICAR LA CONTRASEÑA
        if hash_guardado:
            if isinstance(hash_guardado, str):
                hash_guardado = hash_guardado.encode('utf-8')
            
            if bcrypt.checkpw(password.encode('utf-8'), hash_guardado):
                print(f"Inicio de sesión exitoso desde: {origen_login}") # Opcional: para depuración
                self.main_window = MainWindow(self, rol_usuario)
                self.main_window.show()
                self.hide()
            else:
                QMessageBox.warning(self, "Acceso Denegado", "Contraseña incorrecta.")
        else:
            QMessageBox.warning(self, "Acceso Denegado", "El correo ingresado no existe o no hay conexión.")
    # ========================================================
    # MÉTODOS PARA RECUPERACIÓN DE CONTRASEÑA / ACCESO POR NIP
    # ========================================================
    def recuperar_password(self):
        correo = self.input_correo.text().strip()
        
        if not correo:
            QMessageBox.warning(self, "Campo vacío", "Por favor, ingresa tu correo en el campo de texto antes de presionar '¿Olvidaste tu contraseña?'.")
            return

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("SELECT rol FROM usuarios WHERE correo = ?", (correo,))
            usuario = cursor.fetchone()
            conexion.close()

            if not usuario:
                QMessageBox.warning(self, "Error", "El usuario no existe.")
                return

            rol = usuario[0]

            if rol == "Vendedor":
                QMessageBox.information(self, "Recuperar Acceso", "Contactar al administrador del sistema al número +52 1 81 8255 2128")
            elif rol == "Super admin":
                self.enviar_nip_y_validar(rol)

        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Hubo un problema al consultar el usuario:\n{str(e)}")

    def enviar_nip_y_validar(self, rol):
        # Generar código NIP aleatorio de 4 dígitos
        nip = str(random.randint(1000, 9999))
        
        remitente = "edwgrro@gmail.com"
        destinatario = "edwgrro@gmail.com"
        password_app = "meiq mrgx xiiv vvby"

        # Crear el mensaje de correo
        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = "Código de Acceso de Emergencia - PRO ELECTRO MEXICO"

        # Diseño profesional en HTML para el correo
        cuerpo_html = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; padding: 20px; color: #333;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); overflow: hidden;">
                <div style="background-color: #1a1a1a; padding: 20px; text-align: center;">
                    <h2 style="color: #ffffff; margin: 0; letter-spacing: 2px;">PRO ELECTRO MEXICO</h2>
                </div>
                <div style="padding: 30px;">
                    <h3 style="color: #2c3e50; margin-top: 0;">Código de Verificación</h3>
                    <p style="font-size: 15px; line-height: 1.6;">Hola,</p>
                    <p style="font-size: 15px; line-height: 1.6;">Se ha solicitado un acceso de emergencia al sistema para tu cuenta de Super Administrador.</p>
                    <p style="font-size: 15px; line-height: 1.6;">Tu NIP de seguridad de 4 dígitos es:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <span style="font-size: 36px; font-weight: bold; background-color: #f8f9fa; padding: 15px 40px; border-radius: 8px; color: #c00000; border: 2px dashed #c00000; letter-spacing: 10px;">
                            {nip}
                        </span>
                    </div>
                    
                    <p style="font-size: 14px; color: #7f8c8d; text-align: center;">Este código es válido únicamente para esta sesión. Si no solicitaste este acceso, por favor ignora este correo.</p>
                </div>
                <div style="background-color: #f8f9fa; padding: 15px; text-align: center; border-top: 1px solid #eeeeee;">
                    <p style="font-size: 12px; color: #95a5a6; margin: 0;">&copy; {random.choice(['2024', '2025', '2026'])} Pro Electro Mexico. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(cuerpo_html, 'html'))

        try:
            # Mostramos un mensaje de que estamos procesando (puede tardar un par de segundos)
            QMessageBox.information(self, "Enviando", "Se está generando y enviando tu NIP de seguridad. Presiona OK para continuar...")
            
            # Conexión SMTP a Gmail
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(remitente, password_app)
            server.send_message(msg)
            server.quit()
            
            # Pedir el NIP al usuario en la app
            nip_ingresado, ok = QInputDialog.getText(self, "Verificación de Seguridad", 
                                                     "Se ha enviado un NIP de 4 dígitos a edwgrro@gmail.com.\n\nIngresa el NIP:",
                                                     QLineEdit.Password)
            
            if ok and nip_ingresado:
                if nip_ingresado.strip() == nip:
                    QMessageBox.information(self, "Acceso Concedido", "NIP verificado correctamente. Bienvenido.")
                    self.main_window = MainWindow(self, rol)
                    self.main_window.show()
                    self.hide()
                else:
                    QMessageBox.warning(self, "Acceso Denegado", "El NIP ingresado es incorrecto.")
                    
        except smtplib.SMTPAuthenticationError:
            QMessageBox.critical(self, "Error de Autenticación", "Fallo al iniciar sesión en el servidor de correo. Revisa la contraseña de aplicación.")
        except Exception as e:
            QMessageBox.critical(self, "Error de Envío", f"No se pudo enviar el correo de recuperación.\nDetalle: {str(e)}")