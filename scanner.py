"""
Módulo de escaneo de archivos para BigBackups
Recorre directorios y cataloga archivos en la base de datos
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, Generator, Tuple, List
from concurrent.futures import ThreadPoolExecutor
import threading

from config import FileStatus, SessionStatus
from database import Database, get_database
from utils import (
    is_file_excluded,
    is_folder_excluded,
    is_onedrive_cloud_file,
    get_file_info,
    format_datetime,
    ensure_long_path,
    get_relative_path
)


class ScannerStats:
    """Estadísticas del escaneo en tiempo real."""
    
    def __init__(self):
        self.archivos_encontrados = 0
        self.carpetas_encontradas = 0
        self.tamano_total = 0
        self.archivos_nube = 0
        self.archivos_excluidos = 0
        self.carpetas_excluidas = 0
        self.errores = 0
        self.carpeta_actual = ""
        self._lock = threading.Lock()
    
    def incrementar_archivos(self, tamano: int = 0, es_nube: bool = False):
        with self._lock:
            self.archivos_encontrados += 1
            self.tamano_total += tamano
            if es_nube:
                self.archivos_nube += 1
    
    def incrementar_carpetas(self):
        with self._lock:
            self.carpetas_encontradas += 1
    
    def incrementar_excluidos(self, es_carpeta: bool = False):
        with self._lock:
            if es_carpeta:
                self.carpetas_excluidas += 1
            else:
                self.archivos_excluidos += 1
    
    def incrementar_errores(self):
        with self._lock:
            self.errores += 1
    
    def set_carpeta_actual(self, carpeta: str):
        with self._lock:
            self.carpeta_actual = carpeta
    
    def get_stats(self) -> dict:
        with self._lock:
            return {
                'archivos': self.archivos_encontrados,
                'carpetas': self.carpetas_encontradas,
                'tamano': self.tamano_total,
                'nube': self.archivos_nube,
                'excluidos_archivos': self.archivos_excluidos,
                'excluidos_carpetas': self.carpetas_excluidas,
                'errores': self.errores,
                'carpeta_actual': self.carpeta_actual
            }


class FileScanner:
    """
    Escáner de archivos que cataloga directorios completos.
    """
    
    def __init__(self, db: Database = None):
        """
        Inicializa el escáner.
        
        Args:
            db: Instancia de base de datos (opcional)
        """
        self.db = db or get_database()
        self.stats = ScannerStats()
        self._cancelado = False
        self._pausado = False
        self._lock = threading.Lock()
        
        # Callbacks para actualizar UI
        self.on_progress: Optional[Callable[[ScannerStats], None]] = None
        self.on_file_found: Optional[Callable[[str, int], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        self.on_complete: Optional[Callable[[ScannerStats], None]] = None
    
    def cancelar(self):
        """Cancela el escaneo."""
        with self._lock:
            self._cancelado = True
    
    def pausar(self):
        """Pausa el escaneo."""
        with self._lock:
            self._pausado = True
    
    def reanudar(self):
        """Reanuda el escaneo."""
        with self._lock:
            self._pausado = False
    
    def _is_cancelado(self) -> bool:
        with self._lock:
            return self._cancelado
    
    def _is_pausado(self) -> bool:
        with self._lock:
            return self._pausado
    
    def _esperar_si_pausado(self):
        """Espera si el escaneo está pausado."""
        while self._is_pausado() and not self._is_cancelado():
            import time
            time.sleep(0.1)
    
    def escanear(self, sesion_id: int, ruta_origen: str, 
                 batch_size: int = 500) -> ScannerStats:
        """
        Escanea un directorio completo y cataloga en la base de datos.
        
        Args:
            sesion_id: ID de la sesión de backup
            ruta_origen: Ruta del directorio a escanear
            batch_size: Tamaño del batch para inserciones
        
        Returns:
            Estadísticas del escaneo
        """
        self.stats = ScannerStats()
        self._cancelado = False
        self._pausado = False
        
        ruta_origen = os.path.abspath(ruta_origen)
        ruta_origen_long = ensure_long_path(ruta_origen)
        
        # Actualizar estado de sesión
        self.db.actualizar_sesion(
            sesion_id,
            estado=SessionStatus.SCANNING,
            fecha_inicio_escaneo=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        self.db.log(sesion_id, "INFO", f"Iniciando escaneo de: {ruta_origen}", "SCANNER")
        
        # Buffers para batch insert
        archivos_batch = []
        carpetas_batch = []
        
        try:
            for root, dirs, files in os.walk(ruta_origen_long):
                if self._is_cancelado():
                    self.db.log(sesion_id, "WARNING", "Escaneo cancelado por el usuario", "SCANNER")
                    break
                
                self._esperar_si_pausado()
                
                # Convertir ruta larga a normal para mostrar
                root_display = root.replace('\\\\?\\', '').replace('\\\\?\\UNC\\', '\\\\')
                self.stats.set_carpeta_actual(root_display)
                
                # Filtrar carpetas excluidas
                dirs_filtrados = []
                for d in dirs:
                    if is_folder_excluded(d):
                        self.stats.incrementar_excluidos(es_carpeta=True)
                        self.db.log(sesion_id, "DEBUG", f"Carpeta excluida: {d}", "SCANNER", root_display)
                    else:
                        dirs_filtrados.append(d)
                dirs[:] = dirs_filtrados  # Modifica in-place para os.walk
                
                # Registrar carpeta actual
                ruta_relativa = get_relative_path(root_display, ruta_origen)
                if ruta_relativa and ruta_relativa != '.':
                    nombre_carpeta = os.path.basename(root_display)
                    carpetas_batch.append((sesion_id, root_display, ruta_relativa, nombre_carpeta))
                    self.stats.incrementar_carpetas()
                
                # Procesar archivos
                for filename in files:
                    if self._is_cancelado():
                        break
                    
                    self._esperar_si_pausado()
                    
                    # Verificar exclusión
                    if is_file_excluded(filename):
                        self.stats.incrementar_excluidos(es_carpeta=False)
                        continue
                    
                    try:
                        file_path = os.path.join(root, filename)
                        file_path_display = file_path.replace('\\\\?\\', '').replace('\\\\?\\UNC\\', '\\\\')
                        
                        # Obtener información del archivo
                        tamano, fecha_mod, _ = get_file_info(file_path)
                        
                        # Detectar si es archivo solo en nube
                        es_nube = is_onedrive_cloud_file(file_path_display)
                        
                        # Preparar datos para batch
                        ruta_rel = get_relative_path(file_path_display, ruta_origen)
                        extension = os.path.splitext(filename)[1].lower()
                        
                        archivos_batch.append((
                            sesion_id,
                            file_path_display,
                            ruta_rel,
                            filename,
                            extension,
                            tamano,
                            format_datetime(fecha_mod),
                            int(es_nube)
                        ))
                        
                        self.stats.incrementar_archivos(tamano, es_nube)
                        
                        # Notificar progreso
                        if self.on_file_found:
                            self.on_file_found(file_path_display, tamano)
                        
                    except PermissionError as e:
                        self.stats.incrementar_errores()
                        self.db.log(sesion_id, "ERROR", f"Sin permisos: {filename}", "SCANNER", str(e))
                        if self.on_error:
                            self.on_error(filename, f"Sin permisos: {e}")
                    
                    except Exception as e:
                        self.stats.incrementar_errores()
                        self.db.log(sesion_id, "ERROR", f"Error escaneando: {filename}", "SCANNER", str(e))
                        if self.on_error:
                            self.on_error(filename, str(e))
                
                # Flush batches si alcanzan el tamaño
                if len(archivos_batch) >= batch_size:
                    self.db.insertar_archivos_batch(archivos_batch)
                    archivos_batch = []
                
                if len(carpetas_batch) >= batch_size:
                    self.db.insertar_carpetas_batch(carpetas_batch)
                    carpetas_batch = []
                
                # Notificar progreso general
                if self.on_progress:
                    self.on_progress(self.stats)
            
            # Flush remaining batches
            if archivos_batch:
                self.db.insertar_archivos_batch(archivos_batch)
            if carpetas_batch:
                self.db.insertar_carpetas_batch(carpetas_batch)
            
            # Actualizar estadísticas de sesión
            stats = self.stats.get_stats()
            self.db.actualizar_sesion(
                sesion_id,
                estado=SessionStatus.READY if not self._is_cancelado() else SessionStatus.PAUSED,
                total_archivos=stats['archivos'],
                total_carpetas=stats['carpetas'],
                total_bytes=stats['tamano'],
                fecha_fin_escaneo=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            self.db.log(
                sesion_id, 
                "INFO", 
                f"Escaneo completado: {stats['archivos']} archivos, {stats['carpetas']} carpetas",
                "SCANNER",
                f"Tamaño total: {stats['tamano']} bytes, En nube: {stats['nube']}, Errores: {stats['errores']}"
            )
            
        except Exception as e:
            self.db.log(sesion_id, "ERROR", f"Error fatal en escaneo: {str(e)}", "SCANNER")
            self.db.actualizar_sesion(sesion_id, estado=SessionStatus.ERROR)
            raise
        
        if self.on_complete:
            self.on_complete(self.stats)
        
        return self.stats
    
    def escaneo_rapido(self, ruta_origen: str) -> Tuple[int, int, int]:
        """
        Realiza un conteo rápido sin guardar en DB (para estimaciones).
        
        Args:
            ruta_origen: Ruta a escanear
        
        Returns:
            Tupla (num_archivos, num_carpetas, tamano_total)
        """
        num_archivos = 0
        num_carpetas = 0
        tamano_total = 0
        
        ruta_origen = ensure_long_path(os.path.abspath(ruta_origen))
        
        try:
            for root, dirs, files in os.walk(ruta_origen):
                if self._is_cancelado():
                    break
                
                # Filtrar excluidos
                dirs[:] = [d for d in dirs if not is_folder_excluded(d)]
                num_carpetas += len(dirs)
                
                for filename in files:
                    if not is_file_excluded(filename):
                        try:
                            file_path = os.path.join(root, filename)
                            tamano, _, _ = get_file_info(file_path)
                            num_archivos += 1
                            tamano_total += tamano
                        except:
                            pass
        except:
            pass
        
        return num_archivos, num_carpetas, tamano_total


def escanear_directorio(sesion_id: int, ruta_origen: str,
                        on_progress: Callable = None,
                        on_error: Callable = None,
                        on_complete: Callable = None) -> ScannerStats:
    """
    Función de conveniencia para escanear un directorio.
    
    Args:
        sesion_id: ID de la sesión
        ruta_origen: Ruta a escanear
        on_progress: Callback de progreso
        on_error: Callback de error
        on_complete: Callback de completado
    
    Returns:
        Estadísticas del escaneo
    """
    scanner = FileScanner()
    scanner.on_progress = on_progress
    scanner.on_error = on_error
    scanner.on_complete = on_complete
    return scanner.escanear(sesion_id, ruta_origen)
