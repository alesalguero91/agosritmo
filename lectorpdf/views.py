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
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
import sys

logger = logging.getLogger(__name__)

def limpiar_nombre_archivo(nombre_archivo):
    """Limpia el nombre del archivo eliminando caracteres especiales"""
    nombre_limpiado = re.sub(r'\([^)]*\)', '', nombre_archivo)
    return get_valid_filename(nombre_limpiado)

def validar_archivo(file):
    """Valida que el archivo no esté corrupto"""
    try:
        # Crear una copia en memoria para validación
        file_copy = io.BytesIO(file.read())
        file.seek(0)  # Reiniciar posición del archivo original
        
        # Verificar si es PDF
        if hasattr(file, 'name') and file.name.lower().endswith('.pdf'):
            try:
                file_copy.seek(0)
                reader = PdfReader(file_copy)
                if len(reader.pages) == 0:
                    raise ValueError("El PDF está vacío")
                if reader.is_encrypted:
                    # Intentar descifrar con contraseña vacía
                    if not reader.decrypt(''):
                        raise ValueError("PDF cifrado no soportado")
            except Exception as e:
                raise ValueError(f"PDF inválido: {str(e)}")
        else:
            # Validar como imagen
            try:
                file_copy.seek(0)
                img = Image.open(file_copy)
                img.verify()
                img.close()
            except Exception as e:
                raise ValueError(f"Imagen inválida: {str(e)}")
        
        file_copy.seek(0)
        file_copy.close()
        return True
    except Exception as e:
        logger.error(f"Error validando archivo: {str(e)}")
        raise

@ensure_csrf_cookie
def subir_archivo_view(request):
    return render(request, "lectorpdf/lectorpdf.html")

class ProcesarNotaView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        file_copy1 = file_copy2 = excel_copy = None
        try:
            logger.info("Iniciando procesamiento de archivo...")
            
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Error validación: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['pdf_file']
            file.name = limpiar_nombre_archivo(file.name)
            
            # Validar archivo antes de procesar
            try:
                validar_archivo(file)
            except ValueError as e:
                logger.error(f"Archivo inválido: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear copias independientes para procesamiento
            file_content = file.read()
            file_copy1 = io.BytesIO(file_content)
            file_copy2 = io.BytesIO(file_content)
            file.seek(0)
            
            # Procesar texto (primera copia)
            file_copy1.seek(0)
            try:
                texto_extraido = process_pdf_or_image(file_copy1)
            except Exception as e:
                logger.error(f"Error procesando archivo: {str(e)}")
                return Response(
                    {'error': f'Error procesando archivo: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Procesar Excel
            excel_file = request.FILES.get('excel_file')
            if not excel_file:
                logger.error("Excel no proporcionado")
                return Response(
                    {'error': 'Debe proporcionar un archivo Excel'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_content = excel_file.read()
            excel_copy = io.BytesIO(excel_content)
            
            try:
                df = pd.read_excel(excel_copy)
                df.columns = df.columns.str.lower().str.strip()
                
                numero_cliente = serializer.validated_data.get('additional_data')
                if not numero_cliente:
                    raise ValueError("Número de cliente no proporcionado")
                
                try:
                    cliente_info = df[df['cuenta'] == int(numero_cliente)].iloc[0]
                    nombre_cliente = cliente_info['nombre']
                    dni_cliente = cliente_info.get('dni', '')
                except IndexError:
                    logger.error(f"Cliente {numero_cliente} no encontrado")
                    return Response(
                        {'error': f'Cliente {numero_cliente} no encontrado en Excel'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                logger.error(f"Error procesando Excel: {str(e)}")
                return Response(
                    {'error': f'Error procesando archivo Excel: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generar PDF (segunda copia)
            file_copy2.seek(0)
            excel_copy.seek(0)
            try:
                resultado = generar_pdf_con_texto_y_imagen(file_copy2, numero_cliente, excel_copy)
            except Exception as e:
                logger.error(f"Error generando PDF: {str(e)}\n{traceback.format_exc()}")
                return Response(
                    {'error': f'Error generando PDF: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            if resultado.get('error'):
                logger.error(f"Error generando PDF: {resultado['message']}")
                return Response(
                    {'error': resultado['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info("Procesamiento completado exitosamente")
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
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error interno: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {'error': f'Error interno del servidor: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Cerrar todos los buffers
            for buffer in [file_copy1, file_copy2, excel_copy]:
                try:
                    if buffer and not buffer.closed:
                        buffer.close()
                except Exception:
                    pass