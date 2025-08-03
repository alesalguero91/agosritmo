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
    """Convierte PDF a imagen con calidad profesional (1200 DPI)"""
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(0)
    # Configuración profesional para máxima calidad
    pix = page.get_pixmap(
        dpi=1200,  # Resolución ultra alta
        colorspace=fitz.csRGB,  # Espacio de color RGB
        alpha=False,  # Sin canal alpha
        annots=False,  # Ignorar anotaciones
        matrix=fitz.Matrix(2, 2)  # Supermuestreo 2x
    )
    img_data = pix.tobytes("png")
    return Image.open(io.BytesIO(img_data))

def buscar_cliente_en_excel(df, cliente_id):
    """Busca cliente en Excel (sin cambios)"""
    df.columns = df.columns.str.lower().str.strip()
    cliente_str = str(cliente_id).strip()
    
    posibles_columnas = ['cuenta', 'nro cuenta', 'nro de cuenta', 'numero cuenta', 
                       'numero de cuenta', 'cliente', 'nrocliente', 'numerocliente', 
                       'nro cliente', 'numero cliente', 'idcliente', 'id']
    
    columna_encontrada = next((col for col in posibles_columnas if col in df.columns), None)
    
    if not columna_encontrada:
        raise ValueError("No se encontró columna de cuenta/cliente")
    
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
        raise ValueError("Faltan campos obligatorios (DNI/Nombre)")
    
    return {
        'nroCliente': str(datos[columna_encontrada]),
        'dni': dni,
        'Nombre': nombre
    }

def generar_pdf_con_texto_y_imagen(image_or_pdf_file, additional_data, excel_data=None):
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    try:
        # Validación de Excel
        if not excel_data:
            return {'error': True, 'message': 'Se requiere archivo Excel'}
        
        excel_data.seek(0)
        df = pd.read_excel(excel_data)
        dats = buscar_cliente_en_excel(df, additional_data)
        if not dats:
            return {'error': True, 'message': f'Cuenta {additional_data} no existe'}

        # Texto original (sin cambios)
        TEXTO_NOTA = f"""
<b>__________________________________________________________________________________</b>
<font name="Times-Roman" size="10"><b>PARA:</b> ADMINISTRACIÓN / <b>DE:</b> GESTION Y MORA/ <b>ASUNTO:</b> AUTORIZACIÓN DE PAGO</font><br/><br/>

<font name="Times-Roman" size="10"><b>FECHA DE PRESENTACIÓN DE NOTA: {fecha_actual}</b></font><br/>
<b>__________________________________________________________________________________</b>

<font name="Times-Roman" size="8"><b>Cuenta: </b>{dats['nroCliente']}</font><br/>

<font name="Times-Roman" size="8"><b>Nombre:</b> {dats['Nombre']}</font><br/>

<font name="Times-Roman" size="8"><b>DNI: </b>{dats['dni']}</font><br/>
<b>__________________________________________________________________________________</b><br/>

<font name="Times-Roman" size="8">Por medio de la presente solicito, se autorice la acreditación de la transferencia adjunta para ser acreditada en la cuenta de 
referencia mencionada mas arriba, el pago de la misma fue realizado mediante transferencia bancaria <b>al BANCO 
MACRO</b> CTA Nº <b>3140000023459615</b> -</font><br/><br/>

<font name="Times-Roman" size="8">Sin más atte.</font>
"""
        # Configurar fuente
        try:
            pdfmetrics.registerFont(TTFont('Times-Roman', 'Times New Roman.ttf'))
            font_name = 'Times-Roman'
        except:
            font_name = 'Helvetica'

        # Procesamiento de imagen/PDF con calidad profesional
        if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith('.pdf'):
            image = pdf_to_image(image_or_pdf_file)
        else:
            image = Image.open(image_or_pdf_file)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            # Preservar metadatos de calidad
            image.info['quality'] = 100
            image.info['dpi'] = (300, 300)

        # Crear PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Configuración de texto
        styles = getSampleStyleSheet()
        custom_style = ParagraphStyle(
            name='Custom',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=12,
            spaceBefore=6,
            spaceAfter=6,
            alignment=4
        )

        # Frame para texto (posición optimizada)
        frame = Frame(
            50, height - 350, width - 100, 300, showBoundary=0
        )
        story = [Paragraph(TEXTO_NOTA, custom_style)]
        frame.addFromList(story, c)

        # Procesamiento de imagen con máxima calidad
        original_width, original_height = image.size
        max_width = width * 0.8
        max_height = height * 0.5
        
        if original_width <= max_width and original_height <= max_height:
            # Usar tamaño original si es posible
            final_width, final_height = original_width, original_height
            img_final = image
        else:
            # Redimensionamiento profesional
            ratio = min(max_width/original_width, max_height/original_height)
            final_width = int(original_width * ratio)
            final_height = int(original_height * ratio)
            img_final = image.resize(
                (final_width, final_height),
                Image.Resampling.LANCZOS,
                reducing_gap=3.0
            )

        # Guardar imagen temporal con máxima calidad
        temp_img = io.BytesIO()
        if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith(('.jpg', '.jpeg')):
            img_final.save(temp_img, format='JPEG', 
                         quality=100,
                         subsampling=0,
                         dpi=(300, 300))
        else:
            img_final.save(temp_img, format='PNG',
                         compress_level=0,
                         dpi=(300, 300))
        temp_img.seek(0)

        # Dibujar imagen en PDF (posición Y=150)
        c.drawImage(
            ImageReader(temp_img),
            x=(width - final_width)/2,
            y=150,  # Posición ajustada
            width=final_width,
            height=final_height,
            preserveAspectRatio=True,
            mask='auto',
            anchor='c'
        )

        c.showPage()
        c.save()
        buffer.seek(0)

        return {'error': False, 'pdf': buffer}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {'error': True, 'message': f'Error al generar PDF: {str(e)}'}
    
    

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