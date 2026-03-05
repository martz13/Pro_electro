import sys
import os
from PySide6.QtWidgets import QApplication
from base_datos.conexion import inicializar_bd, realizar_descarga_inicial
from vistas.login import LoginWindow
from utilidades.auto_inicio import configurar_inicio_automatico


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    inicializar_bd()
    realizar_descarga_inicial()
    configurar_inicio_automatico()
    app = QApplication(sys.argv)
    

    ruta_estilos = resource_path("recursos/estilos.qss")
    if os.path.exists(ruta_estilos):
        with open(ruta_estilos, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    ventana = LoginWindow()
    ventana.show()

    sys.exit(app.exec())