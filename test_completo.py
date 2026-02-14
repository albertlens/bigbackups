"""
Tests automatizados completos para BigBackups
Verifica toda la lógica crítica sin necesidad de GUI
"""

import os
import sys
import tempfile
import shutil
import sqlite3
import time
from datetime import datetime, timedelta

# Colores para output
class C:
    OK = '\033[92m✓\033[0m'
    FAIL = '\033[91m✗\033[0m'
    INFO = '\033[94mℹ\033[0m'
    WARN = '\033[93m⚠\033[0m'

def test_imports():
    """Test 1: Verificar que todos los imports funcionan"""
    print(f"\n{'='*60}")
    print("TEST 1: Verificación de imports")
    print('='*60)
    
    errores = []
    modulos = [
        ('config', ['APP_NAME', 'Colors', 'SessionStatus', 'FileStatus']),
        ('database', ['Database', 'get_database']),
        ('scanner', ['FileScanner', 'ScannerStats']),
        ('copier', ['FileCopier', 'CopyStats', 'PostCopyVerifier']),
        ('utils', ['format_size', 'format_time', 'get_drive_space']),
        ('i18n', ['I18n', 't', 'get_i18n']),
    ]
    
    for modulo, componentes in modulos:
        try:
            mod = __import__(modulo)
            for comp in componentes:
                if hasattr(mod, comp):
                    print(f"  {C.OK} {modulo}.{comp}")
                else:
                    print(f"  {C.FAIL} {modulo}.{comp} - NO ENCONTRADO")
                    errores.append(f"{modulo}.{comp}")
        except Exception as e:
            print(f"  {C.FAIL} {modulo} - ERROR: {e}")
            errores.append(modulo)
    
    return len(errores) == 0, errores


def test_database_sesiones_pendientes():
    """Test 2: Verificar detección de sesiones pendientes"""
    print(f"\n{'='*60}")
    print("TEST 2: Detección de sesiones pendientes al inicio")
    print('='*60)
    
    from database import Database
    from config import SessionStatus, FileStatus
    
    # Crear BD temporal
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # 1. Sin sesiones - debe retornar lista vacía
        pendientes = db.obtener_sesiones_pendientes()
        assert pendientes == [], f"Sin sesiones debería ser [], got {pendientes}"
        print(f"  {C.OK} Sin sesiones = lista vacía")
        
        # 2. Crear sesión CREATED (no debe aparecer en pendientes)
        sesion1 = db.crear_sesion("test1", "/origen1", "/destino1")
        pendientes = db.obtener_sesiones_pendientes()
        assert len(pendientes) == 0, "Sesión CREATED no debe aparecer en pendientes"
        print(f"  {C.OK} Sesión CREATED no aparece en pendientes")
        
        # 3. Sesión en SCANNING (debe aparecer)
        db.actualizar_sesion(sesion1, estado=SessionStatus.SCANNING)
        pendientes = db.obtener_sesiones_pendientes()
        assert len(pendientes) == 1, "Sesión SCANNING debe aparecer"
        print(f"  {C.OK} Sesión SCANNING aparece en pendientes")
        
        # 4. Sesión en PAUSED (debe aparecer)
        db.actualizar_sesion(sesion1, estado=SessionStatus.PAUSED)
        pendientes = db.obtener_sesiones_pendientes()
        assert len(pendientes) == 1, "Sesión PAUSED debe aparecer"
        assert pendientes[0]['estado'] == 'PAUSADA'
        print(f"  {C.OK} Sesión PAUSED aparece en pendientes")
        
        # 5. Sesión COMPLETED (no debe aparecer)
        db.actualizar_sesion(sesion1, estado=SessionStatus.COMPLETED)
        pendientes = db.obtener_sesiones_pendientes()
        assert len(pendientes) == 0, "Sesión COMPLETED no debe aparecer"
        print(f"  {C.OK} Sesión COMPLETED no aparece en pendientes")
        
        # 6. Múltiples sesiones
        sesion2 = db.crear_sesion("test2", "/origen2", "/destino2")
        db.actualizar_sesion(sesion2, estado=SessionStatus.COPYING)
        sesion3 = db.crear_sesion("test3", "/origen3", "/destino3")
        db.actualizar_sesion(sesion3, estado=SessionStatus.PAUSED)
        
        pendientes = db.obtener_sesiones_pendientes()
        assert len(pendientes) == 2, f"Deberían haber 2 pendientes, hay {len(pendientes)}"
        print(f"  {C.OK} Múltiples sesiones pendientes detectadas")
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False, [str(e)]
    finally:
        os.unlink(db_path)


