import os
import requests
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QMessageBox)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from base_datos.conexion import obtener_conexion

from vistas.usuarios import VistaUsuarios
from vistas.clientes import VistaClientes
from vistas.proveedores import VistaProveedores
from vistas.inventario import VistaInventario
from vistas.cotizaciones import VistaCotizaciones
from vistas.datos_fiscales import VistaDatosFiscales

class MainWindow(QMainWindow):
    def __init__(self, login_window, rol="Super admin"):
        super().__init__()
        self.login_window = login_window
        self.rol = rol
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
        opciones_menu = ["Usuarios", "Clientes", "Proveedores", "Inventario", "Cotización", "Datos Fiscales"]
        
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
            if self.rol == "Vendedor" and opcion in ["Usuarios", "Proveedores", "Datos Fiscales"]:
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
        
        self.vista_clientes = VistaClientes()
        self.contenedor_vistas.addWidget(self.vista_clientes)
        
        self.vista_proveedores = VistaProveedores()
        self.contenedor_vistas.addWidget(self.vista_proveedores)
        
        self.vista_inventario = VistaInventario(self.rol)
        self.contenedor_vistas.addWidget(self.vista_inventario)
        
        self.vista_cotizaciones = VistaCotizaciones()
        self.contenedor_vistas.addWidget(self.vista_cotizaciones)
        
        self.vista_datos_fiscales = VistaDatosFiscales()
        self.contenedor_vistas.addWidget(self.vista_datos_fiscales)
        
        if self.rol == "Vendedor":
            self.cambiar_vista(1)
        else:
            self.cambiar_vista(0)

    def cambiar_vista(self, index):
        """Cambia la vista y actualiza los datos si es necesario"""
        if index == 3:  
            self.vista_inventario.cargar_datos()
        elif index == 0 and hasattr(self.vista_usuarios, 'cargar_datos'):
            self.vista_usuarios.cargar_datos()
        elif index == 1 and hasattr(self.vista_clientes, 'cargar_datos'):
            self.vista_clientes.cargar_datos()
        elif index == 2 and hasattr(self.vista_proveedores, 'cargar_datos'):
            self.vista_proveedores.cargar_datos()
        elif index == 4 and hasattr(self.vista_cotizaciones, 'cargar_datos'):
            self.vista_cotizaciones.cargar_datos()
        
        self.contenedor_vistas.setCurrentIndex(index)
        
        for i, btn in enumerate(self.botones_menu):
            btn.setChecked(i == index)

    # ==========================================
    # LÓGICA DE SINCRONIZACIÓN MANUAL
    # ==========================================
    def forzar_sincronizacion(self):
        respuesta = QMessageBox.question(
            self, "Actualizar Datos",
            "¿Deseas descargar los datos más recientes de la nube?\n\nEsto actualizará inventarios, clientes y cotizaciones en esta computadora.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.No:
            return

        # Cambiamos visualmente el botón para que el usuario sepa que está cargando
        self.btn_sync.setText("⏳ Descargando...")
        self.btn_sync.setEnabled(False)
        self.repaint() # Obligamos a la ventana a actualizar el texto del botón al instante

        try:
            URL_API_PULL = "https://api-pro-electro.pro-electro.workers.dev/api/descargar_todo"
            respuesta_nube = requests.get(URL_API_PULL, timeout=15)
            
            if respuesta_nube.status_code == 200:
                datos_nube = respuesta_nube.json()
                
                if datos_nube.get("success"):
                    data = datos_nube["data"]
                    
                    conexion = obtener_conexion()
                    cursor = conexion.cursor()
                    cursor.execute("PRAGMA foreign_keys = OFF;")
                    
                    # Función para insertar datos masivamente reemplazando los locales viejos
                    def insertar_lote(tabla, registros):
                        if not registros: return
                        columnas = ", ".join(registros[0].keys())
                        placeholders = ", ".join(["?"] * len(registros[0]))
                        query = f"INSERT OR REPLACE INTO {tabla} ({columnas}) VALUES ({placeholders})"
                        valores = [tuple(r.values()) for r in registros]
                        cursor.executemany(query, valores)
                    
                    # Ejecutamos las inserciones
                    insertar_lote("usuarios", data.get("usuarios", []))
                    insertar_lote("clientes", data.get("clientes", []))
                    insertar_lote("proveedores", data.get("proveedores", []))
                    insertar_lote("inventario", data.get("inventario", []))
                    insertar_lote("cotizaciones", data.get("cotizaciones", []))
                    insertar_lote("cotizaciones_detalle", data.get("cotizaciones_detalle", []))
                    insertar_lote("catalogo_um", data.get("catalogo_um", []))
                    insertar_lote("datos_fiscales", data.get("datos_fiscales", []))
                    
                    cursor.execute("PRAGMA foreign_keys = ON;")
                    conexion.commit()
                    conexion.close()

                    # Refrescar la pantalla actual para que aparezcan los datos recién descargados
                    idx_actual = self.contenedor_vistas.currentIndex()
                    self.cambiar_vista(idx_actual)

                    QMessageBox.information(self, "Sincronización Exitosa", "Los datos se han actualizado correctamente.")
                else:
                    QMessageBox.critical(self, "Error de Servidor", datos_nube.get('error', 'Error desconocido'))
            else:
                QMessageBox.warning(self, "Error", f"Problema de red. Status: {respuesta_nube.status_code}")
                
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin Conexión", "No se pudo conectar a la nube. Verifica tu conexión a internet.")
        except Exception as e:
            QMessageBox.critical(self, "Error Local", f"Ocurrió un error al guardar los datos:\n{str(e)}")
        finally:
            # Regresamos el botón a la normalidad
            self.btn_sync.setText("🔄 Sincronizar")
            self.btn_sync.setEnabled(True)

    def cerrar_sesion(self):
        self.login_window.show()
        self.close()