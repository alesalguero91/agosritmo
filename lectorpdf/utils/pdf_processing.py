# documentos/utils/pdf_processing.py

from PIL import Image
import fitz  # PyMuPDF
import pytesseract
import io
import re

def convert_image_to_pdf(image_file):
    image = Image.open(image_file)
    rgb_image = image.convert('RGB')
    output = io.BytesIO()
    rgb_image.save(output, format='PDF')
    output.seek(0)
    return output

def extract_text_from_pdf(pdf_file):
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def perform_ocr_on_pdf(pdf_file, lang='spa'):
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        text += pytesseract.image_to_string(image, lang=lang) + "\n"
    return text

def extract_financial_data(text):
    amount_match = re.search(r'\$\s*([\d.,]+)', text)
    amount = amount_match.group(1).replace('.', '').replace(',', '.') if amount_match else None

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
    is_pdf = (
        hasattr(file, 'content_type') and file.content_type == 'application/pdf'
    ) or (
        hasattr(file, 'name') and file.name.lower().endswith('.pdf')
    )

    if not is_pdf:
        file = convert_image_to_pdf(file)

    text = extract_text_from_pdf(file)

    if not text.strip():
        file.seek(0)
        text = perform_ocr_on_pdf(file)

    if not text.strip():
        raise ValueError("No se pudo extraer texto del archivo.")

    financial_data = extract_financial_data(text)

    return {
        'full_text': text,
        'financial_data': financial_data
    }