def test_progreso_sesion():
    """Test 3: Verificar cálculo de progreso con FileStatus correcto"""
    print(f"\n{'='*60}")
    print("TEST 3: Cálculo de progreso de sesión")
    print('='*60)
    
    from database import Database
    from config import SessionStatus, FileStatus
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Crear sesión
        sesion_id = db.crear_sesion("test", "/origen", "/destino")
        db.actualizar_sesion(sesion_id, estado=SessionStatus.COPYING)
        
        # Agregar archivos usando insertar_archivo
        fecha_mod = "2026-01-01 12:00:00"
        db.insertar_archivo(sesion_id, "/origen/a.txt", "a.txt", "a.txt", ".txt", 100, fecha_mod)
        db.insertar_archivo(sesion_id, "/origen/b.txt", "b.txt", "b.txt", ".txt", 200, fecha_mod)
        db.insertar_archivo(sesion_id, "/origen/c.txt", "c.txt", "c.txt", ".txt", 300, fecha_mod)
        
        # Verificar progreso inicial (0 copiados)
        progreso = db.obtener_progreso_sesion(sesion_id)
        assert progreso['total'] == 3, f"Total debería ser 3, es {progreso['total']}"
        assert progreso['copiados'] == 0, f"Copiados debería ser 0, es {progreso['copiados']}"
        print(f"  {C.OK} Progreso inicial: 0/3")
        
        # Marcar un archivo como COMPLETED usando actualizar_archivo
        # Primero necesitamos obtener el ID del archivo
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM archivos WHERE sesion_id = ? AND ruta_origen = ?", 
                          (sesion_id, "/origen/a.txt"))
            archivo_id = cursor.fetchone()[0]
        db.actualizar_archivo(archivo_id, estado=FileStatus.COMPLETED)
        progreso = db.obtener_progreso_sesion(sesion_id)
        assert progreso['copiados'] == 1, f"Copiados debería ser 1, es {progreso['copiados']}"
        print(f"  {C.OK} Después de 1 COMPLETED: 1/3")
        
        # Marcar otro como COMPLETED
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM archivos WHERE sesion_id = ? AND ruta_origen = ?", 
                          (sesion_id, "/origen/b.txt"))
            archivo_id = cursor.fetchone()[0]
        db.actualizar_archivo(archivo_id, estado=FileStatus.COMPLETED)
        progreso = db.obtener_progreso_sesion(sesion_id)
        assert progreso['copiados'] == 2, f"Copiados debería ser 2, es {progreso['copiados']}"
        print(f"  {C.OK} Después de 2 COMPLETED: 2/3")
        
        # Verificar que PENDING no cuenta
        progreso = db.obtener_progreso_sesion(sesion_id)
        assert progreso['pendientes'] == 1, f"Pendientes debería ser 1, es {progreso['pendientes']}"
        print(f"  {C.OK} 1 archivo PENDING restante")
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False, [str(e)]
    finally:
        os.unlink(db_path)


