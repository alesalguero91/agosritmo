from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import fitz
import io
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.enums import TA_LEFT
import pandas as pd

def pdf_to_image(pdf_file):
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))
    return image

def buscar_cliente_en_excel(df, cliente_id):
    """Busca un cliente en el DataFrame del Excel por número de cliente/cuenta"""
    # Normalizar nombres de columnas
    df.columns = df.columns.str.lower().str.strip()
    
    # Convertir el ID del cliente a string y limpiar
    cliente_str = str(cliente_id).strip()
    
    # Columnas donde podría estar el número de cuenta/cliente
    posibles_columnas = ['cuenta', 'nro cuenta', 'nro de cuenta', 'numero cuenta', 
                       'numero de cuenta', 'cliente', 'nrocliente', 'numerocliente', 
                       'nro cliente', 'numero cliente', 'idcliente', 'id']
    
    # Encontrar la columna correcta
    columna_encontrada = None
    for col in posibles_columnas:
        if col in df.columns:
            columna_encontrada = col
            break
    
    if not columna_encontrada:
        raise ValueError("No se encontró columna con número de cuenta/cliente en el Excel")
    
    # Buscar el cliente (comparando como strings)
    try:
        # Convertir la columna a string y limpiar
        df[columna_encontrada] = df[columna_encontrada].astype(str).str.strip()
        
        # Primera búsqueda exacta
        cliente_data = df[df[columna_encontrada] == cliente_str]
        
        # Si no se encuentra, probar sin ceros a la izquierda
        if cliente_data.empty:
            cliente_str_sin_ceros = cliente_str.lstrip('0')
            cliente_data = df[df[columna_encontrada].str.lstrip('0') == cliente_str_sin_ceros]
            
            if cliente_data.empty:
                return None  # Cliente no encontrado
        
        datos = cliente_data.iloc[0].to_dict()
    except Exception as e:
        raise ValueError(f"Error al buscar cliente: {str(e)}")
    
    # Obtener DNI y Nombre (ahora obligatorios)
    try:
        dni = next(str(datos[col]) for col in ['dni', 'documento', 'nrodocumento', 'cedula'] 
                  if col in datos and pd.notna(datos[col]))
        nombre = next(str(datos[col]) for col in ['nombre', 'nombre completo', 'nom', 'nombres', 'apellido']
                    if col in datos and pd.notna(datos[col]))
    except StopIteration:
        raise ValueError("No se encontraron los campos obligatorios (DNI y Nombre) para el cliente")
    
    return {
        'nroCliente': str(datos[columna_encontrada]),
        'dni': dni,
        'Nombre': nombre
    }

def generar_pdf_con_texto_y_imagen(image_or_pdf_file, additional_data, excel_data=None):
    try:
        print("Iniciando generación de PDF...")
        print("Número de cuenta recibido:", additional_data)
        
        if not excel_data:
            return {
                'error': True,
                'message': 'Se requiere archivo Excel para buscar los datos del cliente'
            }
        
        excel_data.seek(0)
        df = pd.read_excel(excel_data)
        print("Primeras filas del Excel:", df.head().to_dict())
        
        dats = buscar_cliente_en_excel(df, additional_data)
        if dats is None:
            return {
                'error': True,
                'message': f'La cuenta {additional_data} no existe en el archivo Excel'
            }
        
        print("Datos encontrados:", dats)
        
        TEXTO_NOTA = f"""PARA: ADMINISTRACIÓN
DE: GESTIÓN Y MORA
ASUNTO: AUTORIZACIÓN DE PAGO

FECHA DE PRESENTACIÓN DE NOTA:

CUENTA: {dats['nroCliente']}
NOMBRE: {dats['Nombre']}
DNI: {dats['dni']}

Por medio de la presente solicito, se autorice la acreditación de la transferencia adjunta para ser acreditada en la cuenta de referencia MACRO CTA Nº 314000023459615.

Sin más, atte.
"""
        # Resto del código de generación de PDF...
        if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith('.pdf'):
            image = pdf_to_image(image_or_pdf_file)
        else:
            image = Image.open(image_or_pdf_file)

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Configuración de márgenes y estilo
        left_margin = 50
        right_margin = 50
        top_margin = height - 50
        available_width = width - left_margin - right_margin
        line_height = 14
        font_size = 11

        # Dividir el texto en líneas
        text_lines = []
        for line in TEXTO_NOTA.split("\n"):
            if not line.strip():
                text_lines.append(line)
                continue
                
            words = line.split()
            current_line = words[0] if words else ""
            for word in words[1:]:
                test_line = f"{current_line} {word}"
                if c.stringWidth(test_line, "Helvetica", font_size) <= available_width:
                    current_line = test_line
                else:
                    text_lines.append(current_line)
                    current_line = word
            text_lines.append(current_line)

        # Escribir texto en el PDF
        y_position = top_margin
        for line in text_lines:
            if line.strip(): 
                c.setFont("Helvetica", font_size)
                c.drawString(left_margin, y_position, line)
            y_position -= line_height

        y_position -= 20

        # Procesamiento de la imagen
        image_width, image_height = image.size
        max_image_width = width * 0.6
        ratio = max_image_width / image_width
        resized_height = image_height * ratio
        
        image_resized = image.resize((int(max_image_width), int(resized_height)))
        img_io = io.BytesIO()
        image_resized.save(img_io, format="PNG")
        img_io.seek(0)

        # Añadir imagen al PDF
        c.drawImage(
            ImageReader(img_io),
            x=(width - max_image_width) / 2,
            y=y_position - resized_height,
            width=max_image_width,
            height=resized_height
        )

        c.showPage()
        c.save()
        buffer.seek(0)

        return {
            'error': False,
            'pdf': buffer
        }
        
    except Exception as e:
        print(f"Error en generar_pdf_con_texto_y_imagen: {str(e)}")
        return {
            'error': True,
            'message': f'Error al generar PDF: {str(e)}'
        }
    

    

