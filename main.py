"""
BigBackups - Aplicación de copia segura de grandes volúmenes de datos
Punto de entrada principal

Uso:
    python main.py          # Inicia la GUI
    python main.py --cli    # Modo consola (futuro)
"""

import sys
import os

# Asegurar que el directorio actual está en el path
if getattr(sys, 'frozen', False):
    # Ejecutando como EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Ejecutando como script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)


def main():
    """Función principal de la aplicación."""
    
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print("""
BigBackups - Copia segura de grandes volúmenes de datos
=========================================================

Uso:
    BigBackups.exe              Inicia la interfaz gráfica
    BigBackups.exe --version    Muestra la versión
    BigBackups.exe --help       Muestra esta ayuda

Características:
    - Escaneo y catalogación en SQLite
    - Copia con verificación SHA256
    - Soporte para rutas largas de Windows
    - Detección de archivos OneDrive en la nube
    - Sistema de reintentos con backoff exponencial
    - Reanudación de copias interrumpidas
    - Log detallado de todas las operaciones
            """)
            return 0
        
        if sys.argv[1] in ['--version', '-v']:
            from config import APP_NAME, APP_VERSION
            print(f"{APP_NAME} v{APP_VERSION}")
            return 0
    
    # Iniciar GUI
    try:
        from gui import BigBackupsApp
        
        app = BigBackupsApp()
        app.mainloop()
        
        return 0
        
    except ImportError as e:
        print(f"Error: No se pudo importar módulos necesarios: {e}")
        print("Asegúrate de tener instaladas las dependencias:")
        print("  pip install customtkinter pillow")
        return 1
    
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
