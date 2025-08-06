from PIL import Image, ImageEnhance, ImageFilter
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
import logging

logger = logging.getLogger(__name__)

def pdf_to_image(pdf_file):
    """Convierte PDF a imagen con calidad adecuada"""
    try:
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return img
    except Exception as e:
        logger.error(f"Error al convertir PDF a imagen: {str(e)}")
        raise

def mejorar_imagen(img):
    """Aplica mejoras moderadas a la imagen"""
    try:
        # Convertir a RGB si es necesario
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Mejorar contraste moderadamente
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)  # Aumento moderado del 20%
        
        # Aplicar suavizado ligero
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    except Exception as e:
        logger.error(f"Error al mejorar imagen: {str(e)}")
        return img

def buscar_cliente_en_excel(df, cliente_id):
    """Busca cliente en Excel (código original)"""
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
        
        TEXTO_NOTA = f"""
<b>_________________________________________________________________________________________</b>
<font name="Times-Roman" size="10"><b>PARA:</b> ADMINISTRACIÓN / <b>DE:</b> GESTION Y MORA/ <b>ASUNTO:</b> AUTORIZACIÓN DE PAGO</font><br/><br/>

<font name="Times-Roman" size="10"><b>FECHA DE PRESENTACIÓN DE NOTA: {fecha_actual}</b></font><br/>
<b>_________________________________________________________________________________________</b>

<font name="Times-Roman" size="8"><b>Cuenta: </b>{dats['nroCliente']}</font><br/>

<font name="Times-Roman" size="8"><b>Nombre:</b> {dats['Nombre']}</font><br/>

<font name="Times-Roman" size="8"><b>DNI: </b>{dats['dni']}</font><br/>
<b>_________________________________________________________________________________________</b>

<font name="Times-Roman" size="8">Por medio de la presente solicito, se autorice la acreditación de la transferencia adjunta para ser acreditada en la cuenta de 
referencia mencionada mas arriba, el pago de la misma fue realizado mediante transferencia bancaria <b>al BANCO 
MACRO</b> CTA Nº <b>3140000023459615</b> -</font><br/><br/>

<font name="Times-Roman" size="8">Sin más atte.</font>
"""
        try:
            pdfmetrics.registerFont(TTFont('Times-Roman', 'Times New Roman.ttf'))
            pdfmetrics.registerFont(TTFont('Times-Bold', 'Times New Roman Bold.ttf'))
            font_name = 'Times-Roman'
        except:
            font_name = 'Helvetica'

        # Procesar imagen/PDF
        if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith('.pdf'):
            image = pdf_to_image(image_or_pdf_file)
        else:
            image = Image.open(image_or_pdf_file)
            image = mejorar_imagen(image)

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        left_margin = 50
        right_margin = 50
        available_width = width - left_margin - right_margin
        
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

        frame = Frame(
            left_margin, height - 350,
            available_width, 300,
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0,
            showBoundary=0
        )
        
        story = [Paragraph(TEXTO_NOTA, custom_style)]
        frame.addFromList(story, c)

        # Insertar imagen
        image_width, image_height = image.size
        max_image_width = width * 0.8
        max_image_height = height * 0.5
        
        ratio = min(max_image_width / image_width, max_image_height / image_height)
        resized_width = image_width * ratio
        resized_height = image_height * ratio
        
        image_y = 120

        img_io = io.BytesIO()
        image.save(img_io, format="PNG", quality=90)
        img_io.seek(0)
        
        c.drawImage(
            ImageReader(img_io),
            x=(width - resized_width) / 2,
            y=image_y,
            width=resized_width,
            height=resized_height,
            preserveAspectRatio=True,
            mask='auto'
        )

        c.showPage()
        c.save()
        buffer.seek(0)

        return {
            'error': False,
            'pdf': buffer
        }
        
    except Exception as e:
        logger.error(f"Error al generar PDF: {str(e)}")
        return {
            'error': True,
            'message': f'Error al generar PDF: {str(e)}'
        }