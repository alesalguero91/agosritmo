from PIL import Image, ImageOps
import fitz 
import pytesseract
import io
import re
import logging
import traceback



logger = logging.getLogger(__name__)

def convert_image_to_pdf(image_file):
    try:
        image_file.seek(0)
        image = Image.open(image_file)
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        
        output = io.BytesIO()
        image.save(output, format='PDF', quality=100)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error en convert_image_to_pdf: {str(e)}")
        raise

def extract_text_from_pdf(pdf_file):
    try:
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        if len(doc) == 0:
            raise ValueError("PDF vacío")
            
        text = ""
        for page in doc:
            text += page.get_text() or ""
        return text.strip()
    except Exception as e:
        logger.error(f"Error en extract_text_from_pdf: {str(e)}")
        raise

def perform_ocr_on_pdf(pdf_file, lang='spa'):
    try:
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        if len(doc) == 0:
            raise ValueError("PDF vacío")
            
        text = ""
        for page in doc:
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Mejorar calidad de imagen para OCR
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            image = ImageOps.autocontrast(image)
            text += pytesseract.image_to_string(image, lang=lang) + "\n"
            
        return text.strip()
    except Exception as e:
        logger.error(f"Error en perform_ocr_on_pdf: {str(e)}")
        raise

def extract_financial_data(text):
    if not text:
        return {'amount': None, 'cbu_cvu': None}
    
    amount_patterns = [
        r'(?:importe|monto|total)\s*[:=]?\s*\$\s*([\d.,]+)',  # "Importe: $1.234,56"
        r'(?:importe|monto|total)\s*[:=]?\s*([\d.,]+)',       # "Monto 1.234,56"
        r'\$\s*([\d.,]+)',                                    # "$ 1.234,56"
        r'(?<!\d)(\d{1,3}(?:\.?\d{3})*(?:,\d{2})?)(?!\d)'    # "1.234,56" o "1234,56"
    ]
    
    amount = None
    for pattern in amount_patterns:
        amount_match = re.search(pattern, text, re.IGNORECASE)
        if amount_match:
            amount_str = amount_match.group(1)
            try:
                # Normalización del formato numérico
                amount_str = amount_str.replace('.', '').replace(',', '.')
                amount = float(amount_str)
                break  # Nos quedamos con la primera coincidencia válida
            except ValueError:
                continue

    cbu_cvu_match = re.search(r'(\d[\d\s]{20,}\d)', text.replace('\n', ' '))
    if cbu_cvu_match:
        cbu_cvu = ''.join(filter(str.isdigit, cbu_cvu_match.group(1)))
        cbu_cvu = cbu_cvu if len(cbu_cvu) == 22 else None
    else:
        cbu_cvu = None

    return {
        'amount': float(amount) if amount else None,
        'cbu_cvu': cbu_cvu
    }

def process_pdf_or_image(file):
    """
    Procesa archivo PDF o imagen para extraer texto y datos financieros
    """
    try:
        is_pdf = (
            hasattr(file, 'content_type') and file.content_type == 'application/pdf'
        ) or (
            hasattr(file, 'name') and file.name.lower().endswith('.pdf')
        )

        # Convertir imagen a PDF si es necesario
        if not is_pdf:
            file = convert_image_to_pdf(file)
        else:
            # Si es PDF, crear una copia para no modificar el original
            file_content = file.read()
            file = io.BytesIO(file_content)
            file.seek(0)

        # Primero intentar extracción directa de texto
        text = extract_text_from_pdf(file)

        # Si no se extrajo texto, intentar OCR
        if not text.strip():
            file.seek(0)
            text = perform_ocr_on_pdf(file)

        if not text.strip():
            raise ValueError("No se pudo extraer texto del archivo.")

        # Extraer datos financieros
        financial_data = extract_financial_data(text)

        return {
            'full_text': text,
            'financial_data': financial_data
        }

    except Exception as e:
        logger.error(f"Error en process_pdf_or_image: {str(e)}\n{traceback.format_exc()}")
        raise ValueError(f"Error procesando archivo: {str(e)}")