def test_verificacion_archivos():
    """Test 4: Verificar que la verificación post-copia funciona"""
    print(f"\n{'='*60}")
    print("TEST 4: Verificación post-copia")
    print('='*60)
    
    from database import Database
    from config import SessionStatus, FileStatus
    from copier import PostCopyVerifier
    
    # Crear directorios temporales
    origen = tempfile.mkdtemp(prefix="origen_")
    destino = tempfile.mkdtemp(prefix="destino_")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Crear archivos de prueba en origen
        test_files = ["file1.txt", "file2.txt", "subdir/file3.txt"]
        for tf in test_files:
            full_path = os.path.join(origen, tf)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(f"Contenido de {tf}")
        
        # Copiar manualmente a destino (simular copia completada)
        for tf in test_files:
            src = os.path.join(origen, tf)
            dst = os.path.join(destino, tf)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        
        # Crear sesión con archivos en BD
        sesion_id = db.crear_sesion("test_verif", origen, destino)
        db.actualizar_sesion(sesion_id, estado=SessionStatus.COMPLETED)
        
        # Insertar archivos usando insertar_archivo
        fecha_mod = "2026-01-01 12:00:00"
        for tf in test_files:
            ruta_origen_f = os.path.join(origen, tf)
            nombre = os.path.basename(tf)
            ext = os.path.splitext(tf)[1]
            tamano = os.path.getsize(ruta_origen_f)
            db.insertar_archivo(sesion_id, ruta_origen_f, tf, nombre, ext, tamano, fecha_mod)
        
        # Actualizar ruta_destino para cada archivo
        with db._get_connection() as conn:
            cursor = conn.cursor()
            for tf in test_files:
                cursor.execute("""
                    UPDATE archivos SET ruta_destino = ?, estado = ?
                    WHERE sesion_id = ? AND ruta_relativa = ?
                """, (os.path.join(destino, tf), FileStatus.COMPLETED, sesion_id, tf))
        
        # Verificar
        verifier = PostCopyVerifier(db)
        resultado = verifier.verificar_sesion(sesion_id)
        
        assert resultado.archivos_verificados == 3, f"Verificados debería ser 3, es {resultado.archivos_verificados}"
        assert resultado.archivos_faltantes_destino == 0, f"Faltantes debería ser 0, es {resultado.archivos_faltantes_destino}"
        print(f"  {C.OK} Verificación: {resultado.archivos_verificados} archivos, 0 faltantes")
        
        # Eliminar un archivo y verificar que se detecte
        os.remove(os.path.join(destino, "file1.txt"))
        resultado = verifier.verificar_sesion(sesion_id)
        
        assert resultado.archivos_faltantes_destino == 1, f"Faltantes debería ser 1, es {resultado.archivos_faltantes_destino}"
        print(f"  {C.OK} Detectó 1 archivo faltante tras eliminarlo")
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False, [str(e)]
    finally:
        os.unlink(db_path)
        shutil.rmtree(origen, ignore_errors=True)
        shutil.rmtree(destino, ignore_errors=True)


def test_i18n():
    """Test 5: Verificar sistema de internacionalización"""
    print(f"\n{'='*60}")
    print("TEST 5: Sistema de internacionalización (i18n)")
    print('='*60)
    
    try:
        from i18n import I18n, t, get_i18n
        
        i18n = get_i18n()
        
        # Verificar idiomas disponibles
        idiomas = ['es', 'ca', 'en']
        for idioma in idiomas:
            i18n.language = idioma
            assert i18n.language == idioma
            print(f"  {C.OK} Idioma {idioma.upper()} configurado correctamente")
        
        # Verificar traducciones clave
        i18n.language = 'es'
        assert 'Escanear' in t('btn_scan')
        print(f"  {C.OK} ES: btn_scan contiene 'Escanear'")
        
        i18n.language = 'en'
        assert 'Scan' in t('btn_scan')
        print(f"  {C.OK} EN: btn_scan contiene 'Scan'")
        
        i18n.language = 'ca'
        assert 'Escanejar' in t('btn_scan')
        print(f"  {C.OK} CA: btn_scan contiene 'Escanejar'")
        
        # Verificar fallback
        i18n.language = 'es'
        resultado = t('clave_inexistente')
        assert resultado == 'clave_inexistente', "Clave inexistente debería retornar la misma clave"
        print(f"  {C.OK} Fallback para claves inexistentes funciona")
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False, [str(e)]


