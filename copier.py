"""
Módulo de copia de archivos para BigBackups
Copia archivos con verificación SHA256 y sistema de reintentos
"""

import os
import shutil
import time
import threading
from collections import deque
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass, field

# Tamaño de la ventana para media móvil (en segundos/muestras)
MEDIA_MOVIL_VENTANA = 15

from config import (
    FileStatus, 
    SessionStatus, 
    COPY_BUFFER_SIZE, 
    MAX_RETRIES, 
    RETRY_DELAY_BASE,
    HASH_ALGORITHM
)
from database import Database, get_database
from utils import (
    calculate_hash,
    ensure_long_path,
    format_size,
    format_time,
    get_drive_space
)


@dataclass
class CopyStats:
    """Estadísticas de la copia en tiempo real."""
    total_archivos: int = 0
    total_bytes: int = 0
    archivos_copiados: int = 0
    bytes_copiados: int = 0
    archivos_verificados: int = 0
    archivos_error: int = 0
    archivos_omitidos: int = 0
    archivo_actual: str = ""
    velocidad_bytes_seg: float = 0.0
    velocidad_archivos_seg: float = 0.0
    tiempo_transcurrido: float = 0.0
    tiempo_estimado_restante: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    @property
    def porcentaje(self) -> float:
        if self.total_archivos == 0:
            return 0.0
        return (self.archivos_copiados / self.total_archivos) * 100
    
    @property
    def porcentaje_bytes(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_copiados / self.total_bytes) * 100
    
    @property
    def archivos_restantes(self) -> int:
        return self.total_archivos - self.archivos_copiados - self.archivos_error - self.archivos_omitidos
    
    def get_stats_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_archivos': self.total_archivos,
                'total_bytes': self.total_bytes,
                'archivos_copiados': self.archivos_copiados,
                'bytes_copiados': self.bytes_copiados,
                'archivos_verificados': self.archivos_verificados,
                'archivos_error': self.archivos_error,
                'archivos_omitidos': self.archivos_omitidos,
                'archivo_actual': self.archivo_actual,
                'velocidad': self.velocidad_bytes_seg,
                'velocidad_archivos': self.velocidad_archivos_seg,
                'tiempo_transcurrido': self.tiempo_transcurrido,
                'tiempo_restante': self.tiempo_estimado_restante,
                'porcentaje': self.porcentaje,
                'porcentaje_bytes': self.porcentaje_bytes,
                'archivos_restantes': self.archivos_restantes
            }


