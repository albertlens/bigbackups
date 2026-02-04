"""
Interfaz gráfica para BigBackups
GUI profesional usando CustomTkinter
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
from datetime import datetime
from typing import Optional, Callable

from config import (
    APP_NAME, 
    APP_VERSION, 
    Colors, 
    SessionStatus, 
    FileStatus
)
from database import Database, get_database
from scanner import FileScanner, ScannerStats
from copier import FileCopier, CopyStats
from utils import format_size, format_time, get_drive_space


# Configuración de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ProgressFrame(ctk.CTkFrame):
    """Frame para mostrar progreso de operaciones."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(self, width=400, height=20)
        self.progress_bar.pack(pady=(10, 5), padx=20, fill="x")
        self.progress_bar.set(0)
        
        # Etiqueta de porcentaje
        self.label_porcentaje = ctk.CTkLabel(
            self, 
            text="0%",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.label_porcentaje.pack(pady=5)
        
        # Etiqueta de estado
        self.label_estado = ctk.CTkLabel(
            self,
            text="Listo para iniciar",
            font=ctk.CTkFont(size=14)
        )
        self.label_estado.pack(pady=5)
        
        # Frame de estadísticas
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(pady=10, fill="x", padx=20)
        
        # Columna izquierda
        self.left_col = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.left_col.pack(side="left", expand=True, fill="both")
        
        self.label_archivos = ctk.CTkLabel(
            self.left_col,
            text="Archivos: 0 / 0",
            font=ctk.CTkFont(size=12)
        )
        self.label_archivos.pack(anchor="w", pady=2)
        
        self.label_tamano = ctk.CTkLabel(
            self.left_col,
            text="Tamaño: 0 B / 0 B",
            font=ctk.CTkFont(size=12)
        )
        self.label_tamano.pack(anchor="w", pady=2)
        
        self.label_errores = ctk.CTkLabel(
            self.left_col,
            text="Errores: 0",
            font=ctk.CTkFont(size=12),
            text_color=Colors.ERROR
        )
        self.label_errores.pack(anchor="w", pady=2)
        
        # Columna derecha
        self.right_col = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.right_col.pack(side="right", expand=True, fill="both")
        
        self.label_velocidad = ctk.CTkLabel(
            self.right_col,
            text="Velocidad: -- MB/s",
            font=ctk.CTkFont(size=12)
        )
        self.label_velocidad.pack(anchor="e", pady=2)
        
        self.label_tiempo = ctk.CTkLabel(
            self.right_col,
            text="Tiempo: 0s",
            font=ctk.CTkFont(size=12)
        )
        self.label_tiempo.pack(anchor="e", pady=2)
        
        self.label_restante = ctk.CTkLabel(
            self.right_col,
            text="Restante: --",
            font=ctk.CTkFont(size=12)
        )
        self.label_restante.pack(anchor="e", pady=2)
        
        # Archivo actual
        self.label_archivo_actual = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=500
        )
        self.label_archivo_actual.pack(pady=5, padx=20)
    
    def reset(self):
        """Resetea el progreso."""
        self.progress_bar.set(0)
        self.label_porcentaje.configure(text="0%")
        self.label_estado.configure(text="Listo para iniciar")
        self.label_archivos.configure(text="Archivos: 0 / 0")
        self.label_tamano.configure(text="Tamaño: 0 B / 0 B")
        self.label_errores.configure(text="Errores: 0")
        self.label_velocidad.configure(text="Velocidad: -- MB/s")
        self.label_tiempo.configure(text="Tiempo: 0s")
        self.label_restante.configure(text="Restante: --")
        self.label_archivo_actual.configure(text="")
    
    def update_scan_progress(self, stats: ScannerStats):
        """Actualiza progreso durante escaneo."""
        data = stats.get_stats()
        self.label_estado.configure(text="Escaneando...")
        self.label_archivos.configure(
            text=f"Archivos: {data['archivos']:,}"
        )
        self.label_tamano.configure(
            text=f"Tamaño: {format_size(data['tamano'])}"
        )
        self.label_errores.configure(text=f"Errores: {data['errores']}")
        self.label_archivo_actual.configure(text=data['carpeta_actual'][-80:] if len(data['carpeta_actual']) > 80 else data['carpeta_actual'])
    
    def update_copy_progress(self, stats: CopyStats):
        """Actualiza progreso durante copia."""
        data = stats.get_stats_dict()
        
        porcentaje = data['porcentaje_bytes'] / 100
        self.progress_bar.set(porcentaje)
        self.label_porcentaje.configure(text=f"{data['porcentaje_bytes']:.1f}%")
        
        self.label_estado.configure(text="Copiando archivos...")
        self.label_archivos.configure(
            text=f"Archivos: {data['archivos_copiados']:,} / {data['total_archivos']:,}"
        )
        self.label_tamano.configure(
            text=f"Tamaño: {format_size(data['bytes_copiados'])} / {format_size(data['total_bytes'])}"
        )
        self.label_errores.configure(text=f"Errores: {data['archivos_error']}")
        
        if data['velocidad'] > 0:
            self.label_velocidad.configure(
                text=f"Velocidad: {format_size(data['velocidad'])}/s"
            )
        
        self.label_tiempo.configure(
            text=f"Tiempo: {format_time(data['tiempo_transcurrido'])}"
        )
        
        if data['tiempo_restante'] > 0:
            self.label_restante.configure(
                text=f"Restante: {format_time(data['tiempo_restante'])}"
            )
        
        archivo = data['archivo_actual']
        if len(archivo) > 80:
            archivo = "..." + archivo[-77:]
        self.label_archivo_actual.configure(text=archivo)


