"""Script temporal para verificar la sesión"""
from database import Database

db = Database()
sesiones = db.obtener_todas_sesiones()
s = sesiones[0]
print(f"Última sesión ID: {s['id']}")
print(f"Nombre: {s['nombre']}")
print(f"Estado: {s['estado']}")

stats = db.obtener_estadisticas_sesion(s['id'])
print(f"\nEstadísticas:")
for k, v in stats.items():
    print(f"  {k}: {v}")

# Buscar archivos con problemas
with db._get_connection() as conn:
    cursor = conn.cursor()
    
    # Archivos omitidos
    cursor.execute("SELECT COUNT(*) FROM archivos WHERE sesion_id = ? AND estado = 'OMITIDO'", (s['id'],))
    omitidos = cursor.fetchone()[0]
    print(f"\nArchivos omitidos: {omitidos}")
    
    # Archivos con error
    cursor.execute("SELECT COUNT(*) FROM archivos WHERE sesion_id = ? AND estado = 'ERROR'", (s['id'],))
    errores = cursor.fetchone()[0]
    print(f"Archivos con error: {errores}")
    
    # Archivos pendientes
    cursor.execute("SELECT COUNT(*) FROM archivos WHERE sesion_id = ? AND estado = 'PENDIENTE'", (s['id'],))
    pendientes = cursor.fetchone()[0]
    print(f"Archivos pendientes: {pendientes}")
    
    # Archivos completados
    cursor.execute("SELECT COUNT(*) FROM archivos WHERE sesion_id = ? AND estado = 'COMPLETADO'", (s['id'],))
    completados = cursor.fetchone()[0]
    print(f"Archivos completados: {completados}")
    
    # Total
    cursor.execute("SELECT COUNT(*) FROM archivos WHERE sesion_id = ?", (s['id'],))
    total = cursor.fetchone()[0]
    print(f"Total archivos en DB: {total}")
    
    # Si hay omitidos o errores, mostrar cuáles
    if omitidos > 0:
        print("\n--- Archivos omitidos ---")
        cursor.execute("SELECT ruta_origen, error_mensaje FROM archivos WHERE sesion_id = ? AND estado = 'OMITIDO' LIMIT 10", (s['id'],))
        for row in cursor.fetchall():
            print(f"  {row[0]} - {row[1]}")
    
    if errores > 0:
        print("\n--- Archivos con error ---")
        cursor.execute("SELECT ruta_origen, error_mensaje FROM archivos WHERE sesion_id = ? AND estado = 'ERROR' LIMIT 10", (s['id'],))
        for row in cursor.fetchall():
            print(f"  {row[0]} - {row[1]}")
    
    if pendientes > 0:
        print("\n--- Archivos pendientes (primeros 10) ---")
        cursor.execute("SELECT ruta_origen FROM archivos WHERE sesion_id = ? AND estado = 'PENDIENTE' LIMIT 10", (s['id'],))
        for row in cursor.fetchall():
            print(f"  {row[0]}")
