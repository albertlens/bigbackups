# BigBackups 🗂️

**Aplicación profesional de copia segura para grandes volúmenes de datos con verificación SHA256**

Diseñada para copiar carpetas con miles de archivos y subcarpetas desde cualquier origen (disco local, OneDrive, carpeta de red) a un disco externo, garantizando la integridad de cada archivo mediante verificación criptográfica.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🎯 Caso de uso

Esta herramienta está pensada para:
- Empresas que necesitan que sus clientes copien grandes volúmenes de información a discos externos
- Backups de carpetas OneDrive sincronizadas
- Copias de seguridad desde servidores de red locales
- Cualquier situación donde se requiera una copia **verificada** y **fiable** de cientos de GB

## ✨ Características principales

| Característica | Descripción |
|----------------|-------------|
| 🔍 **Escaneo completo** | Cataloga todos los archivos en SQLite antes de copiar |
| 🔐 **Verificación SHA256** | Cada archivo copiado se verifica con hash criptográfico |
| 📁 **Soporte rutas largas** | Maneja rutas de más de 260 caracteres en Windows |
| ☁️ **Detección OneDrive** | Identifica archivos que están solo en la nube (no descargados) |
| 🔄 **Sistema de reintentos** | Backoff exponencial ante fallos temporales de red/disco |
| ⏸️ **Pausar/Reanudar** | Continúa copias interrumpidas desde donde quedaron |
| 📋 **Log completo** | Registro detallado de todas las operaciones en DB |
| 📊 **Progreso en tiempo real** | Velocidad, tiempo restante, archivos procesados |
| 💾 **EXE standalone** | No requiere Python instalado en el equipo del cliente |

---

## 🖥️ Interfaz

La aplicación cuenta con una GUI moderna y profesional:

- Selección de carpeta origen y destino con explorador
- Indicador de espacio disponible en disco destino
- Barra de progreso con porcentaje y estadísticas
- Log de eventos en tiempo real
- Botones de pausar/cancelar operación

---

## 📦 Instalación para desarrollo

### Requisitos
- Python 3.11 o superior
- Windows 10/11

### Dependencias

```bash
pip install -r requirements.txt
```

Las dependencias son mínimas:
- `customtkinter` - GUI moderna
- `pillow` - Soporte de imágenes para CustomTkinter
- `pyinstaller` - Generación de ejecutable (solo para build)

---

## 🚀 Uso

### Modo desarrollo

```bash
python main.py
```

### Generar ejecutable (.exe)

**Opción 1: Script automatizado**
```batch
build.bat
```

**Opción 2: Manual**
```bash
pip install pyinstaller
pyinstaller bigbackups.spec --noconfirm
```

El ejecutable se genera en `dist/BigBackups.exe` (~30-50MB, standalone)

---

## 📖 Flujo de uso

```
┌─────────────────────────────────────────────────────┐
│  1. SELECCIONAR ORIGEN                              │
│     → Carpeta local, OneDrive o ruta de red         │
├─────────────────────────────────────────────────────┤
│  2. SELECCIONAR DESTINO                             │
│     → Disco externo USB, NAS, otra carpeta          │
├─────────────────────────────────────────────────────┤
│  3. ESCANEAR                                        │
│     → Cataloga archivos en SQLite (muy rápido)      │
│     → Muestra total de archivos y tamaño            │
├─────────────────────────────────────────────────────┤
│  4. COPIAR                                          │
│     → Crea estructura de carpetas                   │
│     → Copia cada archivo calculando SHA256          │
│     → Verifica hash del archivo copiado             │
│     → Puede pausarse y reanudarse                   │
├─────────────────────────────────────────────────────┤
│  5. VERIFICACIÓN                                    │
│     → Todos los archivos verificados con SHA256     │
│     → Errores registrados en log                    │
│     → Resumen final de la operación                 │
└─────────────────────────────────────────────────────┘
```

---

## 🗄️ Estructura del proyecto

```
bigbackups/
├── main.py              # Punto de entrada de la aplicación
├── gui.py               # Interfaz gráfica (CustomTkinter)
├── database.py          # Gestión de SQLite (sesiones, archivos, log)
├── scanner.py           # Escaneo recursivo de directorios
├── copier.py            # Copia con verificación SHA256
├── utils.py             # Utilidades (hash, formato, detección OneDrive)
├── config.py            # Configuración global
├── requirements.txt     # Dependencias Python
├── bigbackups.spec      # Configuración de PyInstaller
├── build.bat            # Script de construcción del EXE
└── README.md            # Esta documentación
```

---

## 🗃️ Base de datos

La aplicación crea `bigbackups.db` junto al ejecutable con las siguientes tablas:

### Tabla `sesiones`
Información de cada trabajo de backup:
- Rutas origen/destino
- Estado (escaneando, copiando, completada, etc.)
- Estadísticas totales
- Fechas de inicio/fin

### Tabla `archivos`
Catálogo completo de archivos:
- Ruta origen y destino
- Nombre, extensión, tamaño
- Hash SHA256 origen y destino
- Estado (pendiente, copiando, verificado, error)
- Número de intentos
- Mensaje de error si aplica

### Tabla `carpetas`
Estructura de directorios a replicar

### Tabla `log_eventos`
Registro cronológico de todas las operaciones

---

## ⚙️ Configuración

El archivo `config.py` permite personalizar:

```python
# Algoritmo de hash
HASH_ALGORITHM = "sha256"  # Opciones: "md5", "sha256"

# Reintentos
MAX_RETRIES = 5
RETRY_DELAY_BASE = 2  # Segundos (backoff exponencial)

# Archivos excluidos
EXCLUDED_FILES = {"thumbs.db", "desktop.ini", ".ds_store", ...}

# Carpetas excluidas
EXCLUDED_FOLDERS = {"$recycle.bin", "system volume information", ...}
```

---

## 🛡️ Manejo de errores

| Situación | Comportamiento |
|-----------|----------------|
| Archivo bloqueado | Reintentos automáticos con espera exponencial |
| Espacio insuficiente | Alerta antes de iniciar la copia |
| Rutas muy largas | Soporte nativo con prefijo `\\?\` |
| Archivos OneDrive en nube | Se marcan como omitidos con aviso |
| Hash no coincide | Se elimina y reintenta la copia |
| Error de red | Reintentos con backoff exponencial |

---

## 📊 Rendimiento esperado

Para una copia de ~1TB con 1 millón de archivos:

| Fase | Tiempo estimado |
|------|-----------------|
| Escaneo | 5-15 minutos |
| Copia + SHA256 | 4-7 horas (depende de velocidad de discos) |

El cuello de botella es siempre la velocidad del disco, no el cálculo de hash.

---

## 🔧 Notas técnicas

- El hash SHA256 se calcula **durante** la copia (una sola lectura del archivo)
- Las inserciones en SQLite usan batch de 500 registros para rendimiento
- Compatible con rutas UNC (carpetas de red)
- SQLite usa modo WAL (Write-Ahead Logging) para mejor rendimiento
- Soporte completo de rutas largas de Windows (+260 caracteres)

---

## 📄 Licencia

MIT License - Libre para uso personal y comercial.

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir cambios mayores antes de enviar un PR.

---

**Desarrollado con ❤️ para facilitar backups seguros y verificables**
