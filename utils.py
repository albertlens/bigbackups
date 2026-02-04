"""
Utilidades para BigBackups
"""

import hashlib
import os
import ctypes
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import fnmatch

from config import (
    HASH_ALGORITHM, 
    HASH_CHUNK_SIZE, 
    EXCLUDED_FILES, 
    EXCLUDED_FOLDERS
)


def calculate_hash(file_path: str, algorithm: str = HASH_ALGORITHM) -> Optional[str]:
    """
    Calcula el hash de un archivo.
    
    Args:
        file_path: Ruta completa del archivo
        algorithm: Algoritmo de hash ('md5' o 'sha256')
    
    Returns:
        Hash en formato hexadecimal o None si hay error
    """
    try:
        if algorithm == "md5":
            hasher = hashlib.md5()
        else:
            hasher = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(HASH_CHUNK_SIZE):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except Exception as e:
        return None


def format_size(size_bytes: int) -> str:
    """
    Formatea un tamaño en bytes a formato legible.
    
    Args:
        size_bytes: Tamaño en bytes
    
    Returns:
        Cadena formateada (ej: "1.5 GB")
    """
    if size_bytes < 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.2f} PB"


def format_time(seconds: float) -> str:
    """
    Formatea segundos a formato legible.
    
    Args:
        seconds: Tiempo en segundos
    
    Returns:
        Cadena formateada (ej: "2h 15m 30s")
    """
    if seconds < 0:
        return "0s"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def format_datetime(dt: datetime) -> str:
    """Formatea un datetime a cadena legible."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parsea una cadena de fecha a datetime."""
    try:
        return datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
    except:
        return None


def get_file_info(file_path: str) -> Tuple[int, datetime, bool]:
    """
    Obtiene información de un archivo.
    
    Args:
        file_path: Ruta del archivo
    
    Returns:
        Tupla (tamaño_bytes, fecha_modificación, es_solo_lectura)
    """
    try:
        stat = os.stat(file_path)
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)
        readonly = not os.access(file_path, os.W_OK)
        return size, mtime, readonly
    except Exception as e:
        return 0, datetime.now(), False


def is_file_excluded(filename: str) -> bool:
    """
    Verifica si un archivo debe ser excluido.
    
    Args:
        filename: Nombre del archivo
    
    Returns:
        True si debe excluirse
    """
    lower_name = filename.lower()
    
    for pattern in EXCLUDED_FILES:
        if fnmatch.fnmatch(lower_name, pattern.lower()):
            return True
    
    return False


def is_folder_excluded(folder_name: str) -> bool:
    """
    Verifica si una carpeta debe ser excluida.
    
    Args:
        folder_name: Nombre de la carpeta
    
    Returns:
        True si debe excluirse
    """
    return folder_name.lower() in EXCLUDED_FOLDERS


def is_onedrive_cloud_file(file_path: str) -> bool:
    """
    Detecta si un archivo de OneDrive está solo en la nube (no descargado).
    
    Args:
        file_path: Ruta del archivo
    
    Returns:
        True si el archivo está solo en la nube (placeholder sin contenido local)
    """
    try:
        # Primero verificar si la ruta está dentro de OneDrive
        onedrive_paths = [
            os.environ.get('OneDrive', ''),
            os.environ.get('OneDriveConsumer', ''),
            os.environ.get('OneDriveCommercial', ''),
        ]
        
        file_path_lower = file_path.lower()
        is_in_onedrive = any(
            od_path and file_path_lower.startswith(od_path.lower()) 
            for od_path in onedrive_paths if od_path
        )
        
        # Si no está en OneDrive, no es un archivo cloud de OneDrive
        if not is_in_onedrive:
            return False
        
        # Atributo de Windows para archivos "recall on data access" (solo en nube)
        FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
        # Atributo para archivos sparse (parcialmente en nube)
        FILE_ATTRIBUTE_SPARSE_FILE = 0x00000200
        # Atributo pinned/unpinned de OneDrive
        FILE_ATTRIBUTE_PINNED = 0x00080000
        FILE_ATTRIBUTE_UNPINNED = 0x00100000
        
        attrs = ctypes.windll.kernel32.GetFileAttributesW(file_path)
        
        if attrs == -1:
            return False
        
        # Solo marcar como "solo en nube" si tiene RECALL_ON_DATA_ACCESS
        # Este atributo indica que el archivo debe descargarse al acceder
        is_cloud_only = bool(attrs & FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS)
        
        return is_cloud_only
    except:
        return False


def get_drive_space(path: str) -> Tuple[int, int, int]:
    """
    Obtiene el espacio del disco.
    
    Args:
        path: Ruta en el disco
    
    Returns:
        Tupla (total, usado, libre) en bytes
    """
    try:
        if os.name == 'nt':
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(path),
                None,
                ctypes.pointer(total_bytes),
                ctypes.pointer(free_bytes)
            )
            total = total_bytes.value
            free = free_bytes.value
            used = total - free
            return total, used, free
        else:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            return total, used, free
    except:
        return 0, 0, 0


def sanitize_path(path: str) -> str:
    """
    Sanitiza una ruta para evitar problemas.
    
    Args:
        path: Ruta original
    
    Returns:
        Ruta sanitizada
    """
    # Normalizar separadores
    path = path.replace('/', '\\')
    
    # Eliminar espacios al inicio y final
    path = path.strip()
    
    # Eliminar comillas si las hay
    path = path.strip('"').strip("'")
    
    return path


def ensure_long_path(path: str) -> str:
    """
    Convierte una ruta a formato largo de Windows para evitar límite de 260 caracteres.
    
    Args:
        path: Ruta original
    
    Returns:
        Ruta en formato largo
    """
    if os.name == 'nt' and not path.startswith('\\\\?\\'):
        # Convertir a ruta absoluta primero
        abs_path = os.path.abspath(path)
        if abs_path.startswith('\\\\'):
            # Ruta UNC (red)
            return '\\\\?\\UNC\\' + abs_path[2:]
        else:
            return '\\\\?\\' + abs_path
    return path


def get_relative_path(file_path: str, base_path: str) -> str:
    """
    Obtiene la ruta relativa de un archivo respecto a una ruta base.
    
    Args:
        file_path: Ruta completa del archivo
        base_path: Ruta base
    
    Returns:
        Ruta relativa
    """
    try:
        return os.path.relpath(file_path, base_path)
    except ValueError:
        # Puede fallar si están en diferentes drives
        return file_path


def create_log_entry(level: str, message: str, details: str = "") -> str:
    """
    Crea una entrada de log formateada.
    
    Args:
        level: Nivel (INFO, WARNING, ERROR)
        message: Mensaje principal
        details: Detalles adicionales
    
    Returns:
        Entrada de log formateada
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    if details:
        entry += f" | {details}"
    return entry
