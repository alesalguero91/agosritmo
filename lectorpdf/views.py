from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import PDFUploadSerializer
from .utils.pdf_processing import process_pdf_or_image
from .utils.pdf_generator import generar_pdf_con_texto_y_imagen
from rest_framework.parsers import MultiPartParser, FormParser
import logging
from datetime import datetime
import re
from django.utils.text import get_valid_filename
import traceback
from django.views.decorators.csrf import ensure_csrf_cookie
import pandas as pd

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
        try:
            logger.info("Iniciando procesamiento completo de nota...")
            
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Errores de validación: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['pdf_file']
            file.name = limpiar_nombre_archivo(file.name)
            
            numero_cliente = serializer.validated_data.get('additional_data')
            excel_file = request.FILES.get('excel_file')
            
            if not excel_file:
                logger.error("Archivo Excel no proporcionado")
                return Response(
                    {'error': 'Debe proporcionar un archivo Excel'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Procesar archivo para extraer texto
            logger.info("Extrayendo texto del archivo...")
            texto_extraido = process_pdf_or_image(file)
            
            # Procesar Excel para datos del cliente
            logger.info("Procesando archivo Excel...")
            excel_file.seek(0)
            df = pd.read_excel(excel_file)
            df.columns = df.columns.str.lower().str.strip()
            
            cliente_info = df[df['cuenta'] == int(numero_cliente)].iloc[0]
            nombre_cliente = cliente_info['nombre']
            dni_cliente = cliente_info.get('dni', '')
            
            # Generar PDF
            logger.info("Generando PDF...")
            file.seek(0)
            excel_file.seek(0)
            resultado = generar_pdf_con_texto_y_imagen(file, numero_cliente, excel_file)
            
            if resultado.get('error'):
                logger.error(f"Error al generar PDF: {resultado['message']}")
                return Response(
                    {'error': resultado['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info("Procesamiento completado exitosamente")
            
            # Crear respuesta con todos los datos necesarios
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