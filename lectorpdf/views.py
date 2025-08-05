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
import io
import tempfile
import os

logger = logging.getLogger(__name__)

def limpiar_nombre_archivo(nombre_archivo):
    """Elimina paréntesis y su contenido, y caracteres inválidos del nombre del archivo."""
    nombre_limpiado = re.sub(r'\([^)]*\)', '', nombre_archivo)
    nombre_limpiado = get_valid_filename(nombre_limpiado)
    return nombre_limpiado.strip()

@ensure_csrf_cookie
def subir_archivo_view(request):
    return render(request, "lectorpdf/lectorpdf.html")

class ProcesarNotaView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        # Variables para manejo de archivos temporales
        temp_files = []
        file_copy1 = None
        file_copy2 = None
        excel_copy = None
        
        try:
            logger.info("Iniciando procesamiento completo de nota...")
            
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Errores de validación: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['pdf_file']
            file.name = limpiar_nombre_archivo(file.name)
            
            # Crear copias temporales en disco para evitar problemas de lectura
            temp_pdf1 = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_pdf2 = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_files.extend([temp_pdf1.name, temp_pdf2.name])
            
            # Guardar el contenido del PDF en los archivos temporales
            for chunk in file.chunks():
                temp_pdf1.write(chunk)
                temp_pdf2.write(chunk)
            temp_pdf1.close()
            temp_pdf2.close()
            
            # Abrir las copias para procesamiento
            file_copy1 = open(temp_pdf1.name, 'rb')
            file_copy2 = open(temp_pdf2.name, 'rb')
            temp_files.extend([file_copy1, file_copy2])
            
            numero_cliente = serializer.validated_data.get('additional_data')
            excel_file = request.FILES.get('excel_file')
            
            if not excel_file:
                logger.error("Archivo Excel no proporcionado")
                return Response(
                    {'error': 'Debe proporcionar un archivo Excel'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear copia temporal del Excel
            temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            for chunk in excel_file.chunks():
                temp_excel.write(chunk)
            temp_excel.close()
            excel_copy = open(temp_excel.name, 'rb')
            temp_files.extend([temp_excel.name, excel_copy])
            
            # Procesar archivo para extraer texto (usando la primera copia)
            logger.info("Extrayendo texto del archivo...")
            file_copy1.seek(0)
            texto_extraido = process_pdf_or_image(file_copy1)
            
            # Procesar Excel para datos del cliente
            logger.info("Procesando archivo Excel...")
            excel_copy.seek(0)
            df = pd.read_excel(excel_copy)
            df.columns = df.columns.str.lower().str.strip()
            
            try:
                cliente_info = df[df['cuenta'] == int(numero_cliente)].iloc[0]
                nombre_cliente = cliente_info['nombre']
                dni_cliente = cliente_info.get('dni', '')
            except IndexError:
                logger.error(f"Cliente {numero_cliente} no encontrado en Excel")
                return Response(
                    {'error': f'Cliente {numero_cliente} no encontrado en el archivo Excel'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generar PDF (usando la segunda copia)
            logger.info("Generando PDF...")
            file_copy2.seek(0)
            excel_copy.seek(0)
            resultado = generar_pdf_con_texto_y_imagen(file_copy2, numero_cliente, excel_copy)
            
            if resultado.get('error'):
                logger.error(f"Error al generar PDF: {resultado['message']}")
                return Response(
                    {'error': resultado['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info("Procesamiento completado exitosamente")
            
            # Crear respuesta
            response_data = {
                'pdf': resultado['pdf'],
                'text_data': {
                    'text': texto_extraido.get('full_text', ''),
                    'financial_data': texto_extraido.get('financial_data', {})
                },
                'cliente_data': {
                    'nombre': nombre_cliente,
                    'dni': dni_cliente
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error en ProcesarNotaView: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {'error': f'Error al procesar la solicitud: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Limpieza segura de recursos
            for resource in temp_files:
                try:
                    if hasattr(resource, 'close'):
                        resource.close()
                except Exception as e:
                    logger.error(f"Error al cerrar recurso: {str(e)}")
            
            # Eliminar archivos temporales
            for filepath in [f for f in temp_files if isinstance(f, str)]:
                try:
                    if os.path.exists(filepath):
                        os.unlink(filepath)
                except Exception as e:
                    logger.error(f"Error al eliminar archivo temporal {filepath}: {str(e)}")