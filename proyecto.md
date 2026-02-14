# BigBackups - Documentación del Proyecto

## Descripción General

**BigBackups** es una aplicación de escritorio para Windows que permite copiar grandes volúmenes de datos de manera robusta y reanudable. Su característica principal es la capacidad de **pausar y reanudar** copias en cualquier momento, incluso después de cerrar la aplicación, manteniendo el progreso exacto.

---

## Características Principales

### 1. Copia Reanudable
- **Detección automática de sesiones pendientes** al iniciar la aplicación
- Reanudación exacta desde el último archivo copiado
- Múltiples pausas/reanudaciones sin pérdida de progreso
- Tiempo total acumulado de todas las "tandas" de copia

### 2. Verificación Post-Copia
- Verificación SHA256 de integridad de archivos
- Comparación de tamaños
- Detección de archivos faltantes en destino
- Reporte detallado de discrepancias

### 3. Internacionalización (i18n)
- **Español** (ES) - Idioma por defecto
- **Català** (CA)
- **English** (EN)
- Cambio de idioma en tiempo real sin reiniciar

### 4. Interfaz Gráfica Moderna
- Tema oscuro con tonos índigo/azul
- Barra de progreso en tiempo real
- Log detallado de operaciones
- Indicadores de velocidad y tiempo restante

---

## Arquitectura del Proyecto

```
bigbackups/
├── main.py              # Punto de entrada
├── gui.py               # Interfaz gráfica (CustomTkinter)
├── database.py          # Gestión SQLite con WAL
├── scanner.py           # Escaneo de archivos
├── copier.py            # Motor de copia y verificación
├── config.py            # Configuración y constantes
├── utils.py             # Utilidades (formato, rutas)
├── i18n.py              # Sistema de traducciones
├── check_session.py     # Utilidad para verificar sesiones
├── bigbackups.spec      # Configuración PyInstaller
├── build.bat            # Script de compilación
├── requirements.txt     # Dependencias Python
└── assets/              # Iconos y recursos
    └── icon.ico
```

---

## Módulos Principales

### `database.py`
Base de datos SQLite con modo WAL para alta concurrencia.

**Tablas:**
- `sesiones` - Información de cada sesión de backup
- `archivos` - Catálogo de archivos a copiar
- `carpetas` - Estructura de directorios
- `logs` - Registro de eventos

**Métodos clave:**
- `crear_sesion()` - Nueva sesión de backup
- `obtener_sesiones_pendientes()` - Sesiones no completadas para reanudación
- `buscar_sesion_por_rutas()` - Busca sesión existente por origen/destino
- `obtener_progreso_sesion()` - Estadísticas de progreso

### `scanner.py`
Escaneo recursivo de directorios con detección de archivos en la nube.

**Características:**
- Soporte para rutas largas (>260 caracteres)
- Detección de archivos OneDrive/iCloud solo en nube
- Filtrado de extensiones y carpetas excluidas
- Inserción en batch para rendimiento

### `copier.py`
Motor de copia con verificación integrada.

**Características:**
- Copia con preservación de metadatos
- Cálculo de hash SHA256
- Verificación post-copia opcional
- Soporte para pausar/cancelar

### `i18n.py`
Sistema de internacionalización con patrón Singleton.

**Idiomas soportados:**
```python
TRANSLATIONS = {
    'es': { ... },  # Español
    'ca': { ... },  # Català
    'en': { ... },  # English
}
```

**Uso:**
```python
from i18n import t, get_i18n

# Obtener traducción
texto = t('btn_start_copy')  # "Iniciar Copia" / "Start Copy" / "Iniciar Còpia"

# Cambiar idioma
i18n = get_i18n()
i18n.language = 'ca'
```

---

## Estados de Sesión

| Estado | Descripción |
|--------|-------------|
| `CREADA` | Sesión creada, sin escanear |
| `ESCANEANDO` | Escaneo en progreso |
| `LISTA` | Escaneo completado, lista para copiar |
| `COPIANDO` | Copia en progreso |
| `PAUSADA` | Copia pausada por el usuario |
| `VERIFICANDO` | Verificación en progreso |
| `COMPLETADA` | Todo completado exitosamente |
| `ERROR` | Error durante el proceso |

---

## Estados de Archivo

| Estado | Descripción |
|--------|-------------|
| `PENDIENTE` | Archivo por copiar |
| `COPIANDO` | Copia en progreso |
| `VERIFICANDO` | Verificando integridad |
| `COMPLETADO` | Copiado y verificado |
| `ERROR` | Error durante copia |
| `OMITIDO` | Omitido (ej: solo en nube) |

---

## Correcciones Implementadas

