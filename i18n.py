"""
Sistema de internacionalización (i18n) para BigBackups
Idiomas soportados: Español (es), Català (ca), English (en)
"""

from typing import Dict, Any
import json
import os

# Idioma por defecto
DEFAULT_LANGUAGE = "es"

# Traducciones
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "es": {
        # App info
        "app_subtitle": "Copia segura de grandes volúmenes de datos con verificación SHA256",
        
        # Secciones
        "section_source": "📁 Carpeta Origen:",
        "section_destination": "💾 Carpeta Destino:",
        "placeholder_source": "Selecciona la carpeta de origen...",
        "placeholder_destination": "Selecciona la carpeta de destino (disco externo)...",
        "btn_browse": "Explorar",
        
        # Botones principales
        "btn_scan": "🔍 1. Escanear Origen",
        "btn_start_copy": "📋 2. Iniciar Copia",
        "btn_continue_copy": "📋 2. Continuar Copia",
        "btn_pause": "⏸️ Pausar",
        "btn_resume": "▶️ Reanudar",
        "btn_cancel": "❌ Cancelar",
        "btn_verify": "✅ 3. Verificar Copia",
        
        # Progreso
        "progress_ready": "Listo para iniciar",
        "progress_session_resumed": "Sesión reanudada - Listo para continuar",
        "progress_scanning": "Escaneando...",
        "progress_copying": "Copiando...",
        "progress_verifying": "Verificando...",
        "progress_completed": "¡Completado!",
        "progress_paused": "En pausa",
        "progress_cancelled": "Cancelado",
        "progress_files": "📄 {current} / {total}",
        "progress_size": "Tamaño: {current} / {total}",
        "progress_errors": "Errores: {count}",
        "progress_speed": "Velocidad: {speed}",
        "progress_time": "Tiempo: {time}",
        "progress_remaining": "Restante: {time}",
        
        # Diálogos
        "dialog_pending_session_title": "Sesión pendiente detectada",
        "dialog_pending_session_message": (
            "Se encontró una sesión de backup sin completar:\n\n"
            "📁 Origen: {source}\n"
            "💾 Destino: {destination}\n"
            "📊 Estado: {status}\n"
            "📅 Última actividad: {last_activity}\n\n"
            "Progreso: {copied:,} de {total:,} archivos ({percentage:.1f}%)\n"
            "({pending:,} archivos pendientes)\n\n"
            "¿Desea REANUDAR esta sesión?\n\n"
            "• Sí = Reanudar donde lo dejó\n"
            "• No = Ignorar y empezar de nuevo\n"
            "• Cancelar = Cerrar aplicación"
        ),
        "dialog_session_found_title": "Sesión encontrada",
        "dialog_session_found_message": (
            "Se encontró una sesión anterior con estas rutas:\n\n"
            "📁 Origen: {source}\n"
            "💾 Destino: {destination}\n\n"
            "Progreso: {copied:,} de {total:,} archivos copiados\n"
            "({pending:,} pendientes)\n\n"
            "¿Desea CONTINUAR la sesión anterior?\n\n"
            "• Sí = Continuar donde lo dejó\n"
            "• No = Crear nueva sesión (empezar de cero)\n"
            "• Cancelar = No hacer nada"
        ),
        "dialog_operation_in_progress_title": "Operación en Curso",
        "dialog_operation_in_progress_message": (
            "Hay una operación en curso.\n\n"
            "¿Deseas cancelarla y cerrar la aplicación?\n"
            "El progreso se guardará y podrás continuar más tarde."
        ),
        "dialog_cancel_title": "Confirmar Cancelación",
        "dialog_cancel_message": (
            "¿Estás seguro de que quieres cancelar?\n"
            "El progreso se guardará y podrás continuar más tarde."
        ),
        "dialog_verify_title": "Verificación Post-Copia",
        "dialog_verify_message": (
            "Se verificarán los hashes de {count:,} archivos copiados.\n\n"
            "Esto puede tardar un tiempo considerable.\n"
            "¿Deseas continuar?"
        ),
        "dialog_scan_complete_title": "Escaneo Completo",
        "dialog_scan_complete_message": (
            "Se encontraron {files:,} archivos ({size})\n"
            "en {folders:,} carpetas.\n\n"
            "Haz clic en 'Iniciar Copia' para continuar."
        ),
        "dialog_copy_complete_title": "Copia Completada",
        "dialog_copy_complete_message": (
            "¡Copia completada exitosamente!\n\n"
            "📊 Resumen:\n"
            "• Archivos copiados: {copied:,}\n"
            "• Archivos omitidos: {skipped:,}\n"
            "• Errores: {errors:,}\n"
            "• Tiempo total: {time}\n\n"
            "Se recomienda ejecutar la verificación para confirmar la integridad."
        ),
        
        # Log
        "log_title": "📜 Registro de Actividad:",
        "log_session_created": "Sesión creada: {name} (ID: {id})",
        "log_session_resumed": "Reanudando sesión anterior (ID: {id}) - {copied:,} archivos ya copiados",
        "log_session_deleted": "Sesión anterior eliminada. Creando nueva...",
        "log_scan_starting": "Iniciando escaneo de: {path}",
        "log_scan_complete": "Escaneo completado: {files:,} archivos, {size}",
        "log_copy_starting": "Iniciando copia de {count:,} archivos",
        "log_copy_complete": "Copia completada: {copied:,} archivos copiados",
        "log_verify_starting": "Iniciando verificación de {count:,} archivos",
        "log_verify_complete": "Verificación completada: {verified:,} verificados, {errors:,} errores",
        "log_operation_cancelled": "Operación cancelada por el usuario",
        "log_pending_files": "Pendientes: {count:,} archivos ({size})",
        
        # Errores
        "error_select_source": "Por favor, selecciona una carpeta de origen",
        "error_select_destination": "Por favor, selecciona una carpeta de destino",
        "error_source_not_exists": "La carpeta de origen no existe",
        "error_same_paths": "Las carpetas de origen y destino no pueden ser iguales",
        "error_destination_inside_source": "La carpeta de destino no puede estar dentro del origen",
        "error_insufficient_space": (
            "⚠️ Espacio insuficiente en destino\n\n"
            "Espacio disponible: {available}\n"
            "Espacio requerido: {required}\n\n"
            "¿Deseas continuar de todos modos?"
        ),
        
        # Footer
        "footer_destination_space": "Espacio en destino: {free} libres de {total}",
        "footer_space_unknown": "Espacio en destino: --",
        
        # Idiomas
        "lang_es": "Español",
        "lang_ca": "Català",
        "lang_en": "English",
    },
    
    "ca": {
        # App info
        "app_subtitle": "Còpia segura de grans volums de dades amb verificació SHA256",
        
        # Secciones
        "section_source": "📁 Carpeta Origen:",
        "section_destination": "💾 Carpeta Destí:",
        "placeholder_source": "Selecciona la carpeta d'origen...",
        "placeholder_destination": "Selecciona la carpeta de destí (disc extern)...",
        "btn_browse": "Explorar",
        
        # Botones principales
        "btn_scan": "🔍 1. Escanejar Origen",
        "btn_start_copy": "📋 2. Iniciar Còpia",
        "btn_continue_copy": "📋 2. Continuar Còpia",
        "btn_pause": "⏸️ Pausar",
        "btn_resume": "▶️ Reprendre",
        "btn_cancel": "❌ Cancel·lar",
        "btn_verify": "✅ 3. Verificar Còpia",
        
        # Progreso
        "progress_ready": "Llest per iniciar",
        "progress_session_resumed": "Sessió represa - Llest per continuar",
        "progress_scanning": "Escanejant...",
        "progress_copying": "Copiant...",
        "progress_verifying": "Verificant...",
        "progress_completed": "Completat!",
        "progress_paused": "En pausa",
        "progress_cancelled": "Cancel·lat",
        "progress_files": "📄 {current} / {total}",
        "progress_size": "Mida: {current} / {total}",
        "progress_errors": "Errors: {count}",
        "progress_speed": "Velocitat: {speed}",
        "progress_time": "Temps: {time}",
        "progress_remaining": "Restant: {time}",
        
        # Diálogos
        "dialog_pending_session_title": "Sessió pendent detectada",
        "dialog_pending_session_message": (
            "S'ha trobat una sessió de backup sense completar:\n\n"
            "📁 Origen: {source}\n"
            "💾 Destí: {destination}\n"
            "📊 Estat: {status}\n"
            "📅 Última activitat: {last_activity}\n\n"
            "Progrés: {copied:,} de {total:,} arxius ({percentage:.1f}%)\n"
            "({pending:,} arxius pendents)\n\n"
            "Voleu REPRENDRE aquesta sessió?\n\n"
            "• Sí = Reprendre on ho vau deixar\n"
            "• No = Ignorar i començar de nou\n"
            "• Cancel·lar = Tancar aplicació"
        ),
        "dialog_session_found_title": "Sessió trobada",
        "dialog_session_found_message": (
            "S'ha trobat una sessió anterior amb aquestes rutes:\n\n"
            "📁 Origen: {source}\n"
            "💾 Destí: {destination}\n\n"
            "Progrés: {copied:,} de {total:,} arxius copiats\n"
            "({pending:,} pendents)\n\n"
            "Voleu CONTINUAR la sessió anterior?\n\n"
            "• Sí = Continuar on ho vau deixar\n"
            "• No = Crear nova sessió (començar de zero)\n"
            "• Cancel·lar = No fer res"
        ),
        "dialog_operation_in_progress_title": "Operació en Curs",
        "dialog_operation_in_progress_message": (
            "Hi ha una operació en curs.\n\n"
            "Voleu cancel·lar-la i tancar l'aplicació?\n"
            "El progrés es guardarà i podreu continuar més tard."
        ),
        "dialog_cancel_title": "Confirmar Cancel·lació",
        "dialog_cancel_message": (
            "Esteu segurs que voleu cancel·lar?\n"
            "El progrés es guardarà i podreu continuar més tard."
        ),
        "dialog_verify_title": "Verificació Post-Còpia",
        "dialog_verify_message": (
            "Es verificaran els hashes de {count:,} arxius copiats.\n\n"
            "Això pot trigar un temps considerable.\n"
            "Voleu continuar?"
        ),
        "dialog_scan_complete_title": "Escaneig Complet",
        "dialog_scan_complete_message": (
            "S'han trobat {files:,} arxius ({size})\n"
            "en {folders:,} carpetes.\n\n"
            "Feu clic a 'Iniciar Còpia' per continuar."
        ),
        "dialog_copy_complete_title": "Còpia Completada",
        "dialog_copy_complete_message": (
            "Còpia completada amb èxit!\n\n"
            "📊 Resum:\n"
            "• Arxius copiats: {copied:,}\n"
            "• Arxius omesos: {skipped:,}\n"
            "• Errors: {errors:,}\n"
            "• Temps total: {time}\n\n"
            "Es recomana executar la verificació per confirmar la integritat."
        ),
        
        # Log
        "log_title": "📜 Registre d'Activitat:",
        "log_session_created": "Sessió creada: {name} (ID: {id})",
        "log_session_resumed": "Reprenent sessió anterior (ID: {id}) - {copied:,} arxius ja copiats",
        "log_session_deleted": "Sessió anterior eliminada. Creant nova...",
        "log_scan_starting": "Iniciant escaneig de: {path}",
        "log_scan_complete": "Escaneig completat: {files:,} arxius, {size}",
        "log_copy_starting": "Iniciant còpia de {count:,} arxius",
        "log_copy_complete": "Còpia completada: {copied:,} arxius copiats",
        "log_verify_starting": "Iniciant verificació de {count:,} arxius",
        "log_verify_complete": "Verificació completada: {verified:,} verificats, {errors:,} errors",
        "log_operation_cancelled": "Operació cancel·lada per l'usuari",
        "log_pending_files": "Pendents: {count:,} arxius ({size})",
        
        # Errores
        "error_select_source": "Si us plau, seleccioneu una carpeta d'origen",
        "error_select_destination": "Si us plau, seleccioneu una carpeta de destí",
        "error_source_not_exists": "La carpeta d'origen no existeix",
        "error_same_paths": "Les carpetes d'origen i destí no poden ser iguals",
        "error_destination_inside_source": "La carpeta de destí no pot estar dins de l'origen",
        "error_insufficient_space": (
            "⚠️ Espai insuficient al destí\n\n"
            "Espai disponible: {available}\n"
            "Espai requerit: {required}\n\n"
            "Voleu continuar igualment?"
        ),
        
        # Footer
        "footer_destination_space": "Espai al destí: {free} lliures de {total}",
        "footer_space_unknown": "Espai al destí: --",
        
        # Idiomas
        "lang_es": "Español",
        "lang_ca": "Català",
        "lang_en": "English",
    },
    
    "en": {
        # App info
        "app_subtitle": "Secure copy of large data volumes with SHA256 verification",
        
        # Secciones
        "section_source": "📁 Source Folder:",
        "section_destination": "💾 Destination Folder:",
        "placeholder_source": "Select source folder...",
        "placeholder_destination": "Select destination folder (external drive)...",
        "btn_browse": "Browse",
        
        # Botones principales
        "btn_scan": "🔍 1. Scan Source",
        "btn_start_copy": "📋 2. Start Copy",
        "btn_continue_copy": "📋 2. Continue Copy",
        "btn_pause": "⏸️ Pause",
        "btn_resume": "▶️ Resume",
        "btn_cancel": "❌ Cancel",
        "btn_verify": "✅ 3. Verify Copy",
        
        # Progreso
        "progress_ready": "Ready to start",
        "progress_session_resumed": "Session resumed - Ready to continue",
        "progress_scanning": "Scanning...",
        "progress_copying": "Copying...",
        "progress_verifying": "Verifying...",
        "progress_completed": "Completed!",
        "progress_paused": "Paused",
        "progress_cancelled": "Cancelled",
        "progress_files": "📄 {current} / {total}",
        "progress_size": "Size: {current} / {total}",
        "progress_errors": "Errors: {count}",
        "progress_speed": "Speed: {speed}",
        "progress_time": "Time: {time}",
        "progress_remaining": "Remaining: {time}",
        
        # Diálogos
        "dialog_pending_session_title": "Pending session detected",
        "dialog_pending_session_message": (
            "An incomplete backup session was found:\n\n"
            "📁 Source: {source}\n"
            "💾 Destination: {destination}\n"
            "📊 Status: {status}\n"
            "📅 Last activity: {last_activity}\n\n"
            "Progress: {copied:,} of {total:,} files ({percentage:.1f}%)\n"
            "({pending:,} files pending)\n\n"
            "Do you want to RESUME this session?\n\n"
            "• Yes = Resume where you left off\n"
            "• No = Ignore and start over\n"
            "• Cancel = Close application"
        ),
        "dialog_session_found_title": "Session found",
        "dialog_session_found_message": (
            "A previous session with these paths was found:\n\n"
            "📁 Source: {source}\n"
            "💾 Destination: {destination}\n\n"
            "Progress: {copied:,} of {total:,} files copied\n"
            "({pending:,} pending)\n\n"
            "Do you want to CONTINUE the previous session?\n\n"
            "• Yes = Continue where you left off\n"
            "• No = Create new session (start from scratch)\n"
            "• Cancel = Do nothing"
        ),
        "dialog_operation_in_progress_title": "Operation in Progress",
        "dialog_operation_in_progress_message": (
            "An operation is in progress.\n\n"
            "Do you want to cancel it and close the application?\n"
            "Progress will be saved and you can continue later."
        ),
        "dialog_cancel_title": "Confirm Cancellation",
        "dialog_cancel_message": (
            "Are you sure you want to cancel?\n"
            "Progress will be saved and you can continue later."
        ),
        "dialog_verify_title": "Post-Copy Verification",
        "dialog_verify_message": (
            "Hashes of {count:,} copied files will be verified.\n\n"
            "This may take a considerable amount of time.\n"
            "Do you want to continue?"
        ),
        "dialog_scan_complete_title": "Scan Complete",
        "dialog_scan_complete_message": (
            "Found {files:,} files ({size})\n"
            "in {folders:,} folders.\n\n"
            "Click 'Start Copy' to continue."
        ),
        "dialog_copy_complete_title": "Copy Completed",
        "dialog_copy_complete_message": (
            "Copy completed successfully!\n\n"
            "📊 Summary:\n"
            "• Files copied: {copied:,}\n"
            "• Files skipped: {skipped:,}\n"
            "• Errors: {errors:,}\n"
            "• Total time: {time}\n\n"
            "It is recommended to run verification to confirm integrity."
        ),
        
        # Log
        "log_title": "📜 Activity Log:",
        "log_session_created": "Session created: {name} (ID: {id})",
        "log_session_resumed": "Resuming previous session (ID: {id}) - {copied:,} files already copied",
        "log_session_deleted": "Previous session deleted. Creating new...",
        "log_scan_starting": "Starting scan of: {path}",
        "log_scan_complete": "Scan complete: {files:,} files, {size}",
        "log_copy_starting": "Starting copy of {count:,} files",
        "log_copy_complete": "Copy complete: {copied:,} files copied",
        "log_verify_starting": "Starting verification of {count:,} files",
        "log_verify_complete": "Verification complete: {verified:,} verified, {errors:,} errors",
        "log_operation_cancelled": "Operation cancelled by user",
        "log_pending_files": "Pending: {count:,} files ({size})",
        
        # Errores
        "error_select_source": "Please select a source folder",
        "error_select_destination": "Please select a destination folder",
        "error_source_not_exists": "Source folder does not exist",
        "error_same_paths": "Source and destination folders cannot be the same",
        "error_destination_inside_source": "Destination folder cannot be inside the source",
        "error_insufficient_space": (
            "⚠️ Insufficient space at destination\n\n"
            "Available space: {available}\n"
            "Required space: {required}\n\n"
            "Do you want to continue anyway?"
        ),
        
        # Footer
        "footer_destination_space": "Destination space: {free} free of {total}",
        "footer_space_unknown": "Destination space: --",
        
        # Idiomas
        "lang_es": "Español",
        "lang_ca": "Català",
        "lang_en": "English",
    },
}


