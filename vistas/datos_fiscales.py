from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QTextEdit, QPushButton, QGroupBox, 
                               QGridLayout, QMessageBox)
from PySide6.QtCore import Qt
from base_datos.conexion import obtener_conexion, registrar_en_cola_sync

class VistaDatosFiscales(QWidget):
    def __init__(self):
        super().__init__()
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(30, 30, 30, 30)

        # --- TÍTULO ---
        titulo = QLabel("Datos Fiscales")
        titulo.setStyleSheet("font-size: 26px; font-weight: bold; color: #2D3748;")
        layout_principal.addWidget(titulo)
        layout_principal.addSpacing(10)

        # --- GRUPO: INFORMACIÓN DE LA EMPRESA ---
        grupo_empresa = QGroupBox("Información de la Empresa")
        grupo_empresa.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        grid = QGridLayout(grupo_empresa)
        grid.setVerticalSpacing(15)

        # Fila 0: Nombre de la Empresa
        grid.addWidget(QLabel("Nombre de la Empresa:"), 0, 0)
        self.input_nombre = QLineEdit()
        grid.addWidget(self.input_nombre, 0, 1, 1, 3) # Ocupa 3 columnas para ser más largo

        # Fila 1: Teléfono y RFC
        grid.addWidget(QLabel("Teléfono:"), 1, 0)
        self.input_telefono = QLineEdit()
        grid.addWidget(self.input_telefono, 1, 1)

        grid.addWidget(QLabel("RFC:"), 1, 2)
        self.input_rfc = QLineEdit()
        grid.addWidget(self.input_rfc, 1, 3)

        # Fila 2: Ubicación y Representante Legal
        grid.addWidget(QLabel("Ubicación:"), 2, 0)
        self.input_ubicacion = QLineEdit()
        grid.addWidget(self.input_ubicacion, 2, 1)

        grid.addWidget(QLabel("Representante Legal:"), 2, 2)
        self.input_representante = QLineEdit()
        grid.addWidget(self.input_representante, 2, 3)

        layout_principal.addWidget(grupo_empresa)
        layout_principal.addSpacing(10)

        # --- GRUPO: TÉRMINOS Y CONDICIONES ---
        lbl_terminos = QLabel("Términos y Condiciones")
        lbl_terminos.setStyleSheet("font-size: 16px; font-weight: bold; color: #2D3748;")
        layout_principal.addWidget(lbl_terminos)

        self.input_terminos = QTextEdit()
        # Estilo para que coincida con los QLineEdit
        self.input_terminos.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QTextEdit:focus { border: 1px solid #3182CE; }
        """)
        layout_principal.addWidget(self.input_terminos)
        layout_principal.addSpacing(15)

        # --- BOTÓN GUARDAR ---
        layout_boton = QHBoxLayout()
        layout_boton.addStretch() # Empuja el botón a la derecha
        
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_guardar.setObjectName("botonPrincipal")
        self.btn_guardar.setMinimumWidth(180)
        self.btn_guardar.clicked.connect(self.guardar_datos)
        
        layout_boton.addWidget(self.btn_guardar)
        layout_principal.addLayout(layout_boton)

        # Cargar los datos al iniciar la vista
        self.cargar_datos()

    def cargar_datos(self):
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Intentamos obtener el registro 1
        cursor.execute("SELECT nombre_empresa, telefono, ubicacion, rfc, representante_legal, terminos_condiciones FROM datos_fiscales WHERE id = 1")
        datos = cursor.fetchone()

        if datos:
            self.input_nombre.setText(datos[0] if datos[0] else "")
            self.input_telefono.setText(datos[1] if datos[1] else "")
            self.input_ubicacion.setText(datos[2] if datos[2] else "")
            self.input_rfc.setText(datos[3] if datos[3] else "")
            self.input_representante.setText(datos[4] if datos[4] else "")
            self.input_terminos.setPlainText(datos[5] if datos[5] else "")
        else:
            # Si por alguna razón la tabla está vacía, insertamos la fila por defecto
            try:
                terminos_defecto = 'Dadas las condiciones comerciales actuales a nivel global, la presente COTIZACION tiene una vigencia de solamente 24 horas a partir de su fecha de emisión. En esta COTIZACIÓN, los Tiempos de Entrega expresados, son aproximados, y NO constituyen compromiso alguno de cumplimiento mientras esta no se convierta en un Pedido fincado. Así mismo, en los casos en que se finque un Pedido y se trate de Mercancia Especial & "Sobre Pedido", el Tiempo de Entrega empezará a contar a partir del Pago ó Anticipo (en su caso) acreditado. En los casos en que se expresen Tiempos de Entrega inmediatos, estos se entienden siempre Salvo Previa Venta (SPV). Pro Electro ofrece la opción de separar material, solamente con una solicitud por escrito emitida por el cliente, y por un lapso no mayor a 24 horas. Después de este tiempo, el material se regresară al almacén para su disposición normal. Así mismo esta COTIZACIÓN no se considera Pedido fincado, por lo que, si el cliente decide unilateralmente depositar cualquier cantidad de dinero antes de fincar oficialmente un Pedido y que Pro Electro haya emitido alguna Remisión & Factura, no se considerará compromiso alguno de surtimiento de mercancia que no se tenga para Entrega Inmediata Los precios ofrecidos se entienden LAB. Monterrey y su área metropolitana y la mercancia puede ser entregada en nuestras instalaciones ó a domicilio. Si fuera a domicilio, se entregaria "al pie" de la obra o domicilie solicitado y no se ofrecen maniobras especiales de subir o bajar a otros niveles a menos que se exprese por escrito otra condición. Así mismo Pre Electre no ofrece el servicio de Recolección de la mercancia entregada a domicilio, que por alguna razón el cliente solicitara cambiar por otra mercancia. No se aceptan devoluciones de mercancia. En casos excepcionales y a juicio y consideración de Pro Electro, se podria aceptar, si y solo si, que la mercancia no haya side traida exprofeso del fabricante para el cliente (mercancia sobre pedido), que venga absolutamente sin usar, en su empaque original y en excelentes condiciones. Todo esto en un plazo no mayor de 48 horas. Dicha devolución estará sujeta a un cargo no negociable del 20% del importe neto.'
                
                cursor.execute("""
                    INSERT INTO datos_fiscales (id, nombre_empresa, telefono, ubicacion, rfc, representante_legal, terminos_condiciones) 
                    VALUES (1, 'PRO ELECTRO MONTERREY', '(81) 8255 2128', 'Monterrey, Nuevo León', 'GUGE9505308Q4','PRO ELECTRO', ?)
                """, (terminos_defecto,))
                
                datos_dict = {
                    "id": 1,
                    "nombre_empresa": "PRO ELECTRO MONTERREY",
                    "telefono": "(81) 8255 2128",
                    "ubicacion": "Monterrey, Nuevo León",
                    "rfc": "GUGE9505308Q4",
                    "representante_legal": "PRO ELECTRO",
                    "terminos_condiciones": terminos_defecto
                }
                
                conexion.commit()
                registrar_en_cola_sync('datos_fiscales', 'INSERT', 1, datos_dict)
                
                self.cargar_datos() # Volvemos a llamar para llenar la interfaz
            except Exception as e:
                print(f"Error al inicializar datos fiscales: {e}")
                
        conexion.close()

    def guardar_datos(self):
        nombre = self.input_nombre.text().strip()
        telefono = self.input_telefono.text().strip()
        ubicacion = self.input_ubicacion.text().strip()
        rfc = self.input_rfc.text().strip()
        representante = self.input_representante.text().strip()
        terminos = self.input_terminos.toPlainText().strip()

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        try:
            # Actualizamos siempre el id=1
            cursor.execute("""
                UPDATE datos_fiscales 
                SET nombre_empresa=?, telefono=?, ubicacion=?, rfc=?, representante_legal=?, terminos_condiciones=?
                WHERE id=1
            """, (nombre, telefono, ubicacion, rfc, representante, terminos))
            
            datos_dict = {
                "nombre_empresa": nombre,
                "telefono": telefono,
                "ubicacion": ubicacion,
                "rfc": rfc,
                "representante_legal": representante,
                "terminos_condiciones": terminos
            }
            
            conexion.commit()
            registrar_en_cola_sync('datos_fiscales', 'UPDATE', 1, datos_dict)
            
            QMessageBox.information(self, "Éxito", "Los datos fiscales se han guardado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar los datos:\n{str(e)}")
        finally:
            conexion.close()