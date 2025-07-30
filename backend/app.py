from flask import Flask, render_template, request, redirect, url_for, flash, make_response, send_from_directory
import mysql.connector
from datetime import date, timedelta, datetime
from fpdf import FPDF
import os
from dotenv import load_dotenv
import uuid # Para generar nombres de archivo únicos
from werkzeug.utils import secure_filename # Para asegurar nombres de archivo
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import jsonify

load_dotenv() # Carga las variables de entorno del archivo .env
app = Flask(__name__, template_folder='../frontend/templates')
app.secret_key = os.environ.get('SECRET_KEY', 'clave_desarrollo_por_defecto')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__, template_folder='../frontend/templates')
app.secret_key = '!!vcbm.Z@XJ5]aO['
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegurarse de que la carpeta de uploads exista
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Configuración de la Base de Datos MySQL ---

db_config = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME')
}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, inicia sesión para acceder a esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Verifica si la extensión del archivo es permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Establece la conexión con la base de datos."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar a MySQL: {err}")
        return None

def get_template_context(**kwargs):
    """Agrega variables comunes al contexto de las plantillas."""
    context = {'year': date.today().year}
    context.update(kwargs)
    return context

def get_lista_generos(conn):
    """Función auxiliar para obtener la lista de todos los géneros."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre FROM Generos ORDER BY nombre")
    generos = cursor.fetchall()
    cursor.close()
    return generos

def get_lista_anaqueles(conn):
    """Función auxiliar para obtener la lista de todos los anaqueles."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre FROM Anaqueles ORDER BY id")
    anaqueles = cursor.fetchall()
    cursor.close()
    return anaqueles

class PDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4'):
        super().__init__(orientation, unit, format)
        self.set_auto_page_break(auto=True, margin=30)  # margen más alto para evitar solapamiento con pie
        self.font_family_pdf = 'Arial'

    def header(self):
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo_izamal.png')
            if os.path.exists(logo_path):
                self.image(logo_path, x=10, y=8, w=30)
            else:
                print(f"⚠️ Logo no encontrado: {logo_path}")
        except Exception as e:
            print(f"⚠️ No se pudo cargar el logo: {e}")

        # Título
        self.set_font(self.font_family_pdf, 'B', 15)
        self.set_y(12)
        self.cell(0, 10, 'Reporte de Biblioteca', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        
        # Texto institucional derecha
        self.set_y(-25)
        self.set_font(self.font_family_pdf, '', 8)
        self.set_text_color(100)
        self.cell(0, 5, "www.izamal.gob.mx", 0, 1, 'R')
        self.cell(0, 5, "Palacio Municipal Calle 30-A N° 323 x 31 y 31-A", 0, 1, 'R')
        self.cell(0, 5, "Centro C.P. 97540 Izamal, Yucatán", 0, 1, 'R')

        # Número de página
        self.set_y(-10)
        self.set_font(self.font_family_pdf, 'I', 8)
        self.set_text_color(0)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font(self.font_family_pdf, 'B', 12)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(50, 50, 50)
        self.cell(0, 10, title, 0, 1, 'L', fill=True)
        self.ln(3)

    def chapter_subtitle(self, subtitle):
        self.set_font(self.font_family_pdf, 'I', 10)
        self.set_text_color(80)
        self.cell(0, 7, subtitle, 0, 1, 'L')
        self.ln(2)

    def create_table(self, table_data, column_widths=None, headers=None, font_size=10, line_height_multiplier=1.5):
        self.set_font(self.font_family_pdf, '', font_size)
        line_height = font_size * line_height_multiplier

    # Obtener todos los datos que vamos a medir
        combined_data = [headers] + table_data if headers else table_data

    # Calcular el ancho máximo de cada columna basado en el texto más largo
        if not column_widths:
           col_count = len(combined_data[0])
           column_widths = [0] * col_count

           for col_idx in range(col_count):
               max_width = 0
               for row in combined_data:
                   cell_text = str(row[col_idx] if row[col_idx] is not None else '')
                   text_width = self.get_string_width(cell_text) + 4  # un poco de padding
                   if text_width > max_width:
                       max_width = text_width
               column_widths[col_idx] = max_width

        # Ajustar a ancho total disponible
        max_total_width = self.w - self.l_margin - self.r_margin
        scale_factor = max_total_width / sum(column_widths)
        column_widths = [w * scale_factor for w in column_widths]

    # Encabezado
        if headers:
           self.set_font(self.font_family_pdf, 'B', font_size)
           self.set_fill_color(154, 27, 31)  # color institucional
           self.set_text_color(255)
           for i, header in enumerate(headers):
               self.cell(column_widths[i], line_height, str(header), border=1, align='C', fill=True)
           self.ln(line_height)

        self.set_font(self.font_family_pdf, '', font_size)
        self.set_text_color(0)

    # Datos
        for row in table_data:
        # Medir altura de fila
            cell_heights = []
            for i, item in enumerate(row):
                text = str(item if item is not None else '')
                lines = self.multi_cell(column_widths[i], line_height, text, border=0, align='L', split_only=True)
                cell_heights.append(len(lines) * line_height)
            max_height = max(cell_heights)

        # Salto de página si no cabe
            if self.get_y() + max_height > self.h - self.b_margin:
                self.add_page()
                if headers:
                   self.set_font(self.font_family_pdf, 'B', font_size)
                   self.set_fill_color(154, 27, 31)
                   self.set_text_color(255)
                   for i, header in enumerate(headers):
                       self.cell(column_widths[i], line_height, str(header), border=1, align='C', fill=True)
                   self.ln(line_height)
                   self.set_font(self.font_family_pdf, '', font_size)
                   self.set_text_color(0)

        # Dibujar fila
            y_start = self.get_y()
            for i, item in enumerate(row):
                text = str(item if item is not None else '')
                x = self.get_x()
                self.multi_cell(column_widths[i], line_height, text, border=1, align='L')
                self.set_xy(x + column_widths[i], y_start)
            self.set_y(y_start + max_height)


    # login inicio de sesion 
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya está en sesión, redirigir a la página principal
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        correo = request.form['email']
        contrasena = request.form['password']

        conn = get_db_connection()
        if not conn:
            flash("Error de conexión con la base de datos.", "danger")
            return render_template('auth/login.html', **get_template_context())

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Usuarios WHERE correo_electronico = %s", (correo,))
        usuario = cursor.fetchone()

        if usuario and check_password_hash(usuario['contrasena_hash'], contrasena):
            # Si el usuario existe y la contraseña es correcta, guardar en sesión
            session.clear()
            session['user_id'] = usuario['id']
            session['user_name'] = usuario['nombre']
            flash(f"¡Bienvenido de nuevo, {usuario['nombre']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Correo electrónico o contraseña incorrectos. Inténtalo de nuevo.", "danger")

        cursor.close()
        conn.close()

    return render_template('auth/login.html', **get_template_context())


@app.route('/logout')
def logout():
    session.clear() # Limpia toda la sesión
    flash("Has cerrado la sesión exitosamente.", "info")
    return redirect(url_for('login'))

# ------dashboard-----
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)
    stats = {}
    libros_por_vencer = []

    try:
        # 1. Total de Libros (títulos únicos)
        cursor.execute("SELECT COUNT(*) as total FROM Libros")
        stats['total_libros'] = cursor.fetchone()['total']

        # 2. Total de Prestatarios
        cursor.execute("SELECT COUNT(*) as total FROM Prestatarios")
        stats['total_prestatarios'] = cursor.fetchone()['total']

        # 3. Total de Préstamos Activos (prestados o vencidos)
        cursor.execute("SELECT COUNT(*) as total FROM Prestamos WHERE estado = 'prestado' OR estado = 'vencido'")
        stats['prestamos_activos'] = cursor.fetchone()['total']
        
        # 4. Libros Próximos a Vencer (en los próximos 3 días)
        fecha_limite = date.today() + timedelta(days=3)
        cursor.execute("""
            SELECT p.id, l.titulo, pr.nombre as nombre_prestatario, p.fecha_devolucion_prevista
            FROM Prestamos p
            JOIN Libros l ON p.libro_id = l.id
            JOIN Prestatarios pr ON p.prestatario_id = pr.id
            WHERE p.estado = 'prestado' AND p.fecha_devolucion_prevista BETWEEN CURDATE() AND %s
            ORDER BY p.fecha_devolucion_prevista ASC
        """, (fecha_limite,))
        libros_por_vencer = cursor.fetchall()
        stats['por_vencer_conteo'] = len(libros_por_vencer)

    except mysql.connector.Error as err:
        flash(f"Error al cargar las estadísticas del dashboard: {err}", "danger")
    finally:
        cursor.close()
        conn.close()

    return render_template('dashboard/dashboard.html', **get_template_context(stats=stats, libros_por_vencer=libros_por_vencer))