class LogFrame(ctk.CTkFrame):
    """Frame para mostrar log de eventos."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Título
        self.title = ctk.CTkLabel(
            self,
            text="📋 Log de Eventos",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title.pack(pady=(10, 5), padx=10, anchor="w")
        
        # Área de texto
        self.textbox = ctk.CTkTextbox(
            self,
            width=400,
            height=150,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.textbox.pack(pady=5, padx=10, fill="both", expand=True)
        self.textbox.configure(state="disabled")
    
    def agregar_log(self, mensaje: str, nivel: str = "INFO"):
        """Agrega una entrada al log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color según nivel
        prefijos = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }
        prefijo = prefijos.get(nivel, "•")
        
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"[{timestamp}] {prefijo} {mensaje}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")
    
    def limpiar(self):
        """Limpia el log."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


class BigBackupsApp(ctk.CTk):
    """Aplicación principal de BigBackups."""
    
    def __init__(self):
        super().__init__()
        
        # Configuración de ventana
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("700x800")
        self.minsize(600, 700)
        
        # Base de datos
        self.db = get_database()
        
        # Estado
        self.sesion_id: Optional[int] = None
        self.scanner: Optional[FileScanner] = None
        self.copier: Optional[FileCopier] = None
        self.hilo_actual: Optional[threading.Thread] = None
        self.operacion_en_curso = False
        
        # Crear interfaz
        self._crear_interfaz()
        
        # Protocolo de cierre
        self.protocol("WM_DELETE_WINDOW", self._on_cerrar)
    
    def _crear_interfaz(self):
        """Crea todos los elementos de la interfaz."""
        
        # Frame principal con scroll
        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === SECCIÓN: TÍTULO ===
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=f"🗂️ {APP_NAME}",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack()
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Copia segura de grandes volúmenes de datos con verificación SHA256",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        )
        self.subtitle_label.pack()
        
        # === SECCIÓN: RUTAS ===
        self.paths_frame = ctk.CTkFrame(self.main_frame)
        self.paths_frame.pack(fill="x", pady=10)
        
        # Ruta origen
        self.origen_label = ctk.CTkLabel(
            self.paths_frame,
            text="📁 Carpeta Origen:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.origen_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.origen_frame = ctk.CTkFrame(self.paths_frame, fg_color="transparent")
        self.origen_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.origen_entry = ctk.CTkEntry(
            self.origen_frame,
            placeholder_text="Selecciona la carpeta de origen...",
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.origen_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.origen_btn = ctk.CTkButton(
            self.origen_frame,
            text="Explorar",
            width=100,
            height=35,
            command=self._seleccionar_origen
        )
        self.origen_btn.pack(side="right")
        
        # Ruta destino
        self.destino_label = ctk.CTkLabel(
            self.paths_frame,
            text="💾 Carpeta Destino:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.destino_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.destino_frame = ctk.CTkFrame(self.paths_frame, fg_color="transparent")
        self.destino_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.destino_entry = ctk.CTkEntry(
            self.destino_frame,
            placeholder_text="Selecciona la carpeta de destino (disco externo)...",
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.destino_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.destino_btn = ctk.CTkButton(
            self.destino_frame,
            text="Explorar",
            width=100,
            height=35,
            command=self._seleccionar_destino
        )
        self.destino_btn.pack(side="right")
        
        # Info de espacio
        self.espacio_label = ctk.CTkLabel(
            self.paths_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY
        )
        self.espacio_label.pack(anchor="w", padx=15, pady=(0, 10))
        
        # === SECCIÓN: PROGRESO ===
        self.progress_frame = ProgressFrame(self.main_frame)
        self.progress_frame.pack(fill="x", pady=10)
        
        # === SECCIÓN: BOTONES DE ACCIÓN ===
        self.actions_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.actions_frame.pack(fill="x", pady=15)
        
        # Fila 1: Escanear e Iniciar Copia
        self.row1_frame = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        self.row1_frame.pack(fill="x", pady=5)
        
        self.escanear_btn = ctk.CTkButton(
            self.row1_frame,
            text="🔍 1. Escanear Origen",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            fg_color=Colors.PRIMARY,
            command=self._iniciar_escaneo
        )
        self.escanear_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.copiar_btn = ctk.CTkButton(
            self.row1_frame,
            text="📋 2. Iniciar Copia",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            fg_color=Colors.SUCCESS,
            state="disabled",
            command=self._iniciar_copia
        )
        self.copiar_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # Fila 2: Pausar y Cancelar
        self.row2_frame = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        self.row2_frame.pack(fill="x", pady=5)
        
        self.pausar_btn = ctk.CTkButton(
            self.row2_frame,
            text="⏸️ Pausar",
            height=40,
            fg_color=Colors.WARNING,
            state="disabled",
            command=self._pausar_operacion
        )
        self.pausar_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.cancelar_btn = ctk.CTkButton(
            self.row2_frame,
            text="❌ Cancelar",
            height=40,
            fg_color=Colors.ERROR,
            state="disabled",
            command=self._cancelar_operacion
        )
        self.cancelar_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # === SECCIÓN: LOG ===
        self.log_frame = LogFrame(self.main_frame)
        self.log_frame.pack(fill="both", expand=True, pady=10)
        
        # === SECCIÓN: FOOTER ===
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.pack(fill="x", pady=(10, 0))
        
        self.footer_label = ctk.CTkLabel(
            self.footer_frame,
            text=f"{APP_NAME} v{APP_VERSION} | Verificación SHA256 | Copia segura garantizada",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_SECONDARY
        )
        self.footer_label.pack()
    
    def _seleccionar_origen(self):
        """Abre diálogo para seleccionar carpeta origen."""
        ruta = filedialog.askdirectory(title="Seleccionar carpeta de origen")
        if ruta:
            self.origen_entry.delete(0, "end")
            self.origen_entry.insert(0, ruta)
            self.log_frame.agregar_log(f"Origen seleccionado: {ruta}")
            
            # Resetear sesión
            self.sesion_id = None
            self.copiar_btn.configure(state="disabled")
            self.progress_frame.reset()
    
    def _seleccionar_destino(self):
        """Abre diálogo para seleccionar carpeta destino."""
        ruta = filedialog.askdirectory(title="Seleccionar carpeta de destino (disco externo)")
        if ruta:
            self.destino_entry.delete(0, "end")
            self.destino_entry.insert(0, ruta)
            self.log_frame.agregar_log(f"Destino seleccionado: {ruta}")
            
            # Mostrar espacio disponible
            total, usado, libre = get_drive_space(ruta)
            if total > 0:
                self.espacio_label.configure(
                    text=f"💿 Espacio disponible: {format_size(libre)} de {format_size(total)} ({(libre/total)*100:.1f}% libre)"
                )
    
    def _validar_rutas(self) -> bool:
        """Valida que las rutas estén correctamente configuradas."""
        origen = self.origen_entry.get().strip()
        destino = self.destino_entry.get().strip()
        
        if not origen:
            messagebox.showerror("Error", "Debes seleccionar una carpeta de origen.")
            return False
        
        if not os.path.exists(origen):
            messagebox.showerror("Error", f"La carpeta de origen no existe:\n{origen}")
            return False
        
        if not os.path.isdir(origen):
            messagebox.showerror("Error", "La ruta de origen debe ser una carpeta, no un archivo.")
            return False
        
        return True
    
    def _validar_destino(self) -> bool:
        """Valida la ruta de destino."""
        destino = self.destino_entry.get().strip()
        
        if not destino:
            messagebox.showerror("Error", "Debes seleccionar una carpeta de destino.")
            return False
        
        # Crear si no existe
        if not os.path.exists(destino):
            try:
                os.makedirs(destino)
                self.log_frame.agregar_log(f"Carpeta destino creada: {destino}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta de destino:\n{e}")
                return False
        
        return True
    
    def _habilitar_controles(self, habilitar: bool):
        """Habilita o deshabilita controles durante operaciones."""
        estado = "normal" if habilitar else "disabled"
        estado_inv = "disabled" if habilitar else "normal"
        
        self.origen_btn.configure(state=estado)
        self.destino_btn.configure(state=estado)
        self.escanear_btn.configure(state=estado)
        
        self.pausar_btn.configure(state=estado_inv)
        self.cancelar_btn.configure(state=estado_inv)
    
    def _iniciar_escaneo(self):
        """Inicia el proceso de escaneo."""
        if not self._validar_rutas():
            return
        
        origen = self.origen_entry.get().strip()
        
        # Crear sesión
        nombre = f"Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        destino = self.destino_entry.get().strip() or "Pendiente"
        
        self.sesion_id = self.db.crear_sesion(nombre, origen, destino)
        self.log_frame.agregar_log(f"Sesión creada: {nombre} (ID: {self.sesion_id})", "SUCCESS")
        
        # Preparar scanner
        self.scanner = FileScanner(self.db)
        self.scanner.on_progress = self._on_scan_progress
        self.scanner.on_error = self._on_scan_error
        self.scanner.on_complete = self._on_scan_complete
        
        # Deshabilitar controles
        self._habilitar_controles(False)
        self.operacion_en_curso = True
        self.progress_frame.reset()
        
        self.log_frame.agregar_log(f"Iniciando escaneo de: {origen}")
        
        # Ejecutar en hilo separado
        self.hilo_actual = threading.Thread(
            target=self._ejecutar_escaneo,
            args=(origen,),
            daemon=True
        )
        self.hilo_actual.start()
    
    def _ejecutar_escaneo(self, origen: str):
        """Ejecuta el escaneo en un hilo separado."""
        try:
            self.scanner.escanear(self.sesion_id, origen)
        except Exception as e:
            self.after(0, lambda: self._on_scan_error("", str(e)))
    
    def _on_scan_progress(self, stats: ScannerStats):
        """Callback de progreso del escaneo."""
        self.after(0, lambda: self.progress_frame.update_scan_progress(stats))
    
    def _on_scan_error(self, archivo: str, error: str):
        """Callback de error del escaneo."""
        self.after(0, lambda: self.log_frame.agregar_log(f"Error: {archivo} - {error}", "ERROR"))
    
    def _on_scan_complete(self, stats: ScannerStats):
        """Callback de escaneo completado."""
        def actualizar_ui():
            data = stats.get_stats()
            self._habilitar_controles(True)
            self.operacion_en_curso = False
            
            # Habilitar botón de copia
            self.copiar_btn.configure(state="normal")
            
            self.progress_frame.label_estado.configure(text="Escaneo completado ✅")
            self.log_frame.agregar_log(
                f"Escaneo completado: {data['archivos']:,} archivos, "
                f"{data['carpetas']:,} carpetas, {format_size(data['tamano'])}",
                "SUCCESS"
            )
            
            if data['nube'] > 0:
                self.log_frame.agregar_log(
                    f"⚠️ {data['nube']} archivos están solo en la nube (OneDrive)",
                    "WARNING"
                )
            
            if data['errores'] > 0:
                self.log_frame.agregar_log(
                    f"⚠️ {data['errores']} errores durante el escaneo",
                    "WARNING"
                )
        
        self.after(0, actualizar_ui)
    
    def _iniciar_copia(self):
        """Inicia el proceso de copia."""
        if not self.sesion_id:
            messagebox.showerror("Error", "Primero debes escanear la carpeta de origen.")
            return
        
        if not self._validar_destino():
            return
        
        destino = self.destino_entry.get().strip()
        
        # Verificar espacio
        stats = self.db.obtener_estadisticas_sesion(self.sesion_id)
        total, usado, libre = get_drive_space(destino)
        bytes_necesarios = stats['tamano_total']
        
        if libre < bytes_necesarios * 1.05:
            respuesta = messagebox.askyesno(
                "Espacio insuficiente",
                f"El destino puede no tener espacio suficiente.\n\n"
                f"Necesario: {format_size(bytes_necesarios)}\n"
                f"Disponible: {format_size(libre)}\n\n"
                f"¿Deseas continuar de todos modos?"
            )
            if not respuesta:
                return
        
        # Preparar copier
        self.copier = FileCopier(self.db)
        self.copier.on_progress = self._on_copy_progress
        self.copier.on_error = self._on_copy_error
        self.copier.on_complete = self._on_copy_complete
        
        # Deshabilitar controles
        self._habilitar_controles(False)
        self.copiar_btn.configure(state="disabled")
        self.operacion_en_curso = True
        
        self.log_frame.agregar_log(f"Iniciando copia a: {destino}")
        
        # Ejecutar en hilo separado
        self.hilo_actual = threading.Thread(
            target=self._ejecutar_copia,
            args=(destino,),
            daemon=True
        )
        self.hilo_actual.start()
    
    def _ejecutar_copia(self, destino: str):
        """Ejecuta la copia en un hilo separado."""
        try:
            self.copier.copiar(self.sesion_id, destino)
        except Exception as e:
            self.after(0, lambda: self._on_copy_error("", str(e)))
    
    def _on_copy_progress(self, stats: CopyStats):
        """Callback de progreso de la copia."""
        self.after(0, lambda: self.progress_frame.update_copy_progress(stats))
    
    def _on_copy_error(self, archivo: str, error: str):
        """Callback de error de la copia."""
        self.after(0, lambda: self.log_frame.agregar_log(f"Error: {archivo} - {error}", "ERROR"))
    
    def _on_copy_complete(self, stats: CopyStats):
        """Callback de copia completada."""
        def actualizar_ui():
            data = stats.get_stats_dict()
            self._habilitar_controles(True)
            self.operacion_en_curso = False
            
            self.progress_frame.progress_bar.set(1.0)
            self.progress_frame.label_porcentaje.configure(text="100%")
            
            if data['archivos_error'] == 0:
                self.progress_frame.label_estado.configure(text="¡Copia completada con éxito! ✅")
                self.log_frame.agregar_log(
                    f"✅ Copia completada: {data['archivos_copiados']:,} archivos, "
                    f"{format_size(data['bytes_copiados'])}",
                    "SUCCESS"
                )
                messagebox.showinfo(
                    "Copia Completada",
                    f"La copia se ha completado exitosamente.\n\n"
                    f"📁 Archivos copiados: {data['archivos_copiados']:,}\n"
                    f"💾 Tamaño total: {format_size(data['bytes_copiados'])}\n"
                    f"⏱️ Tiempo total: {format_time(data['tiempo_transcurrido'])}\n\n"
                    f"Todos los archivos han sido verificados con SHA256."
                )
            else:
                self.progress_frame.label_estado.configure(text="Copia completada con errores ⚠️")
                self.log_frame.agregar_log(
                    f"⚠️ Copia completada con {data['archivos_error']} errores",
                    "WARNING"
                )
                messagebox.showwarning(
                    "Copia Completada con Errores",
                    f"La copia ha finalizado pero hubo errores.\n\n"
                    f"📁 Archivos copiados: {data['archivos_copiados']:,}\n"
                    f"❌ Archivos con error: {data['archivos_error']}\n"
                    f"⏭️ Archivos omitidos: {data['archivos_omitidos']}\n\n"
                    f"Revisa el log para más detalles."
                )
        
        self.after(0, actualizar_ui)
    
    def _pausar_operacion(self):
        """Pausa o reanuda la operación actual."""
        if self.scanner and self.operacion_en_curso:
            if self.pausar_btn.cget("text") == "⏸️ Pausar":
                self.scanner.pausar()
                self.pausar_btn.configure(text="▶️ Reanudar")
                self.log_frame.agregar_log("Operación pausada", "WARNING")
            else:
                self.scanner.reanudar()
                self.pausar_btn.configure(text="⏸️ Pausar")
                self.log_frame.agregar_log("Operación reanudada")
        
        if self.copier and self.operacion_en_curso:
            if self.pausar_btn.cget("text") == "⏸️ Pausar":
                self.copier.pausar()
                self.pausar_btn.configure(text="▶️ Reanudar")
                self.log_frame.agregar_log("Copia pausada", "WARNING")
            else:
                self.copier.reanudar()
                self.pausar_btn.configure(text="⏸️ Pausar")
                self.log_frame.agregar_log("Copia reanudada")
    
    def _cancelar_operacion(self):
        """Cancela la operación actual."""
        respuesta = messagebox.askyesno(
            "Confirmar Cancelación",
            "¿Estás seguro de que deseas cancelar la operación?\n\n"
            "El progreso se guardará y podrás continuar más tarde."
        )
        
        if respuesta:
            if self.scanner:
                self.scanner.cancelar()
            if self.copier:
                self.copier.cancelar()
            
            self.log_frame.agregar_log("Operación cancelada por el usuario", "WARNING")
    
    def _on_cerrar(self):
        """Maneja el cierre de la aplicación."""
        if self.operacion_en_curso:
            respuesta = messagebox.askyesno(
                "Operación en Curso",
                "Hay una operación en curso.\n\n"
                "¿Deseas cancelarla y cerrar la aplicación?\n"
                "El progreso se guardará."
            )
            if not respuesta:
                return
            
            if self.scanner:
                self.scanner.cancelar()
            if self.copier:
                self.copier.cancelar()
        
        self.destroy()


def main():
    """Punto de entrada de la aplicación GUI."""
    app = BigBackupsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
