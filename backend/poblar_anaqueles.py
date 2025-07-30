import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root', # usuario de MySQL
    'password': '!!vcbm.Z@XJ5]aO[', #  contraseña
    'database': 'biblioteca_db'
}
# ---------------------

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Verificar si la tabla ya tiene datos para no duplicar
    cursor.execute("SELECT COUNT(*) FROM Anaqueles")
    if cursor.fetchone()[0] > 0:
        print("La tabla 'Anaqueles' ya contiene datos. No se realizaron cambios.")
    else:
        print("Poblando la tabla 'Anaqueles' con 24 registros...")
        for i in range(1, 25):
            nombre_anaquel = f"Anaquel {i:02d}"
            descripcion_anaquel = f"Sección general {i}"
            query = "INSERT INTO Anaqueles (nombre, descripcion) VALUES (%s, %s)"
            cursor.execute(query, (nombre_anaquel, descripcion_anaquel))
        
        conn.commit()
        print("="*50)
        print("¡24 anaqueles creados exitosamente!")
        print("="*50)

except mysql.connector.Error as err:
    print(f"Error al poblar la tabla: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()