@app.route('/')
@login_required
def index():
    # Redirige directamente al nuevo dashboard
    return redirect(url_for('dashboard'))

# --- Rutas para Libros ---
@app.route('/libros')
@login_required
def listar_libros():
    """
    Muestra la lista de todos los libros.
    Si se proporciona un parámetro 'q' en la URL, filtra los resultados.
    """
    termino_busqueda = request.args.get('q', '')

    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)
    
    # Query base que une Libros con Generos para obtener el nombre del género
    base_query = """
        SELECT l.id, l.titulo, l.autor, l.isbn, g.nombre as genero, l.total_ejemplares, l.ejemplares_disponibles 
        FROM Libros l
        JOIN Generos g ON l.genero_id = g.id
    """
    
    params = []
    # Si hay un término de búsqueda, añadimos la cláusula WHERE
    if termino_busqueda:
        base_query += " WHERE l.titulo LIKE %s OR l.autor LIKE %s OR g.nombre LIKE %s"
        parametro_like = f"%{termino_busqueda}%"
        params.extend([parametro_like, parametro_like, parametro_like])

    base_query += " ORDER BY l.titulo"

    try:
        cursor.execute(base_query, tuple(params))
        libros = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error al obtener la lista de libros: {err}", "danger")
        libros = [] 
    finally:
        cursor.close()
        conn.close()
        
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('libros/tabla_libros_partial.html', libros=libros)
        
    return render_template('libros/listar.html', **get_template_context(libros=libros, busqueda=termino_busqueda))

@app.route('/libros/detalle/<int:id_libro>')
@login_required
def detalle_libro(id_libro):
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)
    
    libro = None
    historial_prestamos = []

    try:
        cursor.execute("""
            SELECT l.*, g.nombre as nombre_genero, a.nombre as nombre_anaquel 
            FROM Libros l 
            JOIN Generos g ON l.genero_id = g.id
            LEFT JOIN Anaqueles a ON l.anaquel_id = a.id 
            WHERE l.id = %s
        """, (id_libro,))
        libro = cursor.fetchone()

        if not libro:
            flash("Libro no encontrado.", "warning")
            return redirect(url_for('listar_libros'))

        # 2. Obtener el historial de préstamos para este libro
        cursor.execute("""
            SELECT p.id, pr.nombre as nombre_prestatario, 
                   p.fecha_prestamo, p.fecha_devolucion_real, p.estado
            FROM Prestamos p
            JOIN Prestatarios pr ON p.prestatario_id = pr.id
            WHERE p.libro_id = %s
            ORDER BY p.fecha_prestamo DESC
        """, (id_libro,))
        historial_prestamos = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error al cargar los detalles del libro: {err}", "danger")
        return redirect(url_for('listar_libros'))
    finally:
        cursor.close()
        conn.close()

    return render_template('libros/detalle.html', 
                           **get_template_context(
                               libro=libro, 
                               historial=historial_prestamos
                           ))