### 1. Detección de Sesiones Pendientes al Inicio
**Problema:** Solo se detectaban sesiones al hacer clic en "Escanear" con las mismas rutas.

**Solución:** 
- Método `obtener_sesiones_pendientes()` que retorna sesiones con estado ≠ COMPLETADA y ≠ CREADA
- Verificación automática 500ms después de iniciar la GUI
- Diálogo preguntando si desea reanudar

### 2. Error FileStatus.COPIED
**Problema:** Se usaba `FileStatus.COPIED` que no existe.

**Solución:** Cambiado a `FileStatus.COMPLETED` en todo el código.

### 3. Verificación Post-Copia Incorrecta
**Problema:** Verificación reconstruía ruta destino incorrectamente, no encontraba archivos de tandas anteriores.

**Solución:** 
- Guardar `ruta_destino` explícitamente en BD al copiar
- Verificación usa `archivo['ruta_destino']` directamente

### 4. Tiempo Total Incorrecto
**Problema:** Solo mostraba tiempo de la última tanda, no el acumulado.

**Solución:**
- `fecha_inicio_copia` no se sobreescribe en reanudaciones
- Cálculo de tiempo desde `fecha_inicio_copia` de la sesión

### 5. Botón "Continuar Copia"
**Problema:** Botón siempre decía "Iniciar Copia".

**Solución:**
- Flag `_es_continuacion` para detectar reanudaciones
- Texto cambia a "Continuar Copia" cuando aplica
- Se resetea a "Iniciar Copia" al completar

---

## Esquema de Colores

```python
class Colors:
    # Colores principales (tonos índigo/azul)
    PRIMARY = "#4f46e5"        # Índigo - botón escanear
    PRIMARY_HOVER = "#4338ca"
    SECONDARY = "#6366f1"      # Índigo claro - botón copiar
    ACCENT = "#818cf8"         # Índigo suave - verificar
    
    # Colores de acción
    ACTION_PAUSE = "#64748b"   # Slate - pausar
    ACTION_CANCEL = "#94a3b8"  # Slate claro - cancelar
    
    # Colores de estado
    SUCCESS = "#22c55e"        # Verde
    WARNING = "#f59e0b"        # Ámbar
    ERROR = "#ef4444"          # Rojo
    INFO = "#3b82f6"           # Azul
```

---

## Compilación

### Requisitos
```
customtkinter>=5.2.0
Pillow>=10.0.0
pyinstaller>=6.0.0
```

### Generar EXE
```bash
python -m PyInstaller bigbackups.spec --noconfirm
```

El ejecutable se genera en `dist/BigBackups.exe` (~17MB).

---

## Tests Automatizados

Ejecutar suite completa:
```bash
python test_completo.py
```

**Tests incluidos:**
1. Verificación de imports
2. Detección de sesiones pendientes
3. Cálculo de progreso de sesión
4. Verificación post-copia
5. Sistema i18n
6. Búsqueda de sesión por rutas
7. Configuración de colores
8. Copia real de archivos
9. Preservación de fecha_inicio_copia

---

## Flujo de Uso

### Primera Copia
1. Seleccionar carpeta origen
2. Seleccionar carpeta destino
3. Click en "Escanear Origen"
4. Revisar estadísticas
5. Click en "Iniciar Copia"
6. (Opcional) Pausar/Reanudar
7. Verificar copia al finalizar

### Reanudar Copia
1. Abrir BigBackups
2. Aparece diálogo: "Sesión pendiente detectada"
3. Click en "Reanudar"
4. Continúa desde donde quedó

---

## Base de Datos

Ubicación: `bigbackups_data/bigbackups.db`

### Esquema Sesiones
```sql
CREATE TABLE sesiones (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    ruta_origen TEXT,
    ruta_destino TEXT,
    fecha_creacion TEXT,
    fecha_inicio_escaneo TEXT,
    fecha_fin_escaneo TEXT,
    fecha_inicio_copia TEXT,
    fecha_fin_copia TEXT,
    estado TEXT,
    total_archivos INTEGER,
    total_bytes INTEGER,
    archivos_copiados INTEGER,
    bytes_copiados INTEGER
);
```

---

## Changelog

### v1.0.0 (2026-02-14)
- ✅ Detección automática de sesiones pendientes al inicio
- ✅ Reanudación correcta con tiempo acumulado
- ✅ Verificación post-copia funcional
- ✅ Internacionalización ES/CA/EN
- ✅ Nuevo esquema de colores índigo/azul
- ✅ Suite de tests automatizados
- ✅ Compilación a EXE standalone

---

## Autor

Desarrollado con asistencia de GitHub Copilot (Claude Opus 4.5).

---

## Licencia

Uso interno.
