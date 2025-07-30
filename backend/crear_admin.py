from werkzeug.security import generate_password_hash
import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root', # usuario de MySQL
    'password': '!!vcbm.Z@XJ5]aO[', #  contraseña
    'database': 'biblioteca_db'
}

nombre_admin = "Administrador"
correo_admin = "admin@biblioteca.com"
contrasena_admin = "admin123"
# ---------------------

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Encriptar la contraseña
    contrasena_hash = generate_password_hash(contrasena_admin)

    # Insertar el nuevo usuario
    query = "INSERT INTO Usuarios (nombre, correo_electronico, contrasena_hash) VALUES (%s, %s, %s)"
    cursor.execute(query, (nombre_admin, correo_admin, contrasena_hash))

    conn.commit()

    print("="*50)
    print("¡Usuario administrador creado exitosamente!")
    print(f"Correo: {correo_admin}")
    print(f"Contraseña: {contrasena_admin}")
    print("="*50)

except mysql.connector.Error as err:
    print(f"Error al crear el usuario: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()