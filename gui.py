"""
Interfaz gráfica para BigBackups
GUI profesional usando CustomTkinter
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import webbrowser
from datetime import datetime
from typing import Optional, Callable
from PIL import Image

from config import (
    APP_NAME, 
    APP_VERSION, 
    Colors, 
    SessionStatus, 
    FileStatus
)
from database import Database, get_database
from scanner import FileScanner, ScannerStats
from copier import FileCopier, CopyStats, PostCopyVerifier, VerificationResult
from utils import format_size, format_time, get_drive_space
from i18n import t, get_i18n, I18n


# Configuración de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Rutas de assets
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
ICON_PNG_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.png")

# Configurar AppUserModelID para que Windows muestre nuestro icono en la barra de tareas
# Debe hacerse ANTES de crear cualquier ventana
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RobustDataSolutions.BigBackups.1.0")
except Exception:
    pass


class ProgressFrame(ctk.CTkFrame):
    """Frame para mostrar progreso de operaciones."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(self, width=400, height=15)
        self.progress_bar.pack(pady=(8, 3), padx=15, fill="x")
        self.progress_bar.set(0)
        
        # Etiqueta de porcentaje
        self.label_porcentaje = ctk.CTkLabel(
            self, 
            text="0%",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.label_porcentaje.pack(pady=2)
        
        # Etiqueta de estado
        self.label_estado = ctk.CTkLabel(
            self,
            text=t("progress_ready"),
            font=ctk.CTkFont(size=12)
        )
        self.label_estado.pack(pady=2)
        
        # Frame de estadísticas
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(pady=5, fill="x", padx=15)
        
        # Columna izquierda
        self.left_col = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.left_col.pack(side="left", expand=True, fill="both")
        
        self.label_archivos = ctk.CTkLabel(
            self.left_col,
            text=t("progress_files", current="0", total="0"),
            font=ctk.CTkFont(size=11)
        )
        self.label_archivos.pack(anchor="w", pady=1)
        
        self.label_tamano = ctk.CTkLabel(
            self.left_col,
            text=t("progress_size", current="0 B", total="0 B"),
            font=ctk.CTkFont(size=11)
        )
        self.label_tamano.pack(anchor="w", pady=1)
        
        self.label_errores = ctk.CTkLabel(
            self.left_col,
            text=t("progress_errors", count=0),
            font=ctk.CTkFont(size=11),
            text_color=Colors.ERROR
        )
        self.label_errores.pack(anchor="w", pady=1)
        
        # Columna derecha
        self.right_col = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.right_col.pack(side="right", expand=True, fill="both")
        
        self.label_velocidad = ctk.CTkLabel(
            self.right_col,
            text=t("progress_speed", speed="-- MB/s"),
            font=ctk.CTkFont(size=11)
        )
        self.label_velocidad.pack(anchor="e", pady=1)
        
        self.label_tiempo = ctk.CTkLabel(
            self.right_col,
            text=t("progress_time", time="0s"),
            font=ctk.CTkFont(size=11)
        )
        self.label_tiempo.pack(anchor="e", pady=1)
        
        self.label_restante = ctk.CTkLabel(
            self.right_col,
            text=t("progress_remaining", time="--"),
            font=ctk.CTkFont(size=11)
        )
        self.label_restante.pack(anchor="e", pady=1)
        
        # Archivo actual
        self.label_archivo_actual = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=9),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=500
        )
        self.label_archivo_actual.pack(pady=3, padx=15)
    
    def reset(self):
        """Resetea el progreso."""
        self.progress_bar.set(0)
        self.label_porcentaje.configure(text="0%")
        self.label_estado.configure(text=t("progress_ready"))
        self.label_archivos.configure(text=t("progress_files", current="0", total="0"))
        self.label_tamano.configure(text=t("progress_size", current="0 B", total="0 B"))
        self.label_errores.configure(text=t("progress_errors", count=0))
        self.label_velocidad.configure(text=t("progress_speed", speed="-- MB/s"))
        self.label_tiempo.configure(text=t("progress_time", time="0s"))
        self.label_restante.configure(text=t("progress_remaining", time="--"))
        self.label_archivo_actual.configure(text="")
    
    def update_scan_progress(self, stats: ScannerStats):
        """Actualiza progreso durante escaneo."""
        data = stats.get_stats()
        self.label_estado.configure(text=t("progress_scanning"))
        self.label_archivos.configure(
            text=t("progress_files", current=f"{data['archivos']:,}", total="?")
        )
        self.label_tamano.configure(
            text=t("progress_size", current=format_size(data['tamano']), total="?")
        )
        self.label_errores.configure(text=t("progress_errors", count=data['errores']))
        self.label_archivo_actual.configure(text=data['carpeta_actual'][-80:] if len(data['carpeta_actual']) > 80 else data['carpeta_actual'])
    
    def update_copy_progress(self, stats: CopyStats):
        """Actualiza progreso durante copia."""
        data = stats.get_stats_dict()
        
        porcentaje = data['porcentaje_bytes'] / 100
        self.progress_bar.set(porcentaje)
        self.label_porcentaje.configure(text=f"{data['porcentaje_bytes']:.1f}%")
        
        self.label_estado.configure(text=t("progress_copying"))
        self.label_archivos.configure(
            text=t("progress_files", current=f"{data['archivos_copiados']:,}", total=f"{data['total_archivos']:,}")
        )
        self.label_tamano.configure(
            text=t("progress_size", current=format_size(data['bytes_copiados']), total=format_size(data['total_bytes']))
        )
        self.label_errores.configure(text=t("progress_errors", count=data['archivos_error']))
        
        if data['velocidad'] > 0:
            vel_archivos = data.get('velocidad_archivos', 0)
            self.label_velocidad.configure(
                text=t("progress_speed", speed=f"{format_size(data['velocidad'])}/s | {vel_archivos:.1f} arch/s")
            )
        
        self.label_tiempo.configure(
            text=t("progress_time", time=format_time(data['tiempo_transcurrido']))
        )
        
        if data['tiempo_restante'] > 0:
            self.label_restante.configure(
                text=t("progress_remaining", time=format_time(data['tiempo_restante']))
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
            text=t("log_title"),
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
        self.title(f"Robust Data Solutions - {APP_NAME} v{APP_VERSION}")
        self.geometry("700x800")
        self.minsize(600, 700)
        
        # Icono de ventana
        if os.path.exists(ICON_PATH):
            self.iconbitmap(ICON_PATH)
        # Icono para barra de tareas (usa PNG)
        if os.path.exists(ICON_PNG_PATH):
            try:
                from tkinter import PhotoImage
                icon_img = PhotoImage(file=ICON_PNG_PATH)
                self.wm_iconphoto(True, icon_img)
                self._icon_img = icon_img  # Mantener referencia
            except Exception:
                pass
        
        # Base de datos
        self.db = get_database()
        
        # Estado
        self.sesion_id: Optional[int] = None
        self.scanner: Optional[FileScanner] = None
        self.copier: Optional[FileCopier] = None
        self.verifier: Optional[PostCopyVerifier] = None
        self.hilo_actual: Optional[threading.Thread] = None
        self.operacion_en_curso = False
        
        # Crear interfaz
        self._crear_interfaz()
        
        # Protocolo de cierre
        self.protocol("WM_DELETE_WINDOW", self._on_cerrar)
        
        # Verificar si hay sesiones pendientes al inicio (ejecutar después de renderizar)
        self.after(500, self._verificar_sesiones_pendientes_inicio)
    
    def _verificar_sesiones_pendientes_inicio(self):
        """Verifica si hay sesiones pendientes al iniciar la aplicación."""
        sesiones_pendientes = self.db.obtener_sesiones_pendientes()
        
        if not sesiones_pendientes:
            return
        
        # Mostrar la sesión más reciente
        sesion = sesiones_pendientes[0]
        progreso = self.db.obtener_progreso_sesion(sesion['id'])
        
        # Calcular porcentaje
        porcentaje = 0
        if progreso['total'] > 0:
            porcentaje = (progreso['copiados'] / progreso['total']) * 100
        
        respuesta = messagebox.askyesnocancel(
            t("dialog_pending_session_title"),
            t("dialog_pending_session_message",
              source=sesion['ruta_origen'],
              destination=sesion['ruta_destino'],
              status=sesion['estado'],
              last_activity=sesion['fecha_ultima_actividad'],
              copied=progreso['copiados'],
              total=progreso['total'],
              percentage=porcentaje,
              pending=progreso['pendientes'])
        )
        
        if respuesta is None:  # Cancelar - cerrar la app
            self.destroy()
            return
        elif respuesta:  # Sí - Reanudar sesión
            self._reanudar_sesion_inicio(sesion, progreso)
        # Si No, simplemente continúa con la app vacía
    
    def _reanudar_sesion_inicio(self, sesion: dict, progreso: dict):
        """Restaura una sesión pendiente al inicio de la aplicación."""
        from utils import format_size
        
        # Establecer la sesión actual
        self.sesion_id = sesion['id']
        
        # Rellenar los campos de rutas
        self.origen_entry.delete(0, 'end')
        self.origen_entry.insert(0, sesion['ruta_origen'])
        self.destino_entry.delete(0, 'end')
        self.destino_entry.insert(0, sesion['ruta_destino'])
        
        # Mostrar progreso en la interfaz
        total = progreso['total']
        copiados = progreso['copiados']
        pendientes = progreso['pendientes']
        bytes_copiados = progreso['bytes_copiados']
        bytes_totales = progreso['bytes_totales']
        
        porcentaje = (copiados / total * 100) if total > 0 else 0
        
        self.progress_frame.progress_bar.set(porcentaje / 100)
        self.progress_frame.label_porcentaje.configure(text=f"{porcentaje:.1f}%")
        self.progress_frame.label_estado.configure(text=t("progress_session_resumed"))
        self.progress_frame.label_archivos.configure(text=t("progress_files", current=f"{copiados:,}", total=f"{total:,}"))
        self.progress_frame.label_tamano.configure(
            text=t("progress_size", current=format_size(bytes_copiados), total=format_size(bytes_totales))
        )
        
        # Cambiar texto del botón a "Continuar Copia"
        self._es_continuacion = True
        self.copiar_btn.configure(text=t("btn_continue_copy"), state="normal")
        self.verificar_btn.configure(state="normal")
        
        # Actualizar estado de la sesión
        self.db.actualizar_sesion(self.sesion_id, estado=SessionStatus.PAUSED)
        
        # Log
        self.log_frame.agregar_log(
            t("log_session_resumed", id=self.sesion_id, copied=copiados),
            "SUCCESS"
        )
        self.log_frame.agregar_log(
            t("log_pending_files", count=pendientes, size=format_size(bytes_totales - bytes_copiados)),
            "INFO"
        )
    
    def _crear_interfaz(self):
        """Crea todos los elementos de la interfaz."""
        
        # Frame principal con scroll
        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        # === SECCIÓN: LOGO Y TÍTULO ===
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 10))
        
        # Selector de idioma (arriba a la derecha, discreto)
        self.lang_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.lang_frame.pack(anchor="e", padx=5)
        
        self.lang_selector = ctk.CTkSegmentedButton(
            self.lang_frame,
            values=["ES", "CA", "EN"],
            command=self._on_language_change,
            font=ctk.CTkFont(size=10),
            width=100,
            height=22,
            selected_color=Colors.PRIMARY,
            selected_hover_color=Colors.PRIMARY_HOVER,
            unselected_color=Colors.SURFACE_LIGHT,
            unselected_hover_color=Colors.SURFACE
        )
        self.lang_selector.set("ES")
        self.lang_selector.pack()
        
        # Cargar logo si existe
        if os.path.exists(LOGO_PATH):
            try:
                logo_image = Image.open(LOGO_PATH)
                self.logo_ctk = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(180, 66))
                self.logo_label = ctk.CTkLabel(self.header_frame, image=self.logo_ctk, text="")
                self.logo_label.pack(pady=(0, 5))
            except Exception:
                pass
        
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=f"{APP_NAME}",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.pack()
        
        # Copyright con enlace en cabecera
        self.header_copyright = ctk.CTkLabel(
            self.header_frame,
            text="© 2026 Robust Data Solutions",
            font=ctk.CTkFont(size=9),
            text_color="#818cf8",
            cursor="hand2"
        )
        self.header_copyright.pack()
        self.header_copyright.bind("<Button-1>", lambda e: webbrowser.open("https://robustdatasolutions.com/"))
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text=t("app_subtitle"),
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_SECONDARY
        )
        self.subtitle_label.pack()
        
        # === SECCIÓN: RUTAS ===
        self.paths_frame = ctk.CTkFrame(self.main_frame)
        self.paths_frame.pack(fill="x", pady=6)
        
        # Ruta origen
        self.origen_label = ctk.CTkLabel(
            self.paths_frame,
            text=t("section_source"),
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.origen_label.pack(anchor="w", padx=12, pady=(10, 3))
        
        self.origen_frame = ctk.CTkFrame(self.paths_frame, fg_color="transparent")
        self.origen_frame.pack(fill="x", padx=12, pady=(0, 6))
        
        self.origen_entry = ctk.CTkEntry(
            self.origen_frame,
            placeholder_text=t("placeholder_source"),
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.origen_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.origen_btn = ctk.CTkButton(
            self.origen_frame,
            text=t("btn_browse"),
            width=80,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=Colors.SURFACE_LIGHT,
            hover_color=Colors.SURFACE,
            command=self._seleccionar_origen
        )
        self.origen_btn.pack(side="right")
        
        # Ruta destino
        self.destino_label = ctk.CTkLabel(
            self.paths_frame,
            text=t("section_destination"),
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.destino_label.pack(anchor="w", padx=12, pady=(6, 3))
        
        self.destino_frame = ctk.CTkFrame(self.paths_frame, fg_color="transparent")
        self.destino_frame.pack(fill="x", padx=12, pady=(0, 10))
        
        self.destino_entry = ctk.CTkEntry(
            self.destino_frame,
            placeholder_text=t("placeholder_destination"),
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.destino_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.destino_btn = ctk.CTkButton(
            self.destino_frame,
            text=t("btn_browse"),
            width=80,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=Colors.SURFACE_LIGHT,
            hover_color=Colors.SURFACE,
            command=self._seleccionar_destino
        )
        self.destino_btn.pack(side="right")
        
        # Info de espacio
        self.espacio_label = ctk.CTkLabel(
            self.paths_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_SECONDARY
        )
        self.espacio_label.pack(anchor="w", padx=12, pady=(0, 6))
        
        # === SECCIÓN: PROGRESO ===
        self.progress_frame = ProgressFrame(self.main_frame)
        self.progress_frame.pack(fill="x", pady=6)
        
        # === SECCIÓN: BOTONES DE ACCIÓN ===
        self.actions_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.actions_frame.pack(fill="x", pady=8)
        
        # Fila 1: Escanear e Iniciar Copia
        self.row1_frame = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        self.row1_frame.pack(fill="x", pady=3)
        
        self.escanear_btn = ctk.CTkButton(
            self.row1_frame,
            text=t("btn_scan"),
            font=ctk.CTkFont(size=12, weight="bold"),
            height=38,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            command=self._iniciar_escaneo
        )
        self.escanear_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        # Estado para saber si es "iniciar" o "continuar"
        self._es_continuacion = False
        
        self.copiar_btn = ctk.CTkButton(
            self.row1_frame,
            text=t("btn_start_copy"),
            font=ctk.CTkFont(size=12, weight="bold"),
            height=38,
            fg_color=Colors.SECONDARY,
            hover_color=Colors.SECONDARY_HOVER,
            state="disabled",
            command=self._iniciar_copia
        )
        self.copiar_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))
        
        # Fila 2: Pausar y Cancelar
        self.row2_frame = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        self.row2_frame.pack(fill="x", pady=3)
        
        self.pausar_btn = ctk.CTkButton(
            self.row2_frame,
            text=t("btn_pause"),
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=Colors.ACTION_PAUSE,
            hover_color=Colors.ACTION_PAUSE_HOVER,
            state="disabled",
            command=self._pausar_operacion
        )
        self.pausar_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.cancelar_btn = ctk.CTkButton(
            self.row2_frame,
            text=t("btn_cancel"),
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=Colors.ACTION_CANCEL,
            hover_color=Colors.ACTION_CANCEL_HOVER,
            state="disabled",
            command=self._cancelar_operacion
        )
        self.cancelar_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))
        
        # Fila 3: Verificar
        self.row3_frame = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        self.row3_frame.pack(fill="x", pady=3)
        
        self.verificar_btn = ctk.CTkButton(
            self.row3_frame,
            text=t("btn_verify"),
            font=ctk.CTkFont(size=12, weight="bold"),
            height=38,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            state="disabled",
            command=self._iniciar_verificacion
        )
        self.verificar_btn.pack(fill="x")
        
        # === SECCIÓN: LOG ===
        self.log_frame = LogFrame(self.main_frame)
        self.log_frame.pack(fill="both", expand=True, pady=6)
        
        # === SECCIÓN: FOOTER ===
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.pack(fill="x", pady=(6, 0))
        
        self.footer_label = ctk.CTkLabel(
            self.footer_frame,
            text=f"{APP_NAME} v{APP_VERSION} | Verificación SHA256",
            font=ctk.CTkFont(size=9),
            text_color=Colors.TEXT_SECONDARY
        )
        self.footer_label.pack()
        
        # Copyright con enlace
        self.copyright_label = ctk.CTkLabel(
            self.footer_frame,
            text="© 2026 Robust Data Solutions",
            font=ctk.CTkFont(size=9),
            text_color="#818cf8",
            cursor="hand2"
        )
        self.copyright_label.pack()
        self.copyright_label.bind("<Button-1>", lambda e: webbrowser.open("https://robustdatasolutions.com/"))
    
    def _on_language_change(self, value: str):
        """Callback cuando el usuario cambia el idioma."""
        lang_map = {"ES": "es", "CA": "ca", "EN": "en"}
        new_lang = lang_map.get(value, "es")
        get_i18n().language = new_lang
        self._update_ui_texts()
    
    def _update_ui_texts(self):
        """Actualiza todos los textos de la interfaz con el idioma actual."""
        # Subtítulo
        self.subtitle_label.configure(text=t("app_subtitle"))
        
        # Sección rutas
        self.origen_label.configure(text=t("section_source"))
        self.destino_label.configure(text=t("section_destination"))
        self.origen_btn.configure(text=t("btn_browse"))
        self.destino_btn.configure(text=t("btn_browse"))
        
        # Botones de acción
        self.escanear_btn.configure(text=t("btn_scan"))
        
        # Botón de copia (puede ser "iniciar" o "continuar")
        if self._es_continuacion:
            self.copiar_btn.configure(text=t("btn_continue_copy"))
        else:
            self.copiar_btn.configure(text=t("btn_start_copy"))
        
        # Restaurar texto de pausar/reanudar según estado actual
        if self.pausar_btn.cget("text").startswith("▶"):
            self.pausar_btn.configure(text=t("btn_resume"))
        else:
            self.pausar_btn.configure(text=t("btn_pause"))
        
        self.cancelar_btn.configure(text=t("btn_cancel"))
        self.verificar_btn.configure(text=t("btn_verify"))
        
        # Actualizar estado del progreso si está en estado inicial
        current_estado = self.progress_frame.label_estado.cget("text")
        if "Listo" in current_estado or "Ready" in current_estado or "Llest" in current_estado:
            if self._es_continuacion:
                self.progress_frame.label_estado.configure(text=t("progress_session_resumed"))
            else:
                self.progress_frame.label_estado.configure(text=t("progress_ready"))
    
    def _seleccionar_origen(self):
        """Abre diálogo para seleccionar carpeta origen."""
        ruta = filedialog.askdirectory(title="Seleccionar carpeta de origen")
        if ruta:
            self.origen_entry.delete(0, "end")
            self.origen_entry.insert(0, ruta)
            self.log_frame.agregar_log(f"Origen seleccionado: {ruta}")
            
            # Resetear sesión y estado de continuación
            self.sesion_id = None
            self._es_continuacion = False
            self.copiar_btn.configure(text=t("btn_start_copy"), state="disabled")
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
        destino = self.destino_entry.get().strip()
        
        # Buscar si existe una sesión previa con las mismas rutas
        sesion_existente = self.db.buscar_sesion_por_rutas(origen, destino)
        
        if sesion_existente:
            # Obtener progreso de la sesión
            progreso = self.db.obtener_progreso_sesion(sesion_existente['id'])
            
            # Preguntar al usuario si quiere continuar
            respuesta = messagebox.askyesnocancel(
                "Sesión encontrada",
                f"Se encontró una sesión anterior con estas rutas:\n\n"
                f"📁 Origen: {origen}\n"
                f"💾 Destino: {destino}\n\n"
                f"Progreso: {progreso['copiados']:,} de {progreso['total']:,} archivos copiados\n"
                f"({progreso['pendientes']:,} pendientes)\n\n"
                f"¿Desea CONTINUAR la sesión anterior?\n\n"
                f"• Sí = Continuar donde lo dejó\n"
                f"• No = Crear nueva sesión (empezar de cero)\n"
                f"• Cancelar = No hacer nada"
            )
            
            if respuesta is None:  # Cancelar
                return
            elif respuesta:  # Sí - Continuar sesión existente
                self.sesion_id = sesion_existente['id']
                self.log_frame.agregar_log(
                    f"Reanudando sesión anterior (ID: {self.sesion_id}) - "
                    f"{progreso['copiados']:,} archivos ya copiados", "SUCCESS"
                )
                # Actualizar estado
                self.db.actualizar_sesion(self.sesion_id, estado=SessionStatus.SCANNING)
                # No necesitamos re-escanear, solo habilitamos el botón de copia
                self._habilitar_copiar_sesion_existente(progreso)
                return
            else:  # No - Crear nueva sesión
                # Eliminar sesión anterior
                self.db.eliminar_sesion(sesion_existente['id'])
                self.log_frame.agregar_log("Sesión anterior eliminada. Creando nueva...", "INFO")
        
        # Crear nueva sesión
        nombre = f"Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
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
    
    def _habilitar_copiar_sesion_existente(self, progreso: dict):
        """Habilita el botón de copia para una sesión existente reanudada."""
        from utils import format_size
        
        # Mostrar progreso en la interfaz
        total = progreso['total']
        copiados = progreso['copiados']
        pendientes = progreso['pendientes']
        bytes_copiados = progreso['bytes_copiados']
        bytes_totales = progreso['bytes_totales']
        
        porcentaje = (copiados / total * 100) if total > 0 else 0
        
        self.progress_frame.progress_bar.set(porcentaje / 100)
        self.progress_frame.label_porcentaje.configure(text=f"{porcentaje:.1f}%")
        self.progress_frame.label_estado.configure(text=t("progress_session_resumed"))
        self.progress_frame.label_archivos.configure(text=t("progress_files", current=f"{copiados:,}", total=f"{total:,}"))
        self.progress_frame.label_tamano.configure(
            text=t("progress_size", current=format_size(bytes_copiados), total=format_size(bytes_totales))
        )
        
        # Cambiar texto del botón a "Continuar Copia"
        self._es_continuacion = True
        self.copiar_btn.configure(text=t("btn_continue_copy"), state="normal")
        self.verificar_btn.configure(state="normal")
        
        self.log_frame.agregar_log(
            t("log_pending_files", count=pendientes, size=format_size(bytes_totales - bytes_copiados)),
            "INFO"
        )
    
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
            
            # Resetear estado de continuación
            self._es_continuacion = False
            self.copiar_btn.configure(text=t("btn_start_copy"))
            
            # Habilitar botón de verificación
            self.verificar_btn.configure(state="normal")
            
            self.progress_frame.progress_bar.set(1.0)
            self.progress_frame.label_porcentaje.configure(text="100%")
            
            # Calcular tiempo total desde fecha_inicio_copia de la sesión
            tiempo_total = data['tiempo_transcurrido']  # Fallback
            if self.sesion_id:
                sesion = self.db.obtener_sesion(self.sesion_id)
                if sesion and sesion.get('fecha_inicio_copia'):
                    try:
                        fecha_inicio = datetime.strptime(sesion['fecha_inicio_copia'], "%Y-%m-%d %H:%M:%S")
                        tiempo_total = (datetime.now() - fecha_inicio).total_seconds()
                    except:
                        pass
            
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
                    f"⏱️ Tiempo total: {format_time(tiempo_total)}\n\n"
                    f"Puedes usar el botón 'Verificar Copia' para una comprobación adicional."
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
                    f"⏭️ Archivos omitidos: {data['archivos_omitidos']}\n"
                    f"⏱️ Tiempo total: {format_time(tiempo_total)}\n\n"
                    f"Revisa el log para más detalles.\n"
                    f"Usa 'Verificar Copia' para comprobar los archivos copiados."
                )
        
        self.after(0, actualizar_ui)
    
    def _iniciar_verificacion(self):
        """Inicia la verificación post-copia."""
        if not self.sesion_id:
            messagebox.showerror("Error", "No hay sesión activa para verificar.")
            return
        
        # Confirmar verificación (puede ser lento)
        respuesta = messagebox.askyesno(
            "Verificación Post-Copia",
            "La verificación comparará cada archivo del destino con el origen:\n\n"
            "• Existencia del archivo\n"
            "• Tamaño correcto\n"
            "• Hash SHA256 idéntico\n\n"
            "Este proceso puede tardar varios minutos.\n"
            "¿Deseas continuar?"
        )
        
        if not respuesta:
            return
        
        # Preparar verificador
        self.verifier = PostCopyVerifier(self.db)
        self.verifier.on_progress = self._on_verify_progress
        self.verifier.on_error = self._on_verify_error
        self.verifier.on_complete = self._on_verify_complete
        
        # Deshabilitar controles
        self._habilitar_controles(False)
        self.verificar_btn.configure(state="disabled")
        self.operacion_en_curso = True
        self.progress_frame.reset()
        self.progress_frame.label_estado.configure(text="Verificando archivos...")
        
        self.log_frame.agregar_log("Iniciando verificación post-copia...", "INFO")
        
        # Ejecutar en hilo separado
        self.hilo_actual = threading.Thread(
            target=self._ejecutar_verificacion,
            daemon=True
        )
        self.hilo_actual.start()
    
    def _ejecutar_verificacion(self):
        """Ejecuta la verificación en un hilo separado."""
        try:
            self.verifier.verificar_sesion(self.sesion_id, verificar_hash=True)
        except Exception as e:
            self.after(0, lambda: self._on_verify_error("", str(e)))
    
    def _on_verify_progress(self, actual: int, total: int, archivo: str):
        """Callback de progreso de la verificación."""
        def actualizar():
            porcentaje = actual / total if total > 0 else 0
            self.progress_frame.progress_bar.set(porcentaje)
            self.progress_frame.label_porcentaje.configure(text=f"{porcentaje*100:.1f}%")
            self.progress_frame.label_estado.configure(text=f"Verificando: {archivo}")
            self.progress_frame.label_archivos.configure(text=f"📄 {actual:,} / {total:,}")
        self.after(0, actualizar)
    
    def _on_verify_error(self, archivo: str, error: str):
        """Callback de error de la verificación."""
        self.after(0, lambda: self.log_frame.agregar_log(f"⚠️ {archivo}: {error}", "WARNING"))
    
    def _on_verify_complete(self, result: VerificationResult):
        """Callback de verificación completada."""
        def actualizar_ui():
            self._habilitar_controles(True)
            self.verificar_btn.configure(state="normal")
            self.operacion_en_curso = False
            
            self.progress_frame.progress_bar.set(1.0)
            self.progress_frame.label_porcentaje.configure(text="100%")
            
            if result.todo_ok:
                self.progress_frame.label_estado.configure(text="¡Verificación exitosa! ✅✅")
                self.log_frame.agregar_log(
                    f"✅ Verificación completada: {result.archivos_ok:,}/{result.total_archivos:,} archivos OK",
                    "SUCCESS"
                )
                messagebox.showinfo(
                    "Verificación Exitosa",
                    f"¡Todos los archivos han sido verificados correctamente!\n\n"
                    f"✅ Archivos verificados: {result.archivos_ok:,}\n"
                    f"📁 Total archivos: {result.total_archivos:,}\n\n"
                    f"La copia es 100% idéntica al origen."
                )
            else:
                self.progress_frame.label_estado.configure(text="Verificación con problemas ⚠️")
                self.log_frame.agregar_log(result.get_summary(), "WARNING")
                
                detalles = []
                if result.archivos_faltantes_destino > 0:
                    detalles.append(f"❌ Faltantes en destino: {result.archivos_faltantes_destino}")
                if result.archivos_tamano_diferente > 0:
                    detalles.append(f"📏 Tamaño diferente: {result.archivos_tamano_diferente}")
                if result.archivos_hash_diferente > 0:
                    detalles.append(f"🔐 Hash diferente: {result.archivos_hash_diferente}")
                
                messagebox.showwarning(
                    "Verificación con Problemas",
                    f"Se encontraron diferencias entre origen y destino:\n\n"
                    f"{chr(10).join(detalles)}\n\n"
                    f"✅ Archivos OK: {result.archivos_ok:,}\n"
                    f"📁 Total: {result.total_archivos:,}\n\n"
                    f"Revisa el log para más detalles."
                )
        
        self.after(0, actualizar_ui)
    
    def _pausar_operacion(self):
        """Pausa o reanuda la operación actual."""
        if not self.operacion_en_curso:
            return
        
        esta_pausado = self.pausar_btn.cget("text") != "⏸️ Pausar"
        
        if esta_pausado:
            # Reanudar
            if self.scanner:
                self.scanner.reanudar()
            if self.copier:
                self.copier.reanudar()
            if self.verifier:
                self.verifier.reanudar()
            self.pausar_btn.configure(text=t("btn_pause"))
            self.log_frame.agregar_log("Operación reanudada")
        else:
            # Pausar
            if self.scanner:
                self.scanner.pausar()
            if self.copier:
                self.copier.pausar()
            if self.verifier:
                self.verifier.pausar()
            self.pausar_btn.configure(text=t("btn_resume"))
            self.log_frame.agregar_log("Operación pausada", "WARNING")
    
    def _cancelar_operacion(self):
        """Cancela la operación actual."""
        respuesta = messagebox.askyesno(
            t("dialog_cancel_title"),
            t("dialog_cancel_message")
        )
        
        if respuesta:
            if self.scanner:
                self.scanner.cancelar()
            if self.copier:
                self.copier.cancelar()
            if self.verifier:
                self.verifier.cancelar()
            
            self.log_frame.agregar_log(t("log_operation_cancelled"), "WARNING")
    
    def _on_cerrar(self):
        """Maneja el cierre de la aplicación."""
        if self.operacion_en_curso:
            respuesta = messagebox.askyesno(
                t("dialog_operation_in_progress_title"),
                t("dialog_operation_in_progress_message")
            )
            if not respuesta:
                return
            
            if self.scanner:
                self.scanner.cancelar()
            if self.copier:
                self.copier.cancelar()
        
        # Guardar estado de la sesión como PAUSADA si existe
        if self.sesion_id:
            try:
                sesion = self.db.obtener_sesion(self.sesion_id)
                if sesion and sesion['estado'] not in (SessionStatus.COMPLETED, SessionStatus.CREATED):
                    self.db.actualizar_sesion(self.sesion_id, estado=SessionStatus.PAUSED)
            except Exception:
                pass  # No bloquear el cierre por errores de BD
        
        self.destroy()


def main():
    """Punto de entrada de la aplicación GUI."""
    app = BigBackupsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
