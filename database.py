"""
Módulo de base de datos para BigBackups
Gestiona SQLite para catalogar archivos y sesiones de backup
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from contextlib import contextmanager
from pathlib import Path

from config import get_db_path, FileStatus, SessionStatus


class Database:
    """Gestiona la base de datos SQLite de BigBackups."""
    
    def __init__(self, db_path: str = None):
        """
        Inicializa la conexión a la base de datos.
        
        Args:
            db_path: Ruta de la base de datos (opcional)
        """
        self.db_path = db_path or str(get_db_path())
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones a la base de datos."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging para mejor rendimiento
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Crea las tablas si no existen."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de sesiones de backup
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sesiones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    ruta_origen TEXT NOT NULL,
                    ruta_destino TEXT NOT NULL,
                    estado TEXT DEFAULT 'CREADA',
                    total_archivos INTEGER DEFAULT 0,
                    total_carpetas INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    archivos_copiados INTEGER DEFAULT 0,
                    bytes_copiados INTEGER DEFAULT 0,
                    archivos_error INTEGER DEFAULT 0,
                    archivos_omitidos INTEGER DEFAULT 0,
                    fecha_creacion TEXT,
                    fecha_inicio_escaneo TEXT,
                    fecha_fin_escaneo TEXT,
                    fecha_inicio_copia TEXT,
                    fecha_fin_copia TEXT,
                    fecha_ultima_actividad TEXT,
                    notas TEXT
                )
            """)
            
            # Tabla de archivos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archivos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id INTEGER NOT NULL,
                    ruta_origen TEXT NOT NULL,
                    ruta_destino TEXT,
                    ruta_relativa TEXT NOT NULL,
                    nombre_archivo TEXT NOT NULL,
                    extension TEXT,
                    tamano_bytes INTEGER DEFAULT 0,
                    fecha_modificacion TEXT,
                    hash_origen TEXT,
                    hash_destino TEXT,
                    estado TEXT DEFAULT 'PENDIENTE',
                    es_solo_nube INTEGER DEFAULT 0,
                    intentos INTEGER DEFAULT 0,
                    error_mensaje TEXT,
                    fecha_copiado TEXT,
                    fecha_verificado TEXT,
                    FOREIGN KEY (sesion_id) REFERENCES sesiones(id) ON DELETE CASCADE
                )
            """)
            
            # Tabla de carpetas (para replicar estructura vacía también)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS carpetas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id INTEGER NOT NULL,
                    ruta_origen TEXT NOT NULL,
                    ruta_destino TEXT,
                    ruta_relativa TEXT NOT NULL,
                    nombre_carpeta TEXT NOT NULL,
                    estado TEXT DEFAULT 'PENDIENTE',
                    fecha_creada TEXT,
                    FOREIGN KEY (sesion_id) REFERENCES sesiones(id) ON DELETE CASCADE
                )
            """)
            
            # Tabla de log de eventos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_eventos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id INTEGER,
                    timestamp TEXT NOT NULL,
                    nivel TEXT NOT NULL,
                    categoria TEXT,
                    mensaje TEXT NOT NULL,
                    detalles TEXT,
                    FOREIGN KEY (sesion_id) REFERENCES sesiones(id) ON DELETE CASCADE
                )
            """)
            
            # Índices para mejorar rendimiento
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_archivos_sesion ON archivos(sesion_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_archivos_estado ON archivos(estado)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_archivos_ruta ON archivos(ruta_origen)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_carpetas_sesion ON carpetas(sesion_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_log_sesion ON log_eventos(sesion_id)")
    
    # ==================== SESIONES ====================
    
    def crear_sesion(self, nombre: str, ruta_origen: str, ruta_destino: str) -> int:
        """
        Crea una nueva sesión de backup.
        
        Returns:
            ID de la sesión creada
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO sesiones (nombre, ruta_origen, ruta_destino, estado, fecha_creacion, fecha_ultima_actividad)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nombre, ruta_origen, ruta_destino, SessionStatus.CREATED, now, now))
            return cursor.lastrowid
    
    def obtener_sesion(self, sesion_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene los datos de una sesión."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sesiones WHERE id = ?", (sesion_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def obtener_todas_sesiones(self) -> List[Dict[str, Any]]:
        """Obtiene todas las sesiones."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sesiones ORDER BY fecha_creacion DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def actualizar_sesion(self, sesion_id: int, **kwargs):
        """Actualiza campos de una sesión."""
        if not kwargs:
            return
        
        kwargs['fecha_ultima_actividad'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            campos = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            valores = list(kwargs.values()) + [sesion_id]
            cursor.execute(f"UPDATE sesiones SET {campos} WHERE id = ?", valores)
    
    def eliminar_sesion(self, sesion_id: int):
        """Elimina una sesión y todos sus datos relacionados."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM archivos WHERE sesion_id = ?", (sesion_id,))
            cursor.execute("DELETE FROM carpetas WHERE sesion_id = ?", (sesion_id,))
            cursor.execute("DELETE FROM log_eventos WHERE sesion_id = ?", (sesion_id,))
            cursor.execute("DELETE FROM sesiones WHERE id = ?", (sesion_id,))
    
    # ==================== ARCHIVOS ====================
    
    def insertar_archivo(self, sesion_id: int, ruta_origen: str, ruta_relativa: str,
                         nombre_archivo: str, extension: str, tamano_bytes: int,
                         fecha_modificacion: str, es_solo_nube: bool = False) -> int:
        """Inserta un archivo en el catálogo."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO archivos (sesion_id, ruta_origen, ruta_relativa, nombre_archivo,
                                      extension, tamano_bytes, fecha_modificacion, es_solo_nube, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sesion_id, ruta_origen, ruta_relativa, nombre_archivo,
                  extension, tamano_bytes, fecha_modificacion, int(es_solo_nube), FileStatus.PENDING))
            return cursor.lastrowid
    
    def insertar_archivos_batch(self, archivos: List[Tuple]) -> int:
        """
        Inserta múltiples archivos en batch para mejor rendimiento.
        
        Args:
            archivos: Lista de tuplas (sesion_id, ruta_origen, ruta_relativa, nombre_archivo,
                                       extension, tamano_bytes, fecha_modificacion, es_solo_nube)
        
        Returns:
            Número de archivos insertados
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO archivos (sesion_id, ruta_origen, ruta_relativa, nombre_archivo,
                                      extension, tamano_bytes, fecha_modificacion, es_solo_nube, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
            """, archivos)
            return cursor.rowcount
    
    def obtener_archivos_pendientes(self, sesion_id: int, limite: int = 1000) -> List[Dict[str, Any]]:
        """Obtiene archivos pendientes de copiar."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM archivos 
                WHERE sesion_id = ? AND estado = ?
                ORDER BY id
                LIMIT ?
            """, (sesion_id, FileStatus.PENDING, limite))
            return [dict(row) for row in cursor.fetchall()]
    
    def obtener_archivos_error(self, sesion_id: int) -> List[Dict[str, Any]]:
        """Obtiene archivos con error."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM archivos 
                WHERE sesion_id = ? AND estado = ?
                ORDER BY id
            """, (sesion_id, FileStatus.ERROR))
            return [dict(row) for row in cursor.fetchall()]
    
    def actualizar_archivo(self, archivo_id: int, **kwargs):
        """Actualiza campos de un archivo."""
        if not kwargs:
            return
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            campos = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            valores = list(kwargs.values()) + [archivo_id]
            cursor.execute(f"UPDATE archivos SET {campos} WHERE id = ?", valores)
    
    def marcar_archivo_copiado(self, archivo_id: int, ruta_destino: str, hash_origen: str):
        """Marca un archivo como copiado."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.actualizar_archivo(
            archivo_id,
            ruta_destino=ruta_destino,
            hash_origen=hash_origen,
            estado=FileStatus.COPYING,
            fecha_copiado=now
        )
    
    def marcar_archivo_verificado(self, archivo_id: int, hash_destino: str, exito: bool, error: str = None):
        """Marca un archivo como verificado."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if exito:
            self.actualizar_archivo(
                archivo_id,
                hash_destino=hash_destino,
                estado=FileStatus.COMPLETED,
                fecha_verificado=now
            )
        else:
            self.actualizar_archivo(
                archivo_id,
                hash_destino=hash_destino,
                estado=FileStatus.ERROR,
                error_mensaje=error or "Hash no coincide",
                fecha_verificado=now
            )
    
    def marcar_archivo_error(self, archivo_id: int, error_mensaje: str, incrementar_intento: bool = True):
        """Marca un archivo con error."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if incrementar_intento:
                cursor.execute("""
                    UPDATE archivos 
                    SET estado = ?, error_mensaje = ?, intentos = intentos + 1
                    WHERE id = ?
                """, (FileStatus.ERROR, error_mensaje, archivo_id))
            else:
                cursor.execute("""
                    UPDATE archivos 
                    SET estado = ?, error_mensaje = ?
                    WHERE id = ?
                """, (FileStatus.ERROR, error_mensaje, archivo_id))
    
    def obtener_estadisticas_sesion(self, sesion_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas detalladas de una sesión."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de archivos y tamaño
            cursor.execute("""
                SELECT COUNT(*) as total, COALESCE(SUM(tamano_bytes), 0) as tamano_total
                FROM archivos WHERE sesion_id = ?
            """, (sesion_id,))
            row = cursor.fetchone()
            total_archivos = row['total']
            tamano_total = row['tamano_total']
            
            # Por estado
            cursor.execute("""
                SELECT estado, COUNT(*) as cantidad, COALESCE(SUM(tamano_bytes), 0) as tamano
                FROM archivos WHERE sesion_id = ?
                GROUP BY estado
            """, (sesion_id,))
            
            estados = {}
            for row in cursor.fetchall():
                estados[row['estado']] = {
                    'cantidad': row['cantidad'],
                    'tamano': row['tamano']
                }
            
            # Total de carpetas
            cursor.execute("SELECT COUNT(*) as total FROM carpetas WHERE sesion_id = ?", (sesion_id,))
            total_carpetas = cursor.fetchone()['total']
            
            return {
                'total_archivos': total_archivos,
                'tamano_total': tamano_total,
                'total_carpetas': total_carpetas,
                'por_estado': estados,
                'completados': estados.get(FileStatus.COMPLETED, {}).get('cantidad', 0),
                'pendientes': estados.get(FileStatus.PENDING, {}).get('cantidad', 0),
                'errores': estados.get(FileStatus.ERROR, {}).get('cantidad', 0),
                'bytes_copiados': estados.get(FileStatus.COMPLETED, {}).get('tamano', 0)
            }
    
    # ==================== CARPETAS ====================
    
    def insertar_carpeta(self, sesion_id: int, ruta_origen: str, ruta_relativa: str, nombre_carpeta: str) -> int:
        """Inserta una carpeta en el catálogo."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO carpetas (sesion_id, ruta_origen, ruta_relativa, nombre_carpeta, estado)
                VALUES (?, ?, ?, ?, ?)
            """, (sesion_id, ruta_origen, ruta_relativa, nombre_carpeta, FileStatus.PENDING))
            return cursor.lastrowid
    
    def insertar_carpetas_batch(self, carpetas: List[Tuple]) -> int:
        """Inserta múltiples carpetas en batch."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO carpetas (sesion_id, ruta_origen, ruta_relativa, nombre_carpeta, estado)
                VALUES (?, ?, ?, ?, 'PENDIENTE')
            """, carpetas)
            return cursor.rowcount
    
    def obtener_carpetas(self, sesion_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las carpetas de una sesión."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM carpetas WHERE sesion_id = ?
                ORDER BY ruta_relativa
            """, (sesion_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def marcar_carpeta_creada(self, carpeta_id: int, ruta_destino: str):
        """Marca una carpeta como creada."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE carpetas SET ruta_destino = ?, estado = ?, fecha_creada = ?
                WHERE id = ?
            """, (ruta_destino, FileStatus.COMPLETED, now, carpeta_id))
    
    # ==================== LOG ====================
    
    def log(self, sesion_id: int, nivel: str, mensaje: str, categoria: str = None, detalles: str = None):
        """Registra un evento en el log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO log_eventos (sesion_id, timestamp, nivel, categoria, mensaje, detalles)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sesion_id, now, nivel, categoria, mensaje, detalles))
    
    def obtener_log(self, sesion_id: int, limite: int = 100) -> List[Dict[str, Any]]:
        """Obtiene entradas del log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM log_eventos 
                WHERE sesion_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (sesion_id, limite))
            return [dict(row) for row in cursor.fetchall()]
    
    def obtener_log_errores(self, sesion_id: int) -> List[Dict[str, Any]]:
        """Obtiene solo entradas de error del log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM log_eventos 
                WHERE sesion_id = ? AND nivel = 'ERROR'
                ORDER BY id DESC
            """, (sesion_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== UTILIDADES ====================
    
    def reintentar_errores(self, sesion_id: int):
        """Resetea archivos con error para reintentarlos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE archivos 
                SET estado = ?, error_mensaje = NULL
                WHERE sesion_id = ? AND estado = ?
            """, (FileStatus.PENDING, sesion_id, FileStatus.ERROR))
            return cursor.rowcount
    
    def verificar_archivo_ya_copiado(self, sesion_id: int, ruta_origen: str) -> bool:
        """Verifica si un archivo ya fue copiado exitosamente."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT estado FROM archivos 
                WHERE sesion_id = ? AND ruta_origen = ? AND estado = ?
            """, (sesion_id, ruta_origen, FileStatus.COMPLETED))
            return cursor.fetchone() is not None


# Singleton para usar en toda la aplicación
_db_instance = None

def get_database() -> Database:
    """Obtiene la instancia singleton de la base de datos."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