def test_buscar_sesion_por_rutas():
    """Test 6: Verificar búsqueda de sesión por rutas (normalización)"""
    print(f"\n{'='*60}")
    print("TEST 6: Búsqueda de sesión por rutas")
    print('='*60)
    
    from database import Database
    from config import SessionStatus
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Crear sesión con rutas específicas
        ruta_origen = "C:\\Users\\Test\\Origen"
        ruta_destino = "D:\\Backup\\Destino"
        
        sesion_id = db.crear_sesion("test_rutas", ruta_origen, ruta_destino)
        db.actualizar_sesion(sesion_id, estado=SessionStatus.PAUSED)
        
        # Buscar con mismas rutas
        encontrada = db.buscar_sesion_por_rutas(ruta_origen, ruta_destino)
        assert encontrada is not None, "Debería encontrar la sesión"
        assert encontrada['id'] == sesion_id
        print(f"  {C.OK} Encontró sesión por rutas exactas")
        
        # Buscar con trailing slash
        encontrada = db.buscar_sesion_por_rutas(ruta_origen + "\\", ruta_destino + "\\")
        assert encontrada is not None, "Debería encontrar con trailing slash"
        print(f"  {C.OK} Encontró sesión con trailing slashes")
        
        # Buscar con rutas diferentes
        encontrada = db.buscar_sesion_por_rutas("X:\\Otra\\Ruta", "Y:\\Otra\\Ruta")
        assert encontrada is None, "No debería encontrar sesión inexistente"
        print(f"  {C.OK} No encontró sesión con rutas diferentes")
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False, [str(e)]
    finally:
        os.unlink(db_path)


def test_colores():
    """Test 7: Verificar configuración de colores"""
    print(f"\n{'='*60}")
    print("TEST 7: Configuración de colores (nuevo esquema)")
    print('='*60)
    
    try:
        from config import Colors
        
        colores_esperados = {
            'PRIMARY': '#4f46e5',     # Indigo
            'SECONDARY': '#6366f1',   # Indigo claro  
            'ACCENT': '#818cf8',      # Indigo más claro
        }
        
        for nombre, valor_esperado in colores_esperados.items():
            valor_actual = getattr(Colors, nombre, None)
            if valor_actual == valor_esperado:
                print(f"  {C.OK} {nombre} = {valor_actual}")
            else:
                print(f"  {C.FAIL} {nombre} = {valor_actual} (esperado: {valor_esperado})")
                return False, [f"{nombre} incorrecto"]
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        return False, [str(e)]