@app.route('/generos/agregar', methods=['POST'])
@login_required
def agregar_genero_api():
    nuevo_genero_nombre = request.form.get('nombre_genero')
    if not nuevo_genero_nombre:
        return jsonify({'success': False, 'message': 'El nombre del género no puede estar vacío.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión a la base de datos.'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Generos (nombre) VALUES (%s)", (nuevo_genero_nombre,))
        conn.commit()
        
        # Devolver la lista actualizada de géneros
        generos_actualizados = get_lista_generos(conn)
        return jsonify({'success': True, 'message': 'Género agregado exitosamente.', 'generos': generos_actualizados})

    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062: # Error de entrada duplicada
            return jsonify({'success': False, 'message': 'Este género ya existe.'}), 409
        return jsonify({'success': False, 'message': f'Error de base de datos: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

# agregar libros
@app.route('/libros/nuevo', methods=['GET', 'POST'])
@login_required
def agregar_libro():
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar."))

    """Permite agregar un nuevo libro al inventario."""

    if request.method == 'POST':
        titulo = request.form['titulo']
        autor = request.form['autor']
        editorial = request.form.get('editorial')
        isbn = request.form['isbn'].strip() or None 
        genero_id = request.form.get('genero_id')
        anaquel_id = request.form.get('anaquel_id')
        total_ejemplares = int(request.form.get('total_ejemplares', 1))
        
        anaquel_id = int(anaquel_id) if anaquel_id else None

        if not genero_id:
            flash("El campo 'Género' es obligatorio.", "warning")
            # Recargar la lista de géneros y anaqueles para volver a mostrar el formulario
            lista_generos = get_lista_generos(conn)
            lista_anaqueles = get_lista_anaqueles(conn)
            conn.close()
            return render_template('libros/formulario.html', **get_template_context(libro=request.form, accion="Registrar Nuevo Libro", generos=lista_generos, anaqueles=lista_anaqueles))

        cursor = conn.cursor()
        # Query de inserción actualizada
        query = """
            INSERT INTO Libros (titulo, autor, editorial , isbn, genero_id, anaquel_id, total_ejemplares, ejemplares_disponibles) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            # ejemplares_disponibles = total_ejemplares al inicio
            cursor.execute(query, (titulo, autor,editorial, isbn, genero_id,anaquel_id, total_ejemplares, total_ejemplares)) 
            conn.commit()
            flash(f"Libro '{titulo}' agregado exitosamente.", "success")
        except mysql.connector.Error as err:
            print(f"Error al insertar libro: {err}")
            conn.rollback()
            flash(f"Error al insertar libro: {err}", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('listar_libros'))
    
    lista_generos = get_lista_generos(conn)
    lista_anaqueles = get_lista_anaqueles(conn)
    conn.close()
    return render_template('libros/formulario.html', **get_template_context(libro=None, accion="Registrar Nuevo Libro", generos= lista_generos, anaqueles=lista_anaqueles))


# EDITAR LIBROS
@app.route('/libros/editar/<int:id_libro>', methods=['GET', 'POST'])
@login_required
def editar_libro(id_libro):
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))

    if request.method == 'POST':
        # Obtener datos del formulario
        titulo = request.form['titulo']
        autor = request.form['autor']
        editorial = request.form.get('editorial')
        isbn = request.form['isbn'].strip() or None
        genero_id = request.form.get('genero_id')
        anaquel_id = request.form.get('anaquel_id')
        total_ejemplares_form = int(request.form.get('total_ejemplares', 1))

        anaquel_id = int(anaquel_id) if anaquel_id else None

        if not genero_id:
            flash("El campo 'Género' es obligatorio.", "warning")
            # Para recargar el formulario en caso de error, necesitamos obtener los datos de nuevo
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Libros WHERE id = %s", (id_libro,))
            libro_actual = cursor.fetchone()
            cursor.close()
            lista_generos = get_lista_generos(conn)
            lista_anaqueles = get_lista_anaqueles(conn)
            conn.close()
            return render_template('libros/formulario.html', **get_template_context(libro=libro_actual, accion="Editar Libro", generos=lista_generos, anaqueles=lista_anaqueles))


        update_query = """
            UPDATE Libros 
            SET titulo=%s, autor=%s, editorial=%s, isbn=%s, genero_id=%s, anaquel_id=%s, total_ejemplares=%s 
            WHERE id=%s
        """
        try:
            cursor_update = conn.cursor()
            cursor_update.execute(update_query, (
                titulo, autor, editorial, isbn, genero_id,
                anaquel_id, total_ejemplares_form, id_libro
            ))
            conn.commit()
            flash(f"Libro '{titulo}' actualizado exitosamente.", "success")
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f"Error al actualizar el libro: {err}", "danger")
        finally:
            cursor_update.close()
            conn.close()
        return redirect(url_for('listar_libros'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Libros WHERE id = %s", (id_libro,))
    libro = cursor.fetchone()
    cursor.close()
    
    if libro is None:
        flash("Libro no encontrado.", "warning")
        conn.close()
        return redirect(url_for('listar_libros'))
    
    lista_generos = get_lista_generos(conn)
    lista_anaqueles = get_lista_anaqueles(conn)
    conn.close()
    
    return render_template('libros/formulario.html', **get_template_context(libro=libro, accion="Editar Libro", generos=lista_generos, anaqueles=lista_anaqueles))

# eliminar libros
@app.route('/libros/eliminar/<int:id_libro>', methods=['POST'])
@login_required
def eliminar_libro(id_libro):
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)
    
    # Obtener el título del libro antes de intentar eliminarlo, para usarlo en los mensajes
    try:
        cursor.execute("SELECT titulo FROM Libros WHERE id = %s", (id_libro,))
        libro_info = cursor.fetchone()
        nombre_libro = libro_info['titulo'] if libro_info else "Libro desconocido"
    except mysql.connector.Error:
        nombre_libro = "Libro desconocido"

    try:
        # Intentar eliminar el libro
        cursor.execute("DELETE FROM Libros WHERE id = %s", (id_libro,))
        conn.commit()
        flash(f"Libro '{nombre_libro}' eliminado exitosamente.", "success")
    
    except mysql.connector.Error as err:
        conn.rollback()
        
        if err.errno == 1451:
#mostrar nuestro mensaje personalizado y amigable
            flash(f"No se puede eliminar el libro '{nombre_libro}'. Tiene préstamos asociados.", "danger")
        else:
            # Para cualquier otro tipo de error de base de datos, mostramos un mensaje genérico
            flash(f"Error al eliminar el libro: Ocurrió un problema con la base de datos.", "danger")
            print(f"Error detallado al eliminar libro: {err}")
       

    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('listar_libros'))

@app.route('/api/libros/buscar', methods=['GET'])
@login_required
def api_buscar_libros():
    """
    API para buscar libros disponibles por título o autor.

    """
    termino_busqueda = request.args.get('q', '')
    if len(termino_busqueda) < 2: # No buscar si el término es muy corto
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    # Buscamos libros que coincidan y que tengan ejemplares disponibles
    query = """
        SELECT id, titulo, autor 
        FROM Libros 
        WHERE (titulo LIKE %s OR autor LIKE %s) AND ejemplares_disponibles > 0
        LIMIT 10
    """
    parametro_like = f"%{termino_busqueda}%"
    
    try:
        cursor.execute(query, (parametro_like, parametro_like))
        libros = cursor.fetchall()
        return jsonify(libros)
    except mysql.connector.Error as err:
        print(f"Error en API de búsqueda de libros: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


# agregar imagenes
@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    """Sirve un archivo desde la carpeta de uploads de forma segura."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#---------------------
@app.route('/anaqueles')
@login_required
def vista_anaqueles():
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))

    cursor = conn.cursor(dictionary=True)
    
    # 1. Obtener todos los anaqueles
    cursor.execute("SELECT * FROM Anaqueles ORDER BY id")
    anaqueles = cursor.fetchall()
    
    # 2. Obtener todos los libros, ordenados por anaquel y luego por título
    cursor.execute("""
        SELECT L.*, A.nombre as nombre_anaquel 
        FROM Libros L 
        LEFT JOIN Anaqueles A ON L.anaquel_id = A.id 
        ORDER BY L.anaquel_id, L.titulo ASC
    """)
    libros = cursor.fetchall()
    
    # 3. Organizar los libros por anaquel en un diccionario
    libros_por_anaquel = {anaquel['id']: [] for anaquel in anaqueles}
    libros_sin_anaquel = []

    for libro in libros:
        if libro['anaquel_id'] in libros_por_anaquel:
            libros_por_anaquel[libro['anaquel_id']].append(libro)
        else:
            libros_sin_anaquel.append(libro)
            
    cursor.close()
    conn.close()

    return render_template('anaqueles/vista.html', 
                           **get_template_context(anaqueles=anaqueles, 
                                                  libros_por_anaquel=libros_por_anaquel,
                                                  libros_sin_anaquel=libros_sin_anaquel))


# --- Rutas para Prestatarios ---
@app.route('/prestatarios')
@login_required
def listar_prestatarios():
    conn = get_db_connection()
    if not conn: return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, nombre, correo_electronico, telefono, ruta_identificacion FROM Prestatarios ORDER BY nombre")
        prestatarios = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error al obtener prestatarios: {err}", "danger")
        prestatarios = []
    finally:
        cursor.close()
        conn.close()
    return render_template('prestatarios/listar.html', **get_template_context(prestatarios=prestatarios))

#-----------detalles prestatarios--------
@app.route('/prestatarios/detalle/<int:id_prestatario>')
@login_required
def detalle_prestatario(id_prestatario):
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)
    
    prestatario = None
    historial_prestamos = []

    try:
        # 1. Obtener la información del prestatario
        cursor.execute("SELECT * FROM Prestatarios WHERE id = %s", (id_prestatario,))
        prestatario = cursor.fetchone()

        # Si no se encuentra el prestatario, redirigir con un mensaje
        if not prestatario:
            flash("Prestatario no encontrado.", "warning")
            return redirect(url_for('listar_prestatarios'))

        # 2. Obtener el historial completo de préstamos de ese prestatario
        query_historial = """
            SELECT p.id, l.titulo AS libro_titulo, 
                   p.fecha_prestamo, p.fecha_devolucion_prevista, p.fecha_devolucion_real, p.estado
            FROM Prestamos p
            JOIN Libros l ON p.libro_id = l.id
            WHERE p.prestatario_id = %s
            ORDER BY p.fecha_prestamo DESC
        """
        cursor.execute(query_historial, (id_prestatario,))
        historial_prestamos = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error al cargar los detalles del prestatario: {err}", "danger")
        return redirect(url_for('listar_prestatarios'))
    finally:
        cursor.close()
        conn.close()

    return render_template('prestatarios/detalle.html', 
                           **get_template_context(
                               prestatario=prestatario, 
                               historial=historial_prestamos,
                               today_date=date.today()
                           ))

@app.route('/prestatarios/nuevo', methods=['GET', 'POST'])
@login_required
def agregar_prestatario():
    if request.method == 'POST':
        archivo_identificacion = None
        if 'identificacion' in request.files:
            file = request.files['identificacion']
            # Si el usuario no selecciona un archivo, el navegador
            #puede enviar una parte vacía sin nombre de archivo.
            if file.filename != '':
                if file and allowed_file(file.filename):
                    extension = file.filename.rsplit('.', 1)[1].lower()
                    nombre_archivo_seguro = secure_filename(f"{uuid.uuid4()}.{extension}")
                    ruta_guardado = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo_seguro)
                    file.save(ruta_guardado)
                    archivo_identificacion = nombre_archivo_seguro
                else:
                    flash("Tipo de archivo no permitido. Use png, jpg, jpeg, o gif.", "warning")
                    return render_template('prestatarios/formulario.html', **get_template_context(prestatario=request.form, accion="Registrar Nuevo Prestatario"))

        # --- Lógica de inserción en BD ---
        nombre = request.form['nombre']
        correo_electronico = request.form.get('correo_electronico')
        telefono = request.form.get('telefono')
        
        conn = get_db_connection()
        if not conn: return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
        
        cursor = conn.cursor()
        # Query actualizada para incluir la ruta de la imagen
        query = "INSERT INTO Prestatarios (nombre, correo_electronico, telefono, ruta_identificacion) VALUES (%s, %s, %s, %s)"
        try:
            cursor.execute(query, (nombre, correo_electronico, telefono, archivo_identificacion))
            conn.commit()
            flash(f"Prestatario '{nombre}' agregado exitosamente.", "success")
        except mysql.connector.Error as err:
            conn.rollback()
            if err.errno == 1062: 
                 flash(f"Error: Ya existe un prestatario con el correo '{correo_electronico}'. ({err})", "danger")
            else:
                flash(f"Error al agregar prestatario: {err}", "danger")
            
            if archivo_identificacion and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], archivo_identificacion)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], archivo_identificacion))
            return render_template('prestatarios/formulario.html', **get_template_context(prestatario=request.form, accion="Registrar Nuevo Prestatario"))
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('listar_prestatarios'))

    return render_template('prestatarios/formulario.html', **get_template_context(prestatario=None, accion="Registrar Nuevo Prestatario"))

