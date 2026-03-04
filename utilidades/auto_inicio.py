import os
import sys
import platform

def configurar_inicio_automatico():
    """
    Detecta el SO y configura el sincronizador para que arranque automáticamente 
    sin intervención del usuario, soportando código fuente y archivos .exe.
    """
    sistema = platform.system()
    
    # ¿Estamos ejecutando el .exe compilado o el código fuente?
    if getattr(sys, 'frozen', False):
        # MODO PRODUCCIÓN (.exe)
        base_dir = os.path.dirname(sys.executable)
        # Asumimos que el sincronizador compilado se llamará Sincronizador.exe
        ruta_sincronizador = os.path.join(base_dir, "Sincronizador.exe")
        comando = f'"{ruta_sincronizador}"'
    else:
        # MODO DESARROLLO (.py)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_sincronizador = os.path.join(base_dir, "utilidades", "sincronizador.py")
        ruta_python = sys.executable.replace("python.exe", "pythonw.exe")
        comando = f'"{ruta_python}" "{ruta_sincronizador}"'

    if sistema == "Windows":
        try:
            import winreg
            llave_ruta = r"Software\Microsoft\Windows\CurrentVersion\Run"
            nombre_tarea = "ProElectroSincronizador"
            
            # Abrimos el registro y guardamos la instrucción
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, llave_ruta, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, nombre_tarea, 0, winreg.REG_SZ, comando)
            winreg.CloseKey(key)
            print("✅ Sincronizador registrado en el inicio de Windows.")
        except Exception as e:
            print(f"❌ Error al registrar en Windows: {e}")

    elif sistema == "Linux":
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            
            desktop_file_path = os.path.join(autostart_dir, "proelectro_sync.desktop")
            contenido = f"""[Desktop Entry]
Type=Application
Exec={comando}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=ProElectro Sincronizador
Comment=Sincroniza datos en segundo plano
"""
            with open(desktop_file_path, "w", encoding="utf-8") as f:
                f.write(contenido)
            print("✅ Sincronizador registrado en el inicio de Linux.")
        except Exception as e:
            print(f"❌ Error al registrar en Linux: {e}")