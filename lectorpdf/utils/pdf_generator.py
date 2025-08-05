from PIL import Image, ImageOps, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import fitz
import io
import pandas as pd
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from datetime import datetime
import tempfile
import os
import base64
import logging
import traceback

logger = logging.getLogger(__name__)

def pdf_to_ultra_quality_image(pdf_file):
    try:
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        page = doc.load_page(0)
        
        zoom = 4
        mat = fitz.Matrix(zoom, zoom)
        
        pix = page.get_pixmap(
            matrix=mat,
            dpi=1200,
            colorspace=fitz.csRGB,
            alpha=False,
            annots=False
        )
        
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        if img.mode == 'RGB':
            img = ImageOps.autocontrast(img, cutoff=2)
            img = img.filter(ImageFilter.SHARPEN)
        
        return img
    except Exception as e:
        logger.error(f"Error en pdf_to_ultra_quality_image: {str(e)}")
        raise

def buscar_cliente_en_excel(df, cliente_id):
    try:
        df.columns = df.columns.str.lower().str.strip()
        cliente_str = str(cliente_id).strip()
        
        posibles_columnas = ['cuenta', 'nro cuenta', 'numero cuenta']
        columna_encontrada = next((col for col in posibles_columnas if col in df.columns), None)
        
        if not columna_encontrada:
            raise ValueError("No se encontró columna de cuenta/cliente")
        
        df[columna_encontrada] = df[columna_encontrada].astype(str).str.strip()
        cliente_data = df[df[columna_encontrada] == cliente_str]
        
        if cliente_data.empty:
            return None
        
        datos = cliente_data.iloc[0].to_dict()
        
        dni = next(str(datos[col]) for col in ['dni', 'documento'] if col in datos and pd.notna(datos[col]))
        nombre = next(str(datos[col]) for col in ['nombre', 'nombre completo'] if col in datos and pd.notna(datos[col]))
        
        return {
            'nroCliente': str(datos[columna_encontrada]),
            'dni': dni,
            'Nombre': nombre
        }
    except Exception as e:
        logger.error(f"Error en buscar_cliente_en_excel: {str(e)}")
        raise

def generar_pdf_con_texto_y_imagen(image_or_pdf_file, additional_data, excel_data=None):
    buffer = io.BytesIO()
    temp_file = None
    
    try:
        if not excel_data:
            return {'error': True, 'message': 'Se requiere archivo Excel'}
        
        excel_data.seek(0)
        df = pd.read_excel(excel_data)
        dats = buscar_cliente_en_excel(df, additional_data)
        if not dats:
            return {'error': True, 'message': f'Cuenta {additional_data} no existe'}

        if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith('.pdf'):
            img = pdf_to_ultra_quality_image(image_or_pdf_file)
        else:
            img = Image.open(image_or_pdf_file)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            if img.width > 2000 or img.height > 2000:
                img = ImageOps.autocontrast(img, cutoff=3)
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        styles = getSampleStyleSheet()
        custom_style = ParagraphStyle(
            name='Custom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            spaceBefore=6,
            spaceAfter=6,
            alignment=4
        )

        frame = Frame(
            40, height - 350, width - 80, 300,
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0,
            showBoundary=0
        )
        
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        TEXTO_NOTA = f"""
<b>___________________________________________________________________________________________</b>
<font name="Times-Roman" size="10"><b>PARA:</b> ADMINISTRACIÓN / <b>DE:</b> GESTION Y MORA/ <b>ASUNTO:</b> AUTORIZACIÓN DE PAGO</font><br/><br/>

<font name="Times-Roman" size="10"><b>FECHA DE PRESENTACIÓN DE NOTA: {fecha_actual}</b></font><br/>
<b>___________________________________________________________________________________________</b>

<font name="Times-Roman" size="8"><b>Cuenta: </b>{dats['nroCliente']}</font><br/>

<font name="Times-Roman" size="8"><b>Nombre:</b> {dats['Nombre']}</font><br/>

<font name="Times-Roman" size="8"><b>DNI: </b>{dats['dni']}</font><br/>
<b>___________________________________________________________________________________________</b>

<font name="Times-Roman" size="8">Por medio de la presente solicito, se autorice la acreditación de la transferencia adjunta para ser acreditada en la cuenta de 
referencia mencionada mas arriba, el pago de la misma fue realizado mediante transferencia bancaria <b>al BANCO 
MACRO</b> CTA Nº <b>3140000023459615</b> -</font><br/><br/>

<font name="Times-Roman" size="8">Sin más atte.</font>
"""
        story = [Paragraph(TEXTO_NOTA, custom_style)]
        frame.addFromList(story, c)

        img_width, img_height = img.size
        max_width = width * 0.85
        max_height = height * 0.45
        ratio = min(max_width/img_width, max_height/img_height)
        final_width = img_width * ratio
        final_height = img_height * ratio

        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name, format='PNG', compress_level=0, dpi=(600, 600))
        temp_file.close()
        
        c.drawImage(
            temp_file.name,
            x=(width - final_width)/2,
            y=120,
            width=final_width,
            height=final_height,
            preserveAspectRatio=True,
            mask='auto'
        )
        
        c.showPage()
        c.save()
        buffer.seek(0)
        
        pdf_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return {
            'error': False,
            'pdf': pdf_base64,
            'message': 'PDF generado correctamente'
        }
        
    except Exception as e:
        logger.error(f"Error en generar_pdf_con_texto_y_imagen: {str(e)}\n{traceback.format_exc()}")
        return {
            'error': True,
            'message': f'Error al generar PDF: {str(e)}'
        }
        
    finally:
        buffer.close()
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.error(f"Error al eliminar temporal: {str(e)}")