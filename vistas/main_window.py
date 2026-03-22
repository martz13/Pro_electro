import os
import requests
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QMessageBox,QProgressDialog)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from base_datos.conexion import obtener_conexion,SyncThread

from vistas.usuarios import VistaUsuarios
from vistas.clientes import VistaClientes
from vistas.proveedores import VistaProveedores
from vistas.inventario import VistaInventario
from vistas.cotizaciones import VistaCotizaciones
from vistas.datos_fiscales import VistaDatosFiscales
from vistas.ordenes_compra import VistaOrdenesCompra # <-- NUEVO

class MainWindow(QMainWindow):
    def __init__(self, login_window, rol="Super admin", nombre_usuario=""):
        super().__init__()
        self.login_window = login_window
        self.rol = rol
        self.nombre_usuario = nombre_usuario
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

        # Logo
        lbl_logo = QLabel()
        ruta_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "logo.png")
        if os.path.exists(ruta_logo):
            pixmap = QPixmap(ruta_logo)
            pixmap = pixmap.scaled(150, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pixmap)
            lbl_logo.setStyleSheet("QLabel { background-color: transparent; border: none; margin: 0px; padding: 0px; }")
        else:
            lbl_logo.setText("PRO ELECTRO")
            lbl_logo.setStyleSheet("font-weight: bold; font-size: 20px; background-color: transparent;")
        layout_menu.addWidget(lbl_logo)
        layout_menu.addSpacing(30)

        # Botones de navegación principal
        self.botones_menu = []
        opciones_menu = ["Usuarios", "Clientes", "Proveedores", "Inventario", "Cotización","Órdenes de Compra" ,"Datos Fiscales"]
        
        for index, opcion in enumerate(opciones_menu):
            btn = QPushButton(opcion)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { border: none; padding: 10px 15px; font-size: 15px; font-weight: bold; color: #4A5568; }
                QPushButton:hover { color: #2B6CB0; }
                QPushButton:checked { border-bottom: 3px solid #3182CE; color: #2D3748; }
            """)
            btn.setCheckable(True)
            
            # Ocultar botones para Vendedor
            if self.rol == "Vendedor" and opcion in ["Usuarios", "Proveedores", "Datos Fiscales","Órdenes de Compra"]:
                btn.setVisible(False)
            
            btn.clicked.connect(lambda checked, idx=index: self.cambiar_vista(idx))
            layout_menu.addWidget(btn)
            self.botones_menu.append(btn)

        layout_menu.addStretch()

        # --- NUEVO: BOTÓN SINCRONIZAR ---
        self.btn_sync = QPushButton("🔄 Sincronizar")
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.setStyleSheet("""
            QPushButton { border: 1px solid #38A169; padding: 8px 15px; font-size: 14px; font-weight: bold; color: #38A169; border-radius: 5px; background-color: white;}
            QPushButton:hover { background-color: #F0FFF4; }
        """)
        self.btn_sync.clicked.connect(self.forzar_sincronizacion)
        layout_menu.addWidget(self.btn_sync)
        
        layout_menu.addSpacing(10)

        # --- BOTÓN SALIR ---
        btn_salir = QPushButton("Salir")
        btn_salir.setCursor(Qt.PointingHandCursor)
        btn_salir.setStyleSheet("""
            QPushButton { border: none; padding: 10px 15px; font-size: 15px; font-weight: bold; color: #E53E3E; }
            QPushButton:hover { color: #C53030; }
        """)
        btn_salir.clicked.connect(self.cerrar_sesion)
        layout_menu.addWidget(btn_salir)

        layout_principal.addWidget(barra_superior)

        # 2. CONTENEDOR DE VISTAS
        self.contenedor_vistas = QStackedWidget()
        layout_principal.addWidget(self.contenedor_vistas)

        self.vista_usuarios = VistaUsuarios()
        self.contenedor_vistas.addWidget(self.vista_usuarios)
        
        self.vista_clientes = VistaClientes(self.rol, self.nombre_usuario)
        self.contenedor_vistas.addWidget(self.vista_clientes)
        
        self.vista_proveedores = VistaProveedores()
        self.contenedor_vistas.addWidget(self.vista_proveedores)
        
        self.vista_inventario = VistaInventario(self.rol, self.nombre_usuario)
        self.contenedor_vistas.addWidget(self.vista_inventario)
        
        self.vista_cotizaciones = VistaCotizaciones()
        self.contenedor_vistas.addWidget(self.vista_cotizaciones)

        self.vista_ordenes_compra = VistaOrdenesCompra()
        self.contenedor_vistas.addWidget(self.vista_ordenes_compra)
        
        self.vista_datos_fiscales = VistaDatosFiscales()
        self.contenedor_vistas.addWidget(self.vista_datos_fiscales)
        
        if self.rol == "Vendedor":
            self.cambiar_vista(1)
        else:
            self.cambiar_vista(0)

    def cambiar_vista(self, index):
        """Cambia la vista y actualiza los datos si es necesario"""
        if index == 3 and hasattr(self.vista_inventario, 'cargar_datos'):
            self.vista_inventario.cargar_datos()
        elif index == 0 and hasattr(self.vista_usuarios, 'cargar_datos'):
            self.vista_usuarios.cargar_datos()
        elif index == 1 and hasattr(self.vista_clientes, 'cargar_datos'):
            self.vista_clientes.cargar_datos()
        elif index == 2 and hasattr(self.vista_proveedores, 'cargar_datos'):
            self.vista_proveedores.cargar_datos()
        elif index == 4 and hasattr(self.vista_cotizaciones, 'cargar_datos'):
            self.vista_cotizaciones.cargar_datos()
        elif index == 5 and hasattr(self.vista_ordenes_compra, 'cargar_datos'): # <-- NUEVO
            self.vista_ordenes_compra.cargar_datos()
        
        self.contenedor_vistas.setCurrentIndex(index)
        
        for i, btn in enumerate(self.botones_menu):
            btn.setChecked(i == index)

    # ==========================================
    # LÓGICA DE SINCRONIZACIÓN MANUAL
    # ==========================================
    # ==========================================
    # LÓGICA DE SINCRONIZACIÓN MANUAL (CON BARRA)
    # ==========================================
    def forzar_sincronizacion(self):
        respuesta = QMessageBox.question(
            self, "Actualizar Datos",
            "¿Deseas sincronizar los datos con la nube?\n\nEsto subirá las cotizaciones pendientes y descargará la base de datos más reciente.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.No:
            return

        self.btn_sync.setText("⏳ Sincronizando...")
        self.btn_sync.setEnabled(False)

        self.progreso_sync = QProgressDialog("Conectando con la nube...", None, 0, 100, self)
        self.progreso_sync.setWindowTitle("Sincronizando Base de Datos")
        self.progreso_sync.setWindowModality(Qt.WindowModal)
        self.progreso_sync.setMinimumDuration(0)
        self.progreso_sync.setValue(0)

        self.hilo_sync = SyncThread()
        self.hilo_sync.progress.connect(self.actualizar_progreso)
        self.hilo_sync.finished.connect(self.finalizar_sincronizacion)
        self.hilo_sync.start()

    def actualizar_progreso(self, valor, texto):
        self.progreso_sync.setValue(valor)
        self.progreso_sync.setLabelText(texto)

    def finalizar_sincronizacion(self, exito, mensaje):
        self.progreso_sync.close()
        self.btn_sync.setText("🔄 Sincronizar")
        self.btn_sync.setEnabled(True)
        
        if exito:
            # Refrescar la pantalla actual para que aparezcan los datos recién descargados
            idx_actual = self.contenedor_vistas.currentIndex()
            self.cambiar_vista(idx_actual)
            QMessageBox.information(self, "Sincronización Exitosa", mensaje)
        else:
            QMessageBox.warning(self, "Aviso", mensaje)
            
            
    def cerrar_sesion(self):
        self.login_window.show()
        self.close()