@app.route('/prestatarios/editar/<int:id_prestatario>', methods=['GET', 'POST'])
@login_required
def editar_prestatario(id_prestatario):
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nombre = request.form['nombre']
        correo_electronico = request.form.get('correo_electronico')
        telefono = request.form.get('telefono')
        
        # Obtener la ruta de la imagen antigua
        cursor.execute("SELECT ruta_identificacion FROM Prestatarios WHERE id = %s", (id_prestatario,))
        prestatario_actual = cursor.fetchone()
        ruta_imagen_antigua = prestatario_actual['ruta_identificacion'] if prestatario_actual else None
        
        archivo_identificacion = ruta_imagen_antigua 

        # Lógica para manejar la nueva imagen, si se subió una
        if 'identificacion' in request.files:
            file = request.files['identificacion']
            if file and file.filename != '' and allowed_file(file.filename):
                
                if ruta_imagen_antigua and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], ruta_imagen_antigua)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], ruta_imagen_antigua))
                
                # Guardar el nuevo archivo
                extension = file.filename.rsplit('.', 1)[1].lower()
                nombre_archivo_seguro = secure_filename(f"{uuid.uuid4()}.{extension}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo_seguro))
                archivo_identificacion = nombre_archivo_seguro
            elif file and file.filename != '':
                flash("Tipo de archivo no permitido. La imagen no fue actualizada.", "warning")

        # Actualizar la base de datos
        update_query = """
            UPDATE Prestatarios SET nombre=%s, correo_electronico=%s, telefono=%s, ruta_identificacion=%s
            WHERE id=%s
        """
        try:
            cursor_update = conn.cursor()
            cursor_update.execute(update_query, (nombre, correo_electronico, telefono, archivo_identificacion, id_prestatario))
            conn.commit()
            cursor_update.close()
            flash(f"Prestatario '{nombre}' actualizado exitosamente.", "success")
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f"Error al actualizar el prestatario: {err}", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('listar_prestatarios'))

    # GET request: Cargar datos del prestatario para editar
    cursor.execute("SELECT * FROM Prestatarios WHERE id = %s", (id_prestatario,))
    prestatario = cursor.fetchone()
    cursor.close()
    conn.close()
    if prestatario is None:
        flash("Prestatario no encontrado.", "warning")
        return redirect(url_for('listar_prestatarios'))
    
    return render_template('prestatarios/formulario.html', **get_template_context(prestatario=prestatario, accion="Editar Prestatario"))


