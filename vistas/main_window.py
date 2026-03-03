import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QStackedWidget, QLabel)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from vistas.usuarios import VistaUsuarios
from vistas.clientes import VistaClientes
from vistas.proveedores import VistaProveedores
from vistas.inventario import VistaInventario
from vistas.cotizaciones import VistaCotizaciones
from vistas.datos_fiscales import VistaDatosFiscales

class MainWindow(QMainWindow):
    def __init__(self, login_window):
        super().__init__()
        self.login_window = login_window
        self.setWindowTitle("Pro Electro - Sistema de Gestión")
        self.resize(1024, 768)
        self.showMaximized()

        # Widget central
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QVBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # 1. BARRA SUPERIOR (Menú)
        barra_superior = QWidget()
        barra_superior.setStyleSheet("background-color: #FFFFFF; border-bottom: 2px solid #CBD5E0;")
        layout_menu = QHBoxLayout(barra_superior)
        layout_menu.setContentsMargins(20, 10, 20, 10)

        # Logo en la barra superior
        lbl_logo = QLabel()
        ruta_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "logo.png")
        if os.path.exists(ruta_logo):
            pixmap = QPixmap(ruta_logo)
            # Asegurar que la imagen mantenga su transparencia
            pixmap = pixmap.scaled(150, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pixmap)
            # Eliminar cualquier fondo o borde del QLabel
            lbl_logo.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)
        else:
            lbl_logo.setText("PRO ELECTRO")
            lbl_logo.setStyleSheet("font-weight: bold; font-size: 20px; background-color: transparent;")
        layout_menu.addWidget(lbl_logo)
        layout_menu.addSpacing(30)

        # Botones de navegación
        self.botones_menu = []
        opciones_menu = ["Usuarios", "Clientes", "Proveedores", "Inventario", "Cotización", "Datos Fiscales", "Salir"]
        
        for index, opcion in enumerate(opciones_menu):
            btn = QPushButton(opcion)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { border: none; padding: 10px 15px; font-size: 15px; font-weight: bold; color: #4A5568; }
                QPushButton:hover { color: #2B6CB0; }
                QPushButton:checked { border-bottom: 3px solid #3182CE; color: #2D3748; }
            """)
            btn.setCheckable(True)
            if opcion == "Salir":
                btn.clicked.connect(self.cerrar_sesion)
                layout_menu.addStretch()
            else:
                btn.clicked.connect(lambda checked, idx=index: self.cambiar_vista(idx))
            
            layout_menu.addWidget(btn)
            self.botones_menu.append(btn)

        layout_principal.addWidget(barra_superior)

        # 2. CONTENEDOR DE VISTAS (QStackedWidget)
        self.contenedor_vistas = QStackedWidget()
        layout_principal.addWidget(self.contenedor_vistas)

        # Agregar las vistas al contenedor
        self.vista_usuarios = VistaUsuarios()
        self.contenedor_vistas.addWidget(self.vista_usuarios)
        
        self.vista_clientes = VistaClientes()
        self.contenedor_vistas.addWidget(self.vista_clientes)
        
        self.vista_proveedores = VistaProveedores()
        self.contenedor_vistas.addWidget(self.vista_proveedores)
        
        self.vista_inventario = VistaInventario()
        self.contenedor_vistas.addWidget(self.vista_inventario)
        
        self.vista_cotizaciones = VistaCotizaciones()
        self.contenedor_vistas.addWidget(self.vista_cotizaciones)
        
        self.vista_datos_fiscales = VistaDatosFiscales()
        self.contenedor_vistas.addWidget(self.vista_datos_fiscales)
        
        # Conectar señales de la vista de cotizaciones para actualizar inventario
        self.vista_cotizaciones.productos_actualizados.connect(self.actualizar_inventario)

        # Iniciar en la primera pestaña
        self.cambiar_vista(0)

    def cambiar_vista(self, index):
        """Cambia la vista y actualiza los datos si es necesario"""
        
        # Actualizar la vista de inventario SIEMPRE que se muestre
        if index == 3:  # Índice de "Inventario" (Usuarios=0, Clientes=1, Proveedores=2, Inventario=3, Cotización=4)
            self.vista_inventario.cargar_datos()
        
        # También actualizar otras vistas si es necesario (por ejemplo, proveedores, clientes)
        elif index == 0:  # Usuarios
            if hasattr(self.vista_usuarios, 'cargar_datos'):
                self.vista_usuarios.cargar_datos()
        elif index == 1:  # Clientes
            if hasattr(self.vista_clientes, 'cargar_datos'):
                self.vista_clientes.cargar_datos()
        elif index == 2:  # Proveedores
            if hasattr(self.vista_proveedores, 'cargar_datos'):
                self.vista_proveedores.cargar_datos()
        
        self.contenedor_vistas.setCurrentIndex(index)
        
        # Actualizar estado visual de los botones (subrayado azul)
        for i, btn in enumerate(self.botones_menu):
            if btn.text() != "Salir":
                btn.setChecked(i == index)

    def actualizar_inventario(self):
        """Actualiza la vista de inventario cuando se modifican productos desde cotizaciones"""
        if hasattr(self, 'vista_inventario'):
            self.vista_inventario.cargar_datos()

    def cerrar_sesion(self):
        self.login_window.show()
        self.close()