class FileCopier:
    """
    Copiador de archivos con verificación y reintentos.
    """
    
    def __init__(self, db: Database = None):
        """
        Inicializa el copiador.
        
        Args:
            db: Instancia de base de datos (opcional)
        """
        self.db = db or get_database()
        self.stats = CopyStats()
        self._cancelado = False
        self._pausado = False
        self._lock = threading.Lock()
        
        # Callbacks
        self.on_progress: Optional[Callable[[CopyStats], None]] = None
        self.on_file_start: Optional[Callable[[str, int], None]] = None
        self.on_file_complete: Optional[Callable[[str, bool], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        self.on_complete: Optional[Callable[[CopyStats], None]] = None
    
    def cancelar(self):
        """Cancela la copia."""
        with self._lock:
            self._cancelado = True
    
    def pausar(self):
        """Pausa la copia."""
        with self._lock:
            self._pausado = True
    
    def reanudar(self):
        """Reanuda la copia."""
        with self._lock:
            self._pausado = False
    
    def _is_cancelado(self) -> bool:
        with self._lock:
            return self._cancelado
    
    def _is_pausado(self) -> bool:
        with self._lock:
            return self._pausado
    
    def _esperar_si_pausado(self):
        """Espera si la copia está pausada."""
        while self._is_pausado() and not self._is_cancelado():
            time.sleep(0.1)
    
    def _copiar_archivo_con_hash(self, origen: str, destino: str) -> tuple[bool, str, str]:
        """
        Copia un archivo calculando hash durante la lectura.
        
        Args:
            origen: Ruta del archivo origen
            destino: Ruta del archivo destino
        
        Returns:
            Tupla (exito, hash_origen, mensaje_error)
        """
        import hashlib
        
        hasher = hashlib.sha256() if HASH_ALGORITHM == 'sha256' else hashlib.md5()
        
        try:
            # Asegurar que el directorio destino existe
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            
            # Copiar con cálculo de hash simultáneo
            with open(origen, 'rb') as src:
                with open(destino, 'wb') as dst:
                    while True:
                        if self._is_cancelado():
                            return False, "", "Cancelado por usuario"
                        
                        self._esperar_si_pausado()
                        
                        chunk = src.read(COPY_BUFFER_SIZE)
                        if not chunk:
                            break
                        
                        hasher.update(chunk)
                        dst.write(chunk)
            
            # Copiar metadatos (fechas)
            shutil.copystat(origen, destino)
            
            return True, hasher.hexdigest(), ""
            
        except PermissionError as e:
            return False, "", f"Sin permisos: {e}"
        except FileNotFoundError as e:
            return False, "", f"Archivo no encontrado: {e}"
        except OSError as e:
            # Puede ser espacio insuficiente, ruta muy larga, etc.
            return False, "", f"Error de sistema: {e}"
        except Exception as e:
            return False, "", str(e)
    
    def _verificar_hash(self, archivo: str, hash_esperado: str) -> tuple[bool, str]:
        """
        Verifica el hash de un archivo copiado.
        
        Args:
            archivo: Ruta del archivo a verificar
            hash_esperado: Hash esperado
        
        Returns:
            Tupla (coincide, hash_calculado)
        """
        hash_calculado = calculate_hash(archivo)
        if hash_calculado is None:
            return False, ""
        return hash_calculado == hash_esperado, hash_calculado
    
    def _copiar_con_reintentos(self, archivo_info: Dict[str, Any], 
                                ruta_destino_base: str) -> tuple[bool, str]:
        """
        Intenta copiar un archivo con reintentos exponenciales.
        
        Args:
            archivo_info: Información del archivo de la DB
            ruta_destino_base: Ruta base del destino
        
        Returns:
            Tupla (exito, mensaje_error)
        """
        archivo_id = archivo_info['id']
        ruta_origen = archivo_info['ruta_origen']
        ruta_relativa = archivo_info['ruta_relativa']
        tamano = archivo_info['tamano_bytes']
        
        # Construir ruta destino
        ruta_destino = os.path.join(ruta_destino_base, ruta_relativa)
        ruta_origen_long = ensure_long_path(ruta_origen)
        ruta_destino_long = ensure_long_path(ruta_destino)
        
        intentos = archivo_info.get('intentos', 0)
        max_intentos = MAX_RETRIES - intentos  # Reintentos restantes
        
        for intento in range(max_intentos):
            if self._is_cancelado():
                return False, "Cancelado por usuario"
            
            self._esperar_si_pausado()
            
            # Notificar inicio
            if self.on_file_start:
                self.on_file_start(ruta_origen, tamano)
            
            with self.stats._lock:
                self.stats.archivo_actual = ruta_origen
            
            # Actualizar estado a COPIANDO
            self.db.actualizar_archivo(archivo_id, estado=FileStatus.COPYING)
            
            # Intentar copiar
            exito, hash_origen, error = self._copiar_archivo_con_hash(
                ruta_origen_long, 
                ruta_destino_long
            )
            
            if not exito:
                if intento < max_intentos - 1:
                    # Esperar antes de reintentar (backoff exponencial)
                    delay = RETRY_DELAY_BASE * (2 ** intento)
                    self.db.log(
                        archivo_info['sesion_id'],
                        "WARNING",
                        f"Reintento {intento + 1}/{max_intentos}: {ruta_relativa}",
                        "COPIER",
                        f"Error: {error}. Esperando {delay}s"
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Se agotaron los reintentos
                    self.db.marcar_archivo_error(archivo_id, error)
                    return False, error
            
            # Verificar hash del archivo copiado
            self.db.actualizar_archivo(archivo_id, estado=FileStatus.VERIFYING)
            
            hash_coincide, hash_destino = self._verificar_hash(ruta_destino_long, hash_origen)
            
            if hash_coincide:
                # Éxito total
                self.db.marcar_archivo_verificado(archivo_id, hash_destino, True)
                self.db.actualizar_archivo(
                    archivo_id,
                    ruta_destino=ruta_destino,
                    hash_origen=hash_origen
                )
                return True, ""
            else:
                # Hash no coincide - eliminar archivo corrupto y reintentar
                try:
                    os.remove(ruta_destino_long)
                except:
                    pass
                
                if intento < max_intentos - 1:
                    self.db.log(
                        archivo_info['sesion_id'],
                        "WARNING",
                        f"Hash no coincide, reintentando: {ruta_relativa}",
                        "COPIER",
                        f"Origen: {hash_origen}, Destino: {hash_destino}"
                    )
                    continue
                else:
                    error_msg = f"Hash no coincide después de {max_intentos} intentos"
                    self.db.marcar_archivo_verificado(archivo_id, hash_destino, False, error_msg)
                    return False, error_msg
        
        return False, "Se agotaron los reintentos"
    
    def verificar_espacio_destino(self, sesion_id: int, ruta_destino: str) -> tuple[bool, str]:
        """
        Verifica si hay suficiente espacio en el destino.
        
        Args:
            sesion_id: ID de la sesión
            ruta_destino: Ruta del destino
        
        Returns:
            Tupla (hay_espacio, mensaje)
        """
        stats = self.db.obtener_estadisticas_sesion(sesion_id)
        bytes_necesarios = stats['tamano_total'] - stats.get('bytes_copiados', 0)
        
        # Agregar 5% de margen
        bytes_necesarios = int(bytes_necesarios * 1.05)
        
        total, usado, libre = get_drive_space(ruta_destino)
        
        if libre < bytes_necesarios:
            return False, (
                f"Espacio insuficiente en destino.\n"
                f"Necesario: {format_size(bytes_necesarios)}\n"
                f"Disponible: {format_size(libre)}"
            )
        
        return True, f"Espacio disponible: {format_size(libre)}"
    
    def crear_estructura_carpetas(self, sesion_id: int, ruta_destino: str) -> int:
        """
        Crea toda la estructura de carpetas en el destino.
        
        Args:
            sesion_id: ID de la sesión
            ruta_destino: Ruta base del destino
        
        Returns:
            Número de carpetas creadas
        """
        carpetas = self.db.obtener_carpetas(sesion_id)
        creadas = 0
        
        for carpeta in carpetas:
            if self._is_cancelado():
                break
            
            ruta_carpeta_destino = os.path.join(ruta_destino, carpeta['ruta_relativa'])
            ruta_carpeta_long = ensure_long_path(ruta_carpeta_destino)
            
            try:
                os.makedirs(ruta_carpeta_long, exist_ok=True)
                self.db.marcar_carpeta_creada(carpeta['id'], ruta_carpeta_destino)
                creadas += 1
            except Exception as e:
                self.db.log(
                    sesion_id,
                    "ERROR",
                    f"Error creando carpeta: {carpeta['ruta_relativa']}",
                    "COPIER",
                    str(e)
                )
        
        return creadas
    
    def copiar(self, sesion_id: int, ruta_destino: str, 
               batch_size: int = 100) -> CopyStats:
        """
        Ejecuta la copia completa de una sesión.
        
        Args:
            sesion_id: ID de la sesión
            ruta_destino: Ruta del directorio destino
            batch_size: Archivos a procesar por lote
        
        Returns:
            Estadísticas de la copia
        """
        self._cancelado = False
        self._pausado = False
        
        # Obtener información de la sesión
        sesion = self.db.obtener_sesion(sesion_id)
        if not sesion:
            raise ValueError(f"Sesión {sesion_id} no encontrada")
        
        # Crear carpeta raíz con el nombre del origen
        # Ej: Si origen es C:\Robust\Clientes, creamos destino\Clientes
        ruta_origen = sesion['ruta_origen']
        nombre_carpeta_origen = os.path.basename(ruta_origen.rstrip('/\\'))
        ruta_destino_final = os.path.join(ruta_destino, nombre_carpeta_origen)
        
        # Crear la carpeta raíz
        os.makedirs(ensure_long_path(ruta_destino_final), exist_ok=True)
        
        # Verificar espacio
        hay_espacio, mensaje = self.verificar_espacio_destino(sesion_id, ruta_destino)
        if not hay_espacio:
            self.db.log(sesion_id, "ERROR", mensaje, "COPIER")
            raise ValueError(mensaje)
        
        # Obtener estadísticas
        stats_db = self.db.obtener_estadisticas_sesion(sesion_id)
        
        # Inicializar estadísticas con los valores actuales (incluye progreso previo)
        self.stats = CopyStats(
            total_archivos=stats_db['total_archivos'],
            total_bytes=stats_db['tamano_total'],
            archivos_copiados=stats_db['completados'],
            bytes_copiados=stats_db['bytes_copiados']
        )
        
        # Actualizar estado de sesión (guardamos la ruta final con subcarpeta)
        # Solo establecer fecha_inicio_copia si es la primera vez
        update_fields = {
            'estado': SessionStatus.COPYING,
            'ruta_destino': ruta_destino_final
        }
        if not sesion.get('fecha_inicio_copia'):
            update_fields['fecha_inicio_copia'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.db.actualizar_sesion(sesion_id, **update_fields)
        
        self.db.log(sesion_id, "INFO", f"Iniciando copia a: {ruta_destino_final}", "COPIER")
        
        # Crear estructura de carpetas primero
        self.db.log(sesion_id, "INFO", "Creando estructura de carpetas...", "COPIER")
        carpetas_creadas = self.crear_estructura_carpetas(sesion_id, ruta_destino_final)
        self.db.log(sesion_id, "INFO", f"Carpetas creadas: {carpetas_creadas}", "COPIER")
        
        # Variables para cálculo de velocidad
        tiempo_inicio = time.time()
        bytes_inicio = self.stats.bytes_copiados
        archivos_inicio = self.stats.archivos_copiados
        ultimo_update = tiempo_inicio
        
        # Media móvil para tiempo estimado más preciso
        # Almacena tuplas (timestamp, bytes_copiados) de los últimos N segundos
        muestras_velocidad = deque(maxlen=MEDIA_MOVIL_VENTANA)
        ultimo_bytes = self.stats.bytes_copiados
        
        try:
            while True:
                if self._is_cancelado():
                    self.db.log(sesion_id, "WARNING", "Copia cancelada por el usuario", "COPIER")
                    self.db.actualizar_sesion(sesion_id, estado=SessionStatus.PAUSED)
                    break
                
                self._esperar_si_pausado()
                
                # Obtener siguiente lote de archivos pendientes
                archivos_pendientes = self.db.obtener_archivos_pendientes(sesion_id, batch_size)
                
                if not archivos_pendientes:
                    # No hay más archivos pendientes
                    break
                
                for archivo in archivos_pendientes:
                    if self._is_cancelado():
                        break
                    
                    self._esperar_si_pausado()
                    
                    # Verificar si es archivo solo en nube
                    if archivo.get('es_solo_nube'):
                        self.db.actualizar_archivo(
                            archivo['id'],
                            estado=FileStatus.SKIPPED,
                            error_mensaje="Archivo solo en la nube (no descargado)"
                        )
                        with self.stats._lock:
                            self.stats.archivos_omitidos += 1
                        continue
                    
                    # Copiar archivo
                    exito, error = self._copiar_con_reintentos(archivo, ruta_destino_final)
                    
                    with self.stats._lock:
                        if exito:
                            self.stats.archivos_copiados += 1
                            self.stats.bytes_copiados += archivo['tamano_bytes']
                            self.stats.archivos_verificados += 1
                        else:
                            self.stats.archivos_error += 1
                            if self.on_error:
                                self.on_error(archivo['ruta_origen'], error)
                    
                    # Notificar completado
                    if self.on_file_complete:
                        self.on_file_complete(archivo['ruta_origen'], exito)
                    
                    # Actualizar velocidad cada segundo
                    ahora = time.time()
                    if ahora - ultimo_update >= 1.0:
                        tiempo_transcurrido = ahora - tiempo_inicio
                        bytes_copiados_periodo = self.stats.bytes_copiados - bytes_inicio
                        archivos_copiados_periodo = self.stats.archivos_copiados - archivos_inicio
                        
                        # Añadir muestra para media móvil
                        bytes_este_segundo = self.stats.bytes_copiados - ultimo_bytes
                        muestras_velocidad.append((ahora, bytes_este_segundo))
                        ultimo_bytes = self.stats.bytes_copiados
                        
                        # Calcular velocidad media móvil (últimos N segundos)
                        if len(muestras_velocidad) >= 2:
                            bytes_ventana = sum(m[1] for m in muestras_velocidad)
                            tiempo_ventana = len(muestras_velocidad)  # Cada muestra es ~1 segundo
                            velocidad_media_movil = bytes_ventana / tiempo_ventana if tiempo_ventana > 0 else 0
                        else:
                            velocidad_media_movil = bytes_este_segundo
                        
                        with self.stats._lock:
                            self.stats.tiempo_transcurrido = tiempo_transcurrido
                            if tiempo_transcurrido > 0:
                                self.stats.velocidad_bytes_seg = bytes_copiados_periodo / tiempo_transcurrido
                                self.stats.velocidad_archivos_seg = archivos_copiados_periodo / tiempo_transcurrido
                            
                            # Estimar tiempo restante usando media móvil
                            bytes_restantes = self.stats.total_bytes - self.stats.bytes_copiados
                            if velocidad_media_movil > 0:
                                self.stats.tiempo_estimado_restante = bytes_restantes / velocidad_media_movil
                            elif self.stats.velocidad_bytes_seg > 0:
                                # Fallback al promedio total si no hay suficientes muestras
                                self.stats.tiempo_estimado_restante = bytes_restantes / self.stats.velocidad_bytes_seg
                        
                        ultimo_update = ahora
                    
                    # Notificar progreso
                    if self.on_progress:
                        self.on_progress(self.stats)
                
                # Actualizar estadísticas en sesión
                self.db.actualizar_sesion(
                    sesion_id,
                    archivos_copiados=self.stats.archivos_copiados,
                    bytes_copiados=self.stats.bytes_copiados,
                    archivos_error=self.stats.archivos_error,
                    archivos_omitidos=self.stats.archivos_omitidos
                )
            
            # Finalizar
            if not self._is_cancelado():
                estado_final = SessionStatus.COMPLETED if self.stats.archivos_error == 0 else SessionStatus.ERROR
                self.db.actualizar_sesion(
                    sesion_id,
                    estado=estado_final,
                    fecha_fin_copia=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                self.db.log(
                    sesion_id,
                    "INFO",
                    f"Copia finalizada: {self.stats.archivos_copiados}/{self.stats.total_archivos} archivos",
                    "COPIER",
                    f"Errores: {self.stats.archivos_error}, Omitidos: {self.stats.archivos_omitidos}"
                )
            
        except Exception as e:
            self.db.log(sesion_id, "ERROR", f"Error fatal en copia: {str(e)}", "COPIER")
            self.db.actualizar_sesion(sesion_id, estado=SessionStatus.ERROR)
            raise
        
        if self.on_complete:
            self.on_complete(self.stats)
        
        return self.stats
    
    def reintentar_errores(self, sesion_id: int) -> int:
        """
        Resetea archivos con error para reintentarlos.
        
        Returns:
            Número de archivos reseteados
        """
        return self.db.reintentar_errores(sesion_id)


def copiar_sesion(sesion_id: int, ruta_destino: str,
                  on_progress: Callable = None,
                  on_error: Callable = None,
                  on_complete: Callable = None) -> CopyStats:
    """
    Función de conveniencia para copiar una sesión.
    
    Args:
        sesion_id: ID de la sesión
        ruta_destino: Ruta destino
        on_progress: Callback de progreso
        on_error: Callback de error
        on_complete: Callback de completado
    
    Returns:
        Estadísticas de la copia
    """
    copier = FileCopier()
    copier.on_progress = on_progress
    copier.on_error = on_error
    copier.on_complete = on_complete
    return copier.copiar(sesion_id, ruta_destino)


@dataclass
class VerificationResult:
    """Resultado de la verificación post-copia."""
    total_archivos: int = 0
    archivos_verificados: int = 0
    archivos_ok: int = 0
    archivos_faltantes_destino: int = 0
    archivos_tamano_diferente: int = 0
    archivos_hash_diferente: int = 0
    archivos_faltantes_origen: int = 0
    errores: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def todo_ok(self) -> bool:
        return (self.archivos_faltantes_destino == 0 and 
                self.archivos_tamano_diferente == 0 and 
                self.archivos_hash_diferente == 0)
    
    def get_summary(self) -> str:
        if self.todo_ok:
            return f"✅ Verificación exitosa: {self.archivos_ok}/{self.total_archivos} archivos verificados correctamente"
        else:
            problemas = []
            if self.archivos_faltantes_destino > 0:
                problemas.append(f"{self.archivos_faltantes_destino} faltantes en destino")
            if self.archivos_tamano_diferente > 0:
                problemas.append(f"{self.archivos_tamano_diferente} con tamaño diferente")
            if self.archivos_hash_diferente > 0:
                problemas.append(f"{self.archivos_hash_diferente} con hash diferente")
            return f"⚠️ Problemas encontrados: {', '.join(problemas)}"


class PostCopyVerifier:
    """
    Verificador post-copia que compara origen y destino archivo por archivo.
    """
    
    def __init__(self, db: Database = None):
        self.db = db or get_database()
        self._cancelado = False
        self._pausado = False
        self._lock = threading.Lock()
        
        # Callbacks
        self.on_progress: Optional[Callable[[int, int, str], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        self.on_complete: Optional[Callable[[VerificationResult], None]] = None
    
    def cancelar(self):
        with self._lock:
            self._cancelado = True
    
    def pausar(self):
        with self._lock:
            self._pausado = True
    
    def reanudar(self):
        with self._lock:
            self._pausado = False
    
    def _is_cancelado(self) -> bool:
        with self._lock:
            return self._cancelado
    
    def _is_pausado(self) -> bool:
        with self._lock:
            return self._pausado
    
    def _esperar_si_pausado(self):
        while self._is_pausado() and not self._is_cancelado():
            time.sleep(0.1)
    
    def verificar_sesion(self, sesion_id: int, verificar_hash: bool = True) -> VerificationResult:
        """
        Verifica todos los archivos copiados de una sesión.
        
        Args:
            sesion_id: ID de la sesión a verificar
            verificar_hash: Si True, calcula y compara hashes SHA256 (más lento pero 100% seguro)
        
        Returns:
            VerificationResult con el resumen de la verificación
        """
        self._cancelado = False
        self._pausado = False
        
        result = VerificationResult()
        
        # Obtener sesión
        sesion = self.db.obtener_sesion(sesion_id)
        if not sesion:
            raise ValueError(f"Sesión {sesion_id} no encontrada")
        
        ruta_origen = sesion['ruta_origen']
        ruta_destino = sesion['ruta_destino']
        
        if not ruta_destino:
            raise ValueError("La sesión no tiene ruta de destino definida")
        
        self.db.log(sesion_id, "INFO", f"Iniciando verificación post-copia", "VERIFIER")
        self.db.log(sesion_id, "INFO", f"Origen: {ruta_origen}", "VERIFIER")
        self.db.log(sesion_id, "INFO", f"Destino: {ruta_destino}", "VERIFIER")
        self.db.log(sesion_id, "INFO", f"Verificación de hash: {'Sí' if verificar_hash else 'No'}", "VERIFIER")
        
        # Obtener todos los archivos completados de la sesión
        # Incluimos ruta_destino guardada en cada archivo para usar la ruta correcta
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ruta_origen, ruta_relativa, ruta_destino, nombre_archivo, tamano_bytes, hash_origen
                FROM archivos 
                WHERE sesion_id = ? AND estado = ?
            """, (sesion_id, FileStatus.COMPLETED))
            archivos = [dict(row) for row in cursor.fetchall()]
        
        result.total_archivos = len(archivos)
        
        for i, archivo in enumerate(archivos):
            if self._is_cancelado():
                self.db.log(sesion_id, "WARNING", "Verificación cancelada por el usuario", "VERIFIER")
                break
            
            self._esperar_si_pausado()
            
            ruta_origen_archivo = archivo['ruta_origen']
            ruta_relativa = archivo['ruta_relativa']
            
            # Usar la ruta de destino guardada en el archivo, o construirla si no existe
            if archivo.get('ruta_destino'):
                ruta_destino_archivo = archivo['ruta_destino']
            else:
                ruta_destino_archivo = os.path.join(ruta_destino, ruta_relativa)
            
            tamano_esperado = archivo['tamano_bytes']
            hash_esperado = archivo.get('hash_origen')
            
            # Notificar progreso
            if self.on_progress:
                self.on_progress(i + 1, result.total_archivos, archivo['nombre_archivo'])
            
            result.archivos_verificados += 1
            
            # 1. Verificar que existe en destino
            ruta_destino_long = ensure_long_path(ruta_destino_archivo)
            if not os.path.exists(ruta_destino_long):
                result.archivos_faltantes_destino += 1
                error_info = {
                    'archivo': ruta_relativa,
                    'tipo': 'FALTANTE_DESTINO',
                    'mensaje': 'Archivo no encontrado en destino'
                }
                result.errores.append(error_info)
                if self.on_error:
                    self.on_error(ruta_relativa, "No encontrado en destino")
                continue
            
            # 2. Verificar tamaño
            try:
                tamano_destino = os.path.getsize(ruta_destino_long)
                if tamano_destino != tamano_esperado:
                    result.archivos_tamano_diferente += 1
                    error_info = {
                        'archivo': ruta_relativa,
                        'tipo': 'TAMANO_DIFERENTE',
                        'mensaje': f'Tamaño origen: {tamano_esperado}, destino: {tamano_destino}'
                    }
                    result.errores.append(error_info)
                    if self.on_error:
                        self.on_error(ruta_relativa, f"Tamaño diferente: {tamano_esperado} vs {tamano_destino}")
                    continue
            except Exception as e:
                result.errores.append({
                    'archivo': ruta_relativa,
                    'tipo': 'ERROR_LECTURA',
                    'mensaje': str(e)
                })
                continue
            
            # 3. Verificar hash (si está habilitado)
            if verificar_hash:
                try:
                    hash_destino = calculate_hash(ruta_destino_long)
                    
                    if hash_esperado and hash_destino != hash_esperado:
                        result.archivos_hash_diferente += 1
                        error_info = {
                            'archivo': ruta_relativa,
                            'tipo': 'HASH_DIFERENTE',
                            'mensaje': f'Hash no coincide'
                        }
                        result.errores.append(error_info)
                        if self.on_error:
                            self.on_error(ruta_relativa, "Hash SHA256 no coincide")
                        continue
                except Exception as e:
                    result.errores.append({
                        'archivo': ruta_relativa,
                        'tipo': 'ERROR_HASH',
                        'mensaje': str(e)
                    })
                    continue
            
            # Todo OK
            result.archivos_ok += 1
        
        # Log final
        self.db.log(sesion_id, "INFO", result.get_summary(), "VERIFIER")
        
        if result.errores:
            for error in result.errores[:10]:  # Primeros 10 errores
                self.db.log(sesion_id, "WARNING", 
                           f"{error['tipo']}: {error['archivo']}", 
                           "VERIFIER", error['mensaje'])
        
        if self.on_complete:
            self.on_complete(result)
        
        return result