"""
API_BASE_URL = "http://127.0.0.1:8000/api/clients/"

def obtener_datos_cliente(cliente):
    print("Aqui")
    try:
        response = requests.get(f"{API_BASE_URL}{cliente}")
        print(f"{API_BASE_URL}{cliente}")
        response.raise_for_status()  # Lanza excepción si hay error HTTP
        print("buscado")
        return response.json()
        
    except requests.RequestException as e:
        print(f"Error al obtener datos del cliente: {e}")
        return None


def pdf_to_image(pdf_file):
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))
    return image


def generar_pdf_con_texto_y_imagen(image_or_pdf_file, additional_data):

    dats = obtener_datos_cliente(additional_data)
    print(dats)

    nro = dats.get("nroCliente", "N/A") if dats else "N/A"
    dni = dats.get("dni", "N/A") if dats else "N/A"
    nombre = dats.get("Nombre", "N/A") if dats else "N/A"

    TEXTO_NOTA = fPARA: ADMINISTRACIÓN
DE: GESTIÓN Y MORA
ASUNTO: AUTORIZACIÓN DE PAGO

FECHA DE PRESENTACIÓN DE NOTA:

CUENTA: {nro}
NOMBRE: {nombre}
DNI: {dni}

Por medio de la presente solicito, se autorice la acreditación de la transferencia adjunta para ser acreditada en la cuenta de referencia MACRO CTA Nº 314000023459615.

Sin más, atte.


    if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith('.pdf'):
        image = pdf_to_image(image_or_pdf_file)
    else:
        image = Image.open(image_or_pdf_file)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Configuraciones
    left_margin = 50
    right_margin = 50
    top_margin = height - 50
    available_width = width - left_margin - right_margin
    line_height = 14
    font_size = 11

    # Crear estilo para el párrafo
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        'nota_style',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=font_size,
        leading=line_height,
        alignment=TA_LEFT,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=0,
        spaceAfter=0,
    )

    # Dividir el texto en líneas que quepan en el ancho disponible
    text_lines = []
    for line in TEXTO_NOTA.split("\n"):
        if not line.strip():
            text_lines.append(line)
            continue
            
        words = line.split()
        current_line = words[0] if words else ""
        for word in words[1:]:
            test_line = f"{current_line} {word}"
            if c.stringWidth(test_line, "Helvetica", font_size) <= available_width:
                current_line = test_line
            else:
                text_lines.append(current_line)
                current_line = word
        text_lines.append(current_line)


    text_height = len(text_lines) * line_height


    image_width, image_height = image.size
    max_image_width = width * 0.6
    ratio = max_image_width / image_width
    resized_height = image_height * ratio
    

    required_space = text_height + resized_height + 100 
    

    while required_space > height - 100 and font_size > 8:
        font_size -= 0.5
        line_height = font_size + 3
        style.fontSize = font_size
        style.leading = line_height
        
 
        text_lines = []
        for line in TEXTO_NOTA.split("\n"):
            if not line.strip():
                text_lines.append(line)
                continue
                
            words = line.split()
            current_line = words[0] if words else ""
            for word in words[1:]:
                test_line = f"{current_line} {word}"
                if c.stringWidth(test_line, "Helvetica", font_size) <= available_width:
                    current_line = test_line
                else:
                    text_lines.append(current_line)
                    current_line = word
            text_lines.append(current_line)
        
        text_height = len(text_lines) * line_height
        required_space = text_height + resized_height + 100


    y_position = top_margin
    for line in text_lines:
        if line.strip(): 
            c.setFont("Helvetica", font_size)
            c.drawString(left_margin, y_position, line)
        y_position -= line_height


    y_position -= 20

    resized_width = max_image_width
    image_resized = image.resize((int(resized_width), int(resized_height)))

    img_io = io.BytesIO()
    image_resized.save(img_io, format="PNG")
    img_io.seek(0)


    if y_position - resized_height < 40:
        c.showPage()  
        y_position = height - 50

    c.drawImage(
        ImageReader(img_io),
        x=(width - resized_width) / 2,
        y=y_position - resized_height,
        width=resized_width,
        height=resized_height
    )

    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer
"""