@app.route('/prestatarios/eliminar/<int:id_prestatario>', methods=['POST'])
@login_required
def eliminar_prestatario(id_prestatario):
    conn = get_db_connection()
    if not conn:
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)
    
   
    cursor.execute("SELECT nombre, ruta_identificacion FROM Prestatarios WHERE id = %s", (id_prestatario,))
    prestatario_info = cursor.fetchone()
    
    if not prestatario_info:
        flash("Prestatario no encontrado.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('listar_prestatarios'))

    nombre_prestatario = prestatario_info['nombre']
    ruta_imagen = prestatario_info['ruta_identificacion']

    try:
        # Intentar eliminar de la base de datos
        cursor_delete = conn.cursor()
        cursor_delete.execute("DELETE FROM Prestatarios WHERE id = %s", (id_prestatario,))
        conn.commit()
        cursor_delete.close()
        
        # Si la eliminación en la BD fue exitosa, borrar el archivo de imagen
        if ruta_imagen and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], ruta_imagen)):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], ruta_imagen))
            
        flash(f"Prestatario '{nombre_prestatario}' eliminado exitosamente.", "success")
    
    except mysql.connector.Error as err:
        conn.rollback()
        # Error de restricción de clave foránea (no se puede borrar porque tiene préstamos)
        if err.errno == 1451:
            flash(f"No se puede eliminar a '{nombre_prestatario}' porque tiene préstamos asociados en su historial.", "danger")
        else:
            flash(f"Error al eliminar el prestatario: {err}", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('listar_prestatarios'))

