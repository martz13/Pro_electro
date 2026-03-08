from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QDialog, QMessageBox, QGridLayout, QComboBox, QListWidget, QListWidgetItem 
)
from PySide6.QtCore import Qt
import requests
from base_datos.conexion import obtener_conexion,forzar_descarga_nube,operacion_crud_nube


# ────────────────────────────────────────────────
# Diálogo para crear nueva Unidad de Medida
# ────────────────────────────────────────────────
class DialogoNuevaUM(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Unidad de Medida")
        self.setFixedSize(380, 240)
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

        layout.addStretch()

        btn = QPushButton("Guardar")
        btn.setMinimumHeight(45)
        btn.clicked.connect(self.guardar)
        layout.addWidget(btn)

    def guardar(self):
        sigla = self.input_sigla.text().strip().upper()
        desc  = self.input_desc.text().strip()

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
                "descripcion": desc
            }

            # --- REGLA 3: NUBE PRIMERO (Genera el ID) ---
            exito, nuevo_id_nube = operacion_crud_nube('catalogo_um', 'INSERT', datos_dict)
            if not exito: raise Exception(f"Error en la nube: {nuevo_id_nube}")

            # --- LOCAL USANDO EL ID MAESTRO DE LA NUBE ---
            cursor = conn.cursor()
            cursor.execute("INSERT INTO catalogo_um (id, sigla, descripcion) VALUES (?, ?, ?)", (nuevo_id_nube, sigla, desc))
            
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
# Diálogo para agregar / editar producto
# ────────────────────────────────────────────────
class DialogoProducto(QDialog):
    def __init__(self, parent=None, producto_datos=None):
        super().__init__(parent)
        self.producto_id = producto_datos[0] if producto_datos else None
        titulo = "Editar Producto" if self.producto_id else "Nuevo Producto"
        self.setWindowTitle(titulo)
        self.setFixedSize(780, 420)
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

        layout.addLayout(grid)
        layout.addStretch()

        btn_guardar = QPushButton("Guardar Cambios" if self.producto_id else "Crear Producto")
        btn_guardar.setObjectName("botonPrincipal")
        btn_guardar.setMinimumHeight(48)
        btn_guardar.clicked.connect(self.guardar)
        layout.addWidget(btn_guardar, alignment=Qt.AlignCenter)

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

        datos_dict = {"codigo_producto": codigo, "descripcion": desc, "stock": stock, "um": um, "proveedor_id": prov_id, "marca": marca, "precio_compra": compra, "precio_venta": venta}

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

                cursor.execute("UPDATE inventario SET codigo_producto=?, descripcion=?, stock=?, um=?, proveedor_id=?, marca=?, precio_compra=?, precio_venta=? WHERE id=?", 
                               (codigo, desc, stock, um, prov_id, marca, compra, venta, self.producto_id))
                
                cursor.execute("PRAGMA foreign_keys = ON;")
            else:
                exito, nuevo_id = operacion_crud_nube('inventario', 'INSERT', datos_dict)
                if not exito: raise Exception(nuevo_id)
                cursor.execute("INSERT INTO inventario (id, codigo_producto, descripcion, stock, um, proveedor_id, marca, precio_compra, precio_venta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                               (nuevo_id, codigo, desc, stock, um, prov_id, marca, compra, venta))
                
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
            SELECT id, sigla, descripcion 
            FROM catalogo_um 
            ORDER BY sigla
        """)
        unidades = cursor.fetchall()
        conn.close()

        self.tabla.setRowCount(len(unidades))

        for fila, (uid, sigla, descripcion) in enumerate(unidades):
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
            btn_editar.clicked.connect(lambda checked, u=uid, s=sigla, d=descripcion: 
                                      self.editar_um(u, s, d))
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
            

    def editar_um(self, uid, sigla_actual, descripcion_actual):
        """Abre diálogo para editar una unidad de medida"""
        # --- REGLA 1: Bloqueo de UI sin internet ---
        try:
            requests.get("https://api-pro-electro.pro-electro.workers.dev", timeout=3)
        except requests.exceptions.RequestException:
            QMessageBox.warning(self, "Sin conexión", "Revisa tu conexión a internet para continuar.")
            return
        # ------------------------------------------
        dialogo = DialogoEditarUM(self, uid, sigla_actual, descripcion_actual)
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
    def __init__(self, parent=None, uid=None, sigla_actual="", descripcion_actual=""):
        super().__init__(parent)
        self.uid = uid
        self.sigla_actual = sigla_actual
        self.setWindowTitle(f"Editar Unidad de Medida: {sigla_actual}")
        self.setFixedSize(380, 260)
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
            um_dict = {"sigla": nueva_sigla, "descripcion": nueva_desc}
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
                UPDATE catalogo_um SET sigla = ?, descripcion = ? WHERE id = ?
            """, (nueva_sigla, nueva_desc, self.uid))
            
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

# ────────────────────────────────────────────────
# Vista principal de Inventario
# ────────────────────────────────────────────────
class VistaInventario(QWidget):
    def __init__(self, rol="Super admin"):
        super().__init__()
        self.rol = rol
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
        header.setStretchLastSection(False)

        # Columnas fijas
        fixed = {
            0:  55,   # ID
            1: 140,   # Código
            3:  80,   # Stock
            4:  65,   # UM
            7: 100,   # Costo
            8: 100,   # Venta
            9: 220    # Acciones
        }
        for col, ancho in fixed.items():
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.tabla.setColumnWidth(col, ancho)

        # Columnas que crecen
        for col in [2, 5, 6]:  # Descripción, Proveedor, Marca
            header.setSectionResizeMode(col, QHeaderView.Stretch)

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
        lay.setContentsMargins(12, 4, 12, 4)
        lay.setSpacing(10)

        btn_edit = QPushButton("✏️ Editar")
        btn_edit.setObjectName("botonEditar")
        btn_edit.clicked.connect(lambda _, p=prod: self.editar_producto(p))

        btn_del = QPushButton("🗑️ Eliminar")
        btn_del.setObjectName("botonEliminar")
        btn_del.clicked.connect(lambda _, pid=prod[0], d=prod[2]: self.eliminar_producto(pid, d))

        lay.addStretch()
        lay.addWidget(btn_edit)
        lay.addWidget(btn_del)
        lay.addStretch()

        return widget

    def cargar_datos(self):
        texto = f"%{self.buscar.text().strip()}%"
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, codigo_producto, descripcion, stock, um, proveedor_id, marca,
                   precio_compra, precio_venta
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