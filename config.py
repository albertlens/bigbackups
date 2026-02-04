"""
Configuración global de la aplicación BigBackups
"""

import os
from pathlib import Path

# Información de la aplicación
APP_NAME = "BigBackups"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Tu Empresa"

# Configuración de base de datos
DB_NAME = "bigbackups.db"

# Configuración de hash
HASH_ALGORITHM = "sha256"  # Opciones: "md5", "sha256"
HASH_CHUNK_SIZE = 65536  # 64KB chunks para calcular hash

# Configuración de copia
COPY_BUFFER_SIZE = 1024 * 1024  # 1MB buffer para copia
MAX_RETRIES = 5
RETRY_DELAY_BASE = 2  # Segundos base para backoff exponencial

# Archivos y carpetas a excluir
EXCLUDED_FILES = {
    "thumbs.db",
    "desktop.ini",
    ".ds_store",
    "._.ds_store",
    "~$*",  # Archivos temporales de Office
}

EXCLUDED_FOLDERS = {
    "$recycle.bin",
    "system volume information",
    ".git",
    "__pycache__",
    "node_modules",
    ".vs",
    ".vscode",
}

# Estados de archivos
class FileStatus:
    PENDING = "PENDIENTE"
    SCANNING = "ESCANEANDO"
    COPYING = "COPIANDO"
    VERIFYING = "VERIFICANDO"
    COMPLETED = "COMPLETADO"
    ERROR = "ERROR"
    SKIPPED = "OMITIDO"

# Estados de sesión
class SessionStatus:
    CREATED = "CREADA"
    SCANNING = "ESCANEANDO"
    READY = "LISTA"
    COPYING = "COPIANDO"
    VERIFYING = "VERIFICANDO"
    COMPLETED = "COMPLETADA"
    PAUSED = "PAUSADA"
    ERROR = "ERROR"

# Colores para la GUI
class Colors:
    PRIMARY = "#1e88e5"
    SUCCESS = "#43a047"
    WARNING = "#fb8c00"
    ERROR = "#e53935"
    BACKGROUND = "#1a1a2e"
    SURFACE = "#16213e"
    TEXT = "#ffffff"
    TEXT_SECONDARY = "#b0b0b0"

# Obtener ruta de la aplicación (compatible con PyInstaller)
def get_app_path():
    """Retorna la ruta base de la aplicación."""
    if getattr(os.sys, 'frozen', False):
        # Ejecutando como EXE
        return Path(os.sys.executable).parent
    else:
        # Ejecutando como script
        return Path(__file__).parent

def get_db_path():
    """Retorna la ruta completa de la base de datos."""
    return get_app_path() / DB_NAME