# --- Rutas para Préstamos ---
@app.route('/prestamos')
@login_required
def listar_prestamos():
    # Obtener el término de búsqueda de los argumentos de la URL (?q=...)
    termino_busqueda = request.args.get('q', '')

    conn = get_db_connection()
    if not conn: 
        return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor = conn.cursor(dictionary=True)
    
    # Query base para obtener todos los préstamos
    base_query = """
        SELECT p.id, l.titulo AS libro_titulo, pr.nombre AS nombre_prestatario, 
               p.fecha_prestamo, p.fecha_devolucion_prevista, p.fecha_devolucion_real, p.estado
        FROM Prestamos p
        JOIN Libros l ON p.libro_id = l.id
        JOIN Prestatarios pr ON p.prestatario_id = pr.id
    """
    
    params = []
    # Si hay un término de búsqueda, añadimos la cláusula WHERE
    if termino_busqueda:
        base_query += " WHERE l.titulo LIKE %s OR pr.nombre LIKE %s"
        parametro_like = f"%{termino_busqueda}%"
        params.extend([parametro_like, parametro_like])

    # Añadimos el ordenamiento al final
    base_query += " ORDER BY p.fecha_prestamo DESC"

    try:
        cursor.execute(base_query, tuple(params))
        prestamos = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error al obtener los préstamos: {err}", "danger")
        prestamos = []
    finally:
        cursor.close()
        conn.close()
        
    # Pasamos el término de búsqueda a la plantilla para mostrarlo en el input
    return render_template(
        'prestamos/listar.html', 
        **get_template_context(
            prestamos=prestamos, 
            today_date=date.today(), 
            busqueda=termino_busqueda
        )
    )


@app.route('/prestamos/nuevo', methods=['GET', 'POST'])
@login_required
def registrar_prestamo():
    conn = get_db_connection()
    if not conn: return render_template('error_db.html', **get_template_context(mensaje_error="No se pudo conectar a la base de datos."))
    
    cursor_lectura = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            libro_id = int(request.form['libro_id'])
            prestatario_id = int(request.form['prestatario_id'])
        except (ValueError, TypeError):
            flash("ID de libro o prestatario inválido.", "danger")
           
            cursor_lectura.close()
            conn.close()

            return redirect(url_for('registrar_prestamo'))


        # 1.límite de préstamos
        cursor_lectura.execute("SELECT COUNT(*) as conteo FROM Prestamos WHERE prestatario_id = %s AND (estado = 'prestado' OR estado = 'vencido')", (prestatario_id,))
        conteo_prestamos = cursor_lectura.fetchone()['conteo']
        if conteo_prestamos >= 3:
            # Obtener el nombre del prestatario para un mensaje más amigable
            cursor_lectura.execute("SELECT nombre FROM Prestatarios WHERE id = %s", (prestatario_id,))
            nombre_prestatario = cursor_lectura.fetchone()['nombre']
            
            flash(f"Límite alcanzado. El prestatario '{nombre_prestatario}' ya tiene 3 préstamos activos y no puede solicitar más.", "danger")
            
            cursor_lectura.close()
            conn.close()
            return redirect(url_for('registrar_prestamo'))
        
        
        cursor_lectura.execute("SELECT titulo, ejemplares_disponibles FROM Libros WHERE id = %s", (libro_id,))
        libro_info = cursor_lectura.fetchone()

        if not libro_info or libro_info['ejemplares_disponibles'] <= 0:
            flash(f"El libro seleccionado no está disponible para préstamo o no existe.", "warning")
            cursor_lectura.close()
            conn.close()
            return redirect(url_for('registrar_prestamo'))
        
        fecha_prestamo = date.today()
        fecha_devolucion_prevista = fecha_prestamo + timedelta(days=15)
        
        cursor_escritura = conn.cursor()
        insert_prestamo_query = """
            INSERT INTO Prestamos (libro_id, prestatario_id, fecha_prestamo, fecha_devolucion_prevista, estado) 
            VALUES (%s, %s, %s, %s, 'prestado')
        """
        update_libro_query = "UPDATE Libros SET ejemplares_disponibles = ejemplares_disponibles - 1 WHERE id = %s"
        
        try:
            cursor_escritura.execute(insert_prestamo_query, (libro_id, prestatario_id, fecha_prestamo, fecha_devolucion_prevista))
            cursor_escritura.execute(update_libro_query, (libro_id,))
            conn.commit()
            flash(f"Préstamo del libro '{libro_info['titulo']}' registrado exitosamente.", "success")
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error al registrar préstamo: {err}")
            flash(f"Error de base de datos al registrar el préstamo: {err}", "danger")
        finally:
            cursor_escritura.close()
            cursor_lectura.close() 
            conn.close()
        
        return redirect(url_for('listar_prestamos'))
    
    # --- Lógica para la solicitud GET 
    try:
        cursor_lectura.execute("SELECT id, nombre FROM Prestatarios ORDER BY nombre")
        prestatarios = cursor_lectura.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error al cargar datos para el formulario de préstamo: {err}", "danger")
        libros_disponibles = []
        prestatarios = []
    finally:
        cursor_lectura.close()
        conn.close()
    return render_template('prestamos/formulario.html', **get_template_context(prestatarios=prestatarios))