class I18n:
    """Gestor de internacionalización."""
    
    _instance = None
    _language = DEFAULT_LANGUAGE
    _observers = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'I18n':
        """Obtiene la instancia singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @property
    def language(self) -> str:
        """Obtiene el idioma actual."""
        return self._language
    
    @language.setter
    def language(self, lang: str):
        """Establece el idioma y notifica a los observadores."""
        if lang in TRANSLATIONS:
            self._language = lang
            self._notify_observers()
    
    def get(self, key: str, **kwargs) -> str:
        """
        Obtiene una traducción.
        
        Args:
            key: Clave de la traducción
            **kwargs: Parámetros para formatear el texto
            
        Returns:
            Texto traducido, o la clave si no existe
        """
        translations = TRANSLATIONS.get(self._language, TRANSLATIONS[DEFAULT_LANGUAGE])
        text = translations.get(key, key)
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass  # Si falla el formateo, devolver texto sin formato
        
        return text
    
    def add_observer(self, callback):
        """Añade un observador que será notificado al cambiar de idioma."""
        if callback not in self._observers:
            self._observers.append(callback)
    
    def remove_observer(self, callback):
        """Elimina un observador."""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self):
        """Notifica a todos los observadores del cambio de idioma."""
        for callback in self._observers:
            try:
                callback()
            except Exception:
                pass
    
    @staticmethod
    def get_available_languages() -> list:
        """Obtiene la lista de idiomas disponibles."""
        return list(TRANSLATIONS.keys())


# Función de conveniencia para acceso rápido
def t(key: str, **kwargs) -> str:
    """Función de traducción rápida."""
    return I18n.get_instance().get(key, **kwargs)


def get_i18n() -> I18n:
    """Obtiene la instancia del gestor de i18n."""
    return I18n.get_instance()