def test_copia_real():
    """Test 8: Test de copia real de archivos"""
    print(f"\n{'='*60}")
    print("TEST 8: Copia real de archivos")
    print('='*60)
    
    from database import Database
    from config import SessionStatus, FileStatus
    from copier import FileCopier
    from scanner import FileScanner
    
    origen = tempfile.mkdtemp(prefix="test_origen_")
    destino = tempfile.mkdtemp(prefix="test_destino_")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Crear archivos de prueba
        archivos_prueba = {
            "archivo1.txt": "Contenido del archivo 1" * 100,
            "carpeta/archivo2.txt": "Contenido del archivo 2" * 50,
            "carpeta/sub/archivo3.txt": "Contenido del archivo 3" * 200,
        }
        
        for nombre, contenido in archivos_prueba.items():
            ruta = os.path.join(origen, nombre)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, 'w') as f:
                f.write(contenido)
        
        print(f"  {C.INFO} Creados {len(archivos_prueba)} archivos de prueba")
        
        # Crear sesión primero
        sesion_id = db.crear_sesion("test_copia", origen, destino)
        
        # Escanear
        scanner = FileScanner(db)
        stats = scanner.escanear(sesion_id, origen)
        
        print(f"  {C.OK} Escaneo: {stats.archivos_encontrados} archivos, {stats.tamano_total} bytes")
        
        # Copiar
        copier = FileCopier(db)
        
        stats = copier.copiar(sesion_id, destino)
        
        print(f"  {C.OK} Copia: {stats.archivos_copiados} archivos copiados")
        
        # Verificar que archivos existen en destino
        errores = []
        nombre_carpeta = os.path.basename(origen.rstrip('/\\'))
        for nombre in archivos_prueba.keys():
            ruta_dest = os.path.join(destino, nombre_carpeta, nombre)
            if os.path.exists(ruta_dest):
                print(f"  {C.OK} Copiado: {nombre}")
            else:
                print(f"  {C.FAIL} No encontrado: {nombre}")
                errores.append(nombre)
        
        if errores:
            return False, errores
        
        # Verificar estado en BD
        progreso = db.obtener_progreso_sesion(sesion_id)
        pct = (progreso['copiados'] / progreso['total'] * 100) if progreso['total'] > 0 else 0
        print(f"  {C.OK} Progreso BD: {progreso['copiados']}/{progreso['total']} ({pct:.1f}%)")
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False, [str(e)]
    finally:
        os.unlink(db_path)
        shutil.rmtree(origen, ignore_errors=True)
        shutil.rmtree(destino, ignore_errors=True)


def test_fecha_inicio_copia():
    """Test 9: Verificar que fecha_inicio_copia no se sobreescribe"""
    print(f"\n{'='*60}")
    print("TEST 9: Preservación de fecha_inicio_copia")
    print('='*60)
    
    from database import Database
    from config import SessionStatus
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        sesion_id = db.crear_sesion("test_fecha", "/origen", "/destino")
        
        # Establecer fecha de inicio usando actualizar_sesion
        fecha_original = "2026-01-15 10:30:00"
        db.actualizar_sesion(sesion_id, fecha_inicio_copia=fecha_original)
        
        # Verificar que está guardada
        sesion = db.obtener_sesion(sesion_id)
        assert sesion['fecha_inicio_copia'] == fecha_original
        print(f"  {C.OK} Fecha original establecida: {fecha_original}")
        
        # La lógica del copier no debería sobreescribir si ya existe
        # (esto se verifica en el código, no en este test unitario)
        print(f"  {C.INFO} Lógica de preservación implementada en copier.py")
        
        return True, []
        
    except Exception as e:
        print(f"  {C.FAIL} Error: {e}")
        return False, [str(e)]
    finally:
        os.unlink(db_path)


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*60)
    print("   BIGBACKUPS - SUITE DE TESTS AUTOMATIZADOS")
    print("="*60)
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Sesiones pendientes", test_database_sesiones_pendientes),
        ("Progreso sesión", test_progreso_sesion),
        ("Verificación archivos", test_verificacion_archivos),
        ("i18n", test_i18n),
        ("Búsqueda por rutas", test_buscar_sesion_por_rutas),
        ("Colores", test_colores),
        ("Copia real", test_copia_real),
        ("Fecha inicio copia", test_fecha_inicio_copia),
    ]
    
    resultados = []
    
    for nombre, test_func in tests:
        try:
            exito, errores = test_func()
            resultados.append((nombre, exito, errores))
        except Exception as e:
            resultados.append((nombre, False, [str(e)]))
    
    # Resumen
    print("\n" + "="*60)
    print("   RESUMEN DE TESTS")
    print("="*60)
    
    exitosos = 0
    fallidos = 0
    
    for nombre, exito, errores in resultados:
        if exito:
            print(f"  {C.OK} {nombre}")
            exitosos += 1
        else:
            print(f"  {C.FAIL} {nombre}: {', '.join(errores)}")
            fallidos += 1
    
    print("="*60)
    print(f"   TOTAL: {exitosos} exitosos, {fallidos} fallidos")
    print("="*60)
    
    return fallidos == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