@app.route('/prestamos/devolucion/<int:id_prestamo>', methods=['POST'])
@login_required
def registrar_devolucion(id_prestamo):
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "danger")
        return redirect(url_for('listar_prestamos'))

    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Obtener el ID del libro de este préstamo para poder actualizar el inventario.
        #    También verificamos que el préstamo no haya sido ya devuelto.
        cursor.execute("SELECT libro_id, estado FROM Prestamos WHERE id = %s", (id_prestamo,))
        prestamo_info = cursor.fetchone()
        
        if not prestamo_info:
            flash("El préstamo que intentas devolver no existe.", "warning")
            return redirect(url_for('listar_prestamos'))
        
        if prestamo_info['estado'] == 'devuelto':
            flash("Este préstamo ya ha sido marcado como devuelto anteriormente.", "info")
            return redirect(url_for('listar_prestamos'))

        id_libro_devuelto = prestamo_info['libro_id']

        # 2. Actualizar el estado del préstamo a 'devuelto' y poner la fecha de devolución.
        update_prestamo_query = "UPDATE Prestamos SET estado = 'devuelto', fecha_devolucion_real = %s WHERE id = %s"
        cursor.execute(update_prestamo_query, (date.today(), id_prestamo))

        # 3. Incrementar el contador de ejemplares disponibles del libro devuelto.
        update_libro_query = "UPDATE Libros SET ejemplares_disponibles = ejemplares_disponibles + 1 WHERE id = %s"
        cursor.execute(update_libro_query, (id_libro_devuelto,))

        # 4. Confirmar todos los cambios en la base de datos.
        conn.commit()
        
        flash("Devolución registrada exitosamente.", "success")

    except mysql.connector.Error as err:
        # Si algo sale mal, revertir todos los cambios.
        conn.rollback()
        flash(f"Error al registrar la devolución: {err}", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('listar_prestamos'))

# --- Rutas para Reportes ---
@app.route('/reportes/prestados')
@login_required
def reporte_libros_prestados():
    """Genera un reporte de los libros actualmente prestados."""
    conn = get_db_connection()
    if not conn: return "Error de conexión a la base de datos", 500
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT l.titulo AS libro_titulo, l.autor AS libro_autor, 
               pr.nombre AS nombre_prestatario, 
               p.fecha_prestamo, p.fecha_devolucion_prevista
        FROM Prestamos p
        JOIN Libros l ON p.libro_id = l.id
        JOIN Prestatarios pr ON p.prestatario_id = pr.id
        WHERE p.estado = 'prestado' OR p.estado = 'vencido' 
        ORDER BY p.fecha_devolucion_prevista ASC
    """
    # Lógica para 'vencido' 
    cursor.execute(query)
    libros_prestados = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('reportes/prestados.html', **get_template_context(libros_prestados=libros_prestados))

@app.route('/reportes/inventario')
@login_required
def reporte_inventario_total():
    """Genera un reporte del total de libros en el inventario."""
    conn = get_db_connection()
    if not conn: return "Error de conexión a la base de datos", 500
    cursor = conn.cursor(dictionary=True)
    
    # Query de sumario 
    cursor.execute("""
        SELECT COUNT(*) AS total_titulos, 
               SUM(total_ejemplares) AS sum_total_ejemplares, 
               SUM(ejemplares_disponibles) AS sum_ejemplares_disponibles 
        FROM Libros
    """)
    sumario = cursor.fetchone()
    
    # Query de detalle 
    cursor.execute("SELECT titulo, autor, total_ejemplares, ejemplares_disponibles FROM Libros ORDER BY titulo")
    detalle_libros = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('reportes/inventario.html', **get_template_context(sumario=sumario, detalle_libros=detalle_libros))

@app.route('/reportes/inventario/pdf') 
@login_required
def generar_pdf_inventario():
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos al generar PDF.", "danger")
        return redirect(url_for('reporte_inventario_total'))

    cursor = conn.cursor(dictionary=True)
    pdf = PDF(orientation='L') 
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font(pdf.font_family_pdf, 'B', 16)
    pdf.cell(0, 10, 'Reporte de Inventario de Libros', 0, 1, 'C')
    pdf.set_font(pdf.font_family_pdf, '', 10)
    pdf.cell(0, 7, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, 'C')
    pdf.ln(5)

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total_titulos, 
                   SUM(total_ejemplares) AS sum_total_ejemplares, 
                   SUM(ejemplares_disponibles) AS sum_ejemplares_disponibles 
            FROM Libros
        """)
        sumario = cursor.fetchone()
        if sumario:
            pdf.set_font(pdf.font_family_pdf, 'B', 11)
            pdf.cell(0, 10, "Resumen del Inventario:", 0, 1, 'L')
            pdf.set_font(pdf.font_family_pdf, '', 10)
            pdf.cell(90, 7, f"Total de Títulos Únicos: {sumario.get('total_titulos', 0)}", 0, 0, 'L')
            pdf.cell(90, 7, f"Total de Ejemplares: {sumario.get('sum_total_ejemplares', 0)}", 0, 0, 'L')
            pdf.cell(90, 7, f"Ejemplares Disponibles: {sumario.get('sum_ejemplares_disponibles', 0)}", 0, 1, 'L')
            pdf.ln(5)

        cursor.execute("""
            SELECT l.titulo, l.autor, l.isbn, g.nombre as genero, l.total_ejemplares, l.ejemplares_disponibles 
            FROM Libros l
            JOIN Generos g ON l.genero_id = g.id
            ORDER BY l.titulo
        """)
        libros = cursor.fetchall()
        
        pdf.set_font(pdf.font_family_pdf, 'B', 11)
        pdf.cell(0, 10, "Detalle de Libros en Inventario:", 0, 1, 'L')
        
        headers = ["Título", "Autor", "ISBN", "Género", "Total Ejem.", "Disponibles"]
        data_for_table = [
            [libro['titulo'], libro['autor'], libro['isbn'], libro['genero'],
             libro['total_ejemplares'], libro['ejemplares_disponibles']]
            for libro in libros
        ] if libros else []

        if data_for_table:
            pdf.create_table(data_for_table, headers=headers, font_size=10)
        else:
            pdf.set_font(pdf.font_family_pdf, '', 10)
            pdf.cell(0, 10, "No hay libros registrados en el inventario.", 0, 1)

    except mysql.connector.Error as err:
        flash("Error al obtener datos para el PDF de inventario.", "danger")
        pdf.set_font(pdf.font_family_pdf, 'B', 12)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, f"Error al generar el reporte: {err}", 0, 1, 'C')
    finally:
        cursor.close()
        conn.close()

    response = make_response(bytes(pdf.output(dest='S')))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_inventario_{date.today().strftime("%Y%m%d")}.pdf'
    return response


