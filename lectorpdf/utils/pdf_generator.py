from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import fitz
import io
import pandas as pd
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from datetime import datetime

def pdf_to_image(pdf_file):
    """Convierte la primera página de un PDF a imagen"""
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))
    return image

def buscar_cliente_en_excel(df, cliente_id):
    """Busca un cliente en el DataFrame del Excel por número de cliente/cuenta"""
    df.columns = df.columns.str.lower().str.strip()
    cliente_str = str(cliente_id).strip()
    
    posibles_columnas = ['cuenta', 'nro cuenta', 'nro de cuenta', 'numero cuenta', 
                       'numero de cuenta', 'cliente', 'nrocliente', 'numerocliente', 
                       'nro cliente', 'numero cliente', 'idcliente', 'id']
    
    columna_encontrada = next((col for col in posibles_columnas if col in df.columns), None)
    
    if not columna_encontrada:
        raise ValueError("No se encontró columna con número de cuenta/cliente en el Excel")
    
    try:
        df[columna_encontrada] = df[columna_encontrada].astype(str).str.strip()
        cliente_data = df[df[columna_encontrada] == cliente_str]
        
        if cliente_data.empty:
            cliente_str_sin_ceros = cliente_str.lstrip('0')
            cliente_data = df[df[columna_encontrada].str.lstrip('0') == cliente_str_sin_ceros]
            
            if cliente_data.empty:
                return None
        
        datos = cliente_data.iloc[0].to_dict()
    except Exception as e:
        raise ValueError(f"Error al buscar cliente: {str(e)}")
    
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
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    try:
        if not excel_data:
            return {
                'error': True,
                'message': 'Se requiere archivo Excel para buscar los datos del cliente'
            }
        
        excel_data.seek(0)
        df = pd.read_excel(excel_data)
        
        dats = buscar_cliente_en_excel(df, additional_data)
        if dats is None:
            return {
                'error': True,
                'message': f'La cuenta {additional_data} no existe en el archivo Excel'
            }
        
        # Texto bien formateado según el modelo
        TEXTO_NOTA = f"""
<b>__________________________________________________________________________________</b>
<font name="Times-Roman" size="10"><b>PARA:</b> ADMINISTRACIÓN / <b>DE:</b> GESTION Y MORA/ <b>ASUNTO:</b> AUTORIZACIÓN DE PAGO</font><br/><br/>

<font name="Times-Roman" size="10"><b>FECHA DE PRESENTACIÓN DE NOTA: {fecha_actual}</b></font><br/>
<b>__________________________________________________________________________________</b>

<font name="Times-Roman" size="8"><b>Cuenta: </b>{dats['nroCliente']}</font><br/>

<font name="Times-Roman" size="8"><b>Nombre:</b> {dats['Nombre']}</font><br/>

<font name="Times-Roman" size="8"><b>DNI: </b>{dats['dni']}</font><br/>
<b>__________________________________________________________________________________</b>

<font name="Times-Roman" size="8">Por medio de la presente solici
to, se autorice la acreditación de la transferencia adjunta para ser acreditada en la cuenta de 
referencia mencionada mas arriba, el pago de la misma fue realizado mediante transferencia bancaria <b>al BANCO 
MACRO</b> CTA Nº <b>3140000023459615</b> -</font><br/><br/>

<font name="Times-Roman" size="8">Sin más atte.</font>
"""
        # Configurar fuente Times New Roman
        try:
            pdfmetrics.registerFont(TTFont('Times-Roman', 'Times New Roman.ttf'))
            pdfmetrics.registerFont(TTFont('Times-Bold', 'Times New Roman Bold.ttf'))
            font_name = 'Times-Roman'
        except:
            # Fallback a Helvetica si Times New Roman no está disponible
            font_name = 'Helvetica'

        # Procesar imagen/PDF de entrada
        if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith('.pdf'):
            image = pdf_to_image(image_or_pdf_file)
        else:
            image = Image.open(image_or_pdf_file)

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Configuración de formato con Paragraph
        left_margin = 50
        right_margin = 50
        top_margin = height - 50  # Ajustado para mejor posicionamiento
        available_width = width - left_margin - right_margin
        
        # Estilo personalizado para Times New Roman
        styles = getSampleStyleSheet()
        custom_style = ParagraphStyle(
            name='Custom',
            parent=styles['Normal'],
            fontName='Times-Roman',
            fontSize=12,  # Tamaño más grande para coincidir con el documento
            leading=14,   # Interlineado ligeramente mayor
            spaceBefore=12,
            spaceAfter=12,
            alignment=4   # Texto justificado
        )
        
        # Crear frame para el texto
        frame = Frame(
            left_margin, 100,
            available_width, top_margin - 100,
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0,
            showBoundary=0
        )
        
        # Convertir texto a Paragraph y añadir al frame
        story = [Paragraph(TEXTO_NOTA, custom_style)]
        frame.addFromList(story, c)

        # Procesar y añadir imagen
        image_width, image_height = image.size
        max_image_width = width * 0.6
        ratio = max_image_width / image_width
        resized_height = image_height * ratio
        
        image_resized = image.resize((int(max_image_width), int(resized_height)))
        img_io = io.BytesIO()
        image_resized.save(img_io, format="PNG")
        img_io.seek(0)

        # Posición de la imagen (debajo del texto)
        c.drawImage(
            ImageReader(img_io),
            x=(width - max_image_width) / 2,
            y=50,
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