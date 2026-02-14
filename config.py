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

# Colores para la GUI (tema oscuro con tonos índigo/azul)
class Colors:
    # Colores principales
    PRIMARY = "#4f46e5"        # Índigo principal (botón escanear)
    PRIMARY_HOVER = "#4338ca"  # Índigo oscuro hover
    SECONDARY = "#6366f1"      # Índigo claro (botón copiar)
    SECONDARY_HOVER = "#4f46e5"
    ACCENT = "#818cf8"         # Índigo suave (verificar)
    ACCENT_HOVER = "#6366f1"
    
    # Colores de acción
    ACTION_PAUSE = "#64748b"   # Slate (pausar) - neutral
    ACTION_PAUSE_HOVER = "#475569"
    ACTION_CANCEL = "#94a3b8"  # Slate claro (cancelar)
    ACTION_CANCEL_HOVER = "#64748b"
    
    # Colores de estado (más sutiles)
    SUCCESS = "#22c55e"        # Verde para mensajes OK
    WARNING = "#f59e0b"        # Ámbar para warnings
    ERROR = "#ef4444"          # Rojo para errores (solo texto/log)
    
    # Colores de fondo
    BACKGROUND = "#0f172a"     # Slate 900 - muy oscuro
    SURFACE = "#1e293b"        # Slate 800
    SURFACE_LIGHT = "#334155"  # Slate 700
    
    # Colores de texto
    TEXT = "#f8fafc"           # Slate 50 - casi blanco
    TEXT_SECONDARY = "#94a3b8" # Slate 400

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