@app.route('/reportes/prestados/pdf')
@login_required
def generar_pdf_prestados():
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos al generar PDF.", "danger")
        return redirect(url_for('reporte_libros_prestados'))

    cursor = conn.cursor(dictionary=True)
    pdf = PDF(orientation='P')
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font(pdf.font_family_pdf, 'B', 16)
    pdf.cell(0, 10, 'Reporte de Libros Actualmente Prestados', 0, 1, 'C')
    pdf.set_font(pdf.font_family_pdf, '', 10)
    pdf.cell(0, 7, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, 'C')
    pdf.ln(8)

    query = """
        SELECT l.titulo AS libro_titulo, l.autor AS libro_autor, 
               pr.nombre AS nombre_prestatario, 
               p.fecha_prestamo, p.fecha_devolucion_prevista, p.estado
        FROM Prestamos p
        JOIN Libros l ON p.libro_id = l.id
        JOIN Prestatarios pr ON p.prestatario_id = pr.id
        WHERE p.estado = 'prestado' OR p.estado = 'vencido' 
        ORDER BY p.fecha_devolucion_prevista ASC
    """
    try:
        cursor.execute(query)
        prestamos = cursor.fetchall()

        headers = ["Libro", "Autor", "Prestatario", "F. Préstamo", "F. Devolución", "Estado"]
        data_for_table = [
            [
                prestamo['libro_titulo'],
                prestamo['libro_autor'],
                prestamo['nombre_prestatario'],
                prestamo['fecha_prestamo'].strftime('%d/%m/%y') if prestamo['fecha_prestamo'] else '',
                prestamo['fecha_devolucion_prevista'].strftime('%d/%m/%y') if prestamo['fecha_devolucion_prevista'] else '',
                "Vencido" if prestamo['estado'] == 'prestado' and prestamo['fecha_devolucion_prevista'] < date.today() else prestamo['estado'].capitalize()
            ]
            for prestamo in prestamos
        ] if prestamos else []

        if data_for_table:
            pdf.create_table(data_for_table, headers=headers, font_size=10)
        else:
            pdf.set_font(pdf.font_family_pdf, '', 10)
            pdf.cell(0, 10, "No hay libros actualmente prestados.", 0, 1)

    except mysql.connector.Error as err:
        flash("Error al obtener datos para el PDF de prestados.", "danger")
        pdf.set_font(pdf.font_family_pdf, 'B', 12)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, f"Error al generar el reporte: {err}", 0, 1, 'C')
    finally:
        cursor.close()
        conn.close()

    response = make_response(bytes(pdf.output(dest='S')))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_prestamos_{date.today().strftime("%Y%m%d")}.pdf'
    return response

@app.route('/reportes/anaqueles/pdf', methods=['POST'])
@login_required
def generar_pdf_anaqueles():
    ids_anaqueles_seleccionados = request.form.getlist('anaquel_id')
    if not ids_anaqueles_seleccionados:
        flash("No se seleccionó ningún anaquel para generar el reporte.", "warning")
        return redirect(url_for('vista_anaqueles'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('vista_anaqueles'))

    cursor = conn.cursor(dictionary=True)
    format_strings = ','.join(['%s'] * len(ids_anaqueles_seleccionados))

    cursor.execute(f"SELECT * FROM Anaqueles WHERE id IN ({format_strings}) ORDER BY id", tuple(ids_anaqueles_seleccionados))
    anaqueles = cursor.fetchall()

    cursor.execute(f"""
        SELECT L.*, A.nombre as nombre_anaquel 
        FROM Libros L 
        JOIN Anaqueles A ON L.anaquel_id = A.id 
        WHERE L.anaquel_id IN ({format_strings})
        ORDER BY L.anaquel_id, L.titulo ASC
    """, tuple(ids_anaqueles_seleccionados))
    libros = cursor.fetchall()

    cursor.close()
    conn.close()

    libros_por_anaquel_pdf = {anaquel['id']: [] for anaquel in anaqueles}
    for libro in libros:
        if libro['anaquel_id'] in libros_por_anaquel_pdf:
            libros_por_anaquel_pdf[libro['anaquel_id']].append(libro)

    pdf = PDF(orientation='P')
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.chapter_title('Reporte de Libros por Anaquel')
    pdf.chapter_subtitle(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    for anaquel in anaqueles:
        pdf.set_font(pdf.font_family_pdf, 'B', 12)
        pdf.cell(0, 10, f"Contenido de: {anaquel['nombre']}", 0, 1, 'L')
        
        libros_de_este_anaquel = libros_por_anaquel_pdf.get(anaquel['id'], [])
        
        if libros_de_este_anaquel:
            headers = ["Título", "Autor", "Editorial"]
            data_for_table = [[libro['titulo'], libro['autor'], libro['editorial']] for libro in libros_de_este_anaquel]
            pdf.create_table(data_for_table, headers=headers, font_size=9)
        else:
            pdf.set_font(pdf.font_family_pdf, 'I', 9)
            pdf.cell(0, 7, "Este anaquel no contiene libros registrados.", 0, 1, 'L')
        
        pdf.ln(8)

    response = make_response(bytes(pdf.output(dest='S')))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_anaqueles_{date.today().strftime("%Y%m%d")}.pdf'
    return response

if __name__ == '__main__':
    print("Iniciando servidor Flask...")
    app.run(debug=True)