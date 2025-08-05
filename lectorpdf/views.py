from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import PDFUploadSerializer
from .utils.pdf_processing import process_pdf_or_image
from .utils.pdf_generator import generar_pdf_con_texto_y_imagen
from rest_framework.parsers import MultiPartParser, FormParser
import logging
import re
from django.utils.text import get_valid_filename
import traceback
from django.views.decorators.csrf import ensure_csrf_cookie
import pandas as pd
import tempfile
import os

logger = logging.getLogger(__name__)

def limpiar_nombre_archivo(nombre_archivo):
    """Limpia el nombre del archivo eliminando caracteres especiales"""
    nombre_limpiado = re.sub(r'\([^)]*\)', '', nombre_archivo)
    return get_valid_filename(nombre_limpiado)

@ensure_csrf_cookie
def subir_archivo_view(request):
    return render(request, "lectorpdf/lectorpdf.html")

class ProcesarNotaView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        # Configuración para Render
        temp_dir = tempfile.gettempdir()
        temp_files = []
        
        try:
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['pdf_file']
            file.name = limpiar_nombre_archivo(file.name)
            
            # Crear archivos temporales en el directorio configurado
            temp_pdf1 = tempfile.NamedTemporaryFile(dir=temp_dir, suffix='.pdf', delete=False)
            temp_pdf2 = tempfile.NamedTemporaryFile(dir=temp_dir, suffix='.pdf', delete=False)
            temp_files.extend([temp_pdf1.name, temp_pdf2.name])
            
            # Guardar contenido en archivos temporales
            for chunk in file.chunks():
                temp_pdf1.write(chunk)
                temp_pdf2.write(chunk)
            temp_pdf1.close()
            temp_pdf2.close()
            
            # Procesar primera copia para extracción de texto
            with open(temp_pdf1.name, 'rb') as f1:
                texto_extraido = process_pdf_or_image(f1)
            
            # Procesar Excel
            excel_file = request.FILES.get('excel_file')
            if not excel_file:
                raise ValueError("Debe proporcionar un archivo Excel")
            
            temp_excel = tempfile.NamedTemporaryFile(dir=temp_dir, suffix='.xlsx', delete=False)
            for chunk in excel_file.chunks():
                temp_excel.write(chunk)
            temp_excel.close()
            temp_files.append(temp_excel.name)
            
            with open(temp_excel.name, 'rb') as excel_copy:
                df = pd.read_excel(excel_copy)
                df.columns = df.columns.str.lower().str.strip()
                
                numero_cliente = serializer.validated_data.get('additional_data')
                try:
                    cliente_info = df[df['cuenta'] == int(numero_cliente)].iloc[0]
                    nombre_cliente = cliente_info['nombre']
                    dni_cliente = cliente_info.get('dni', '')
                except IndexError:
                    raise ValueError(f"Cliente {numero_cliente} no encontrado")

            # Generar PDF con segunda copia
            with open(temp_pdf2.name, 'rb') as f2, open(temp_excel.name, 'rb') as excel_copy:
                resultado = generar_pdf_con_texto_y_imagen(f2, numero_cliente, excel_copy)

            if resultado.get('error'):
                raise ValueError(resultado['message'])

            return Response({
                'pdf': resultado['pdf'],
                'text_data': {
                    'text': texto_extraido.get('full_text', ''),
                    'financial_data': texto_extraido.get('financial_data', {})
                },
                'cliente_data': {
                    'nombre': nombre_cliente,
                    'dni': dni_cliente
                }
            })

        except Exception as e:
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Limpieza garantizada de archivos temporales
            for filepath in temp_files:
                try:
                    if os.path.exists(filepath):
                        os.unlink(filepath)
                except Exception as e:
                    logger.error(f"Error eliminando temporal {filepath}: {str(e)}")