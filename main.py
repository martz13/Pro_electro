import sys
import os
from PySide6.QtWidgets import QApplication
from base_datos.conexion import inicializar_bd
from vistas.login import LoginWindow

if __name__ == "__main__":
    # 1. Asegurarnos de que la base de datos local y el usuario existan
    inicializar_bd()

    # 2. Iniciar la aplicación
    app = QApplication(sys.argv)

    # 3. Cargar la hoja de estilos global
    ruta_estilos = os.path.join(os.path.dirname(__file__), "recursos", "estilos.qss")
    if os.path.exists(ruta_estilos):
        with open(ruta_estilos, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # 4. Mostrar la interfaz de Login
    ventana = LoginWindow()
    ventana.show()

    # 5. Ejecutar el bucle principal
    sys.exit(app.exec())