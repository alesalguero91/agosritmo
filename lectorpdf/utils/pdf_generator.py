from PIL import Image, ImageOps, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import fitz  # PyMuPDF
import io
import pandas as pd
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from datetime import datetime
import tempfile
import os

def pdf_to_ultra_quality_image(pdf_file):
    """Convierte PDF a imagen con calidad ultra HD"""
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(0)
    
    # Configuración profesional para máxima fidelidad
    zoom = 4  # Supermuestreo 4x
    mat = fitz.Matrix(zoom, zoom)
    
    pix = page.get_pixmap(
        matrix=mat,
        dpi=1200,  # Resolución extremadamente alta
        colorspace=fitz.csRGB,
        alpha=False,
        annots=False
    )
    
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Mejorar contraste y nitidez
    if img.mode == 'RGB':
        img = ImageOps.autocontrast(img, cutoff=2)
        img = img.filter(ImageFilter.SHARPEN)
    
    return img

def buscar_cliente_en_excel(df, cliente_id):
    """Busca cliente en Excel con manejo robusto"""
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
    """Genera PDF profesional con texto e imagen en máxima calidad"""
    try:
        # Validación de Excel
        if not excel_data:
            return {'error': True, 'message': 'Se requiere archivo Excel'}
        
        excel_data.seek(0)
        df = pd.read_excel(excel_data)
        dats = buscar_cliente_en_excel(df, additional_data)
        if not dats:
            return {'error': True, 'message': f'Cuenta {additional_data} no existe'}

        # Procesamiento de imagen/PDF con calidad ultra
        if hasattr(image_or_pdf_file, 'name') and image_or_pdf_file.name.lower().endswith('.pdf'):
            img = pdf_to_ultra_quality_image(image_or_pdf_file)
        else:
            img = Image.open(image_or_pdf_file)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Mejorar calidad para imágenes escaneadas
            if img.width > 2000 or img.height > 2000:
                img = ImageOps.autocontrast(img, cutoff=3)
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

        # Crear PDF con configuración premium
        buffer = io.BytesIO()
        
        try:
            c = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
            width, height = A4

            # Configuración de texto profesional
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

            # Frame para texto
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

            # Procesamiento de imagen
            img_width, img_height = img.size
            max_width = width * 0.85
            max_height = height * 0.45
            
            ratio = min(max_width/img_width, max_height/img_height)
            final_width = img_width * ratio
            final_height = img_height * ratio

            # Usar archivo temporal
            temp_file = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    img.save(tmp_file.name, format='PNG', compress_level=0, dpi=(600, 600))
                    temp_file = tmp_file.name
                
                # Insertar imagen
                c.drawImage(
                    temp_file,
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
                
                return {'error': False, 'pdf': buffer}
                
            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                    
        except Exception as e:
            if 'buffer' in locals():
                buffer.close()
            raise e
            
    except Exception as e:
        import traceback
        print(f"Error en generación de PDF: {str(e)}\n{traceback.format_exc()}")
        return {'error': True, 'message': f'Error al generar PDF: {str(e)}'}
      