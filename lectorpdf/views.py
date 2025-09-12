from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import PDFUploadSerializer, ExcelUploadSerializer
from .utils.pdf_processing import process_pdf_or_image
from django.http import HttpResponse, FileResponse
from .utils.pdf_generator import generar_pdf_con_texto_y_imagen
import pandas as pd
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.parsers import MultiPartParser, FormParser
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def subir_archivo_view(request):
    return render(request, "lectorpdf/lectorpdf.html")

class PDFUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Request data: {request.data}")
            logger.info(f"Files in request: {request.FILES}")
            
            if 'pdf_file' not in request.FILES:
                logger.error("No file found in request.FILES")
                return Response(
                    {'error': 'No file was submitted'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Validation error: {serializer.errors}")
                return Response(
                    serializer.errors, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = serializer.validated_data['pdf_file']
            logger.info(f"File received: {file.name}, size: {file.size}")
            
            data = process_pdf_or_image(file)
            
            logger.info(f"Extracted text: {data.get('full_text')}")
            
            return Response({
                'text': data.get('full_text', ''),
                'financial_data': data.get('financial_data', {})
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in PDFUploadView: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        

class NotaGeneradaView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        try:
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Errores de serializador: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['pdf_file']
            numero_cliente = serializer.validated_data.get('additional_data')
            excel_file = request.FILES.get('excel_file')
            
            if not excel_file:
                logger.error("No se proporcionó archivo Excel")
                return Response(
                    {'error': 'Debe proporcionar un archivo Excel'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            texto_extraido = process_pdf_or_image(file)
            logger.info(f"Texto extraído del archivo: {texto_extraido}")
            
            try:
                df = pd.read_excel(excel_file)
                df.columns = df.columns.str.lower().str.strip()
                
                cliente_info = df[df['cuenta'].replace(" ","") == str(numero_cliente).replace(" ","")].iloc[0]
                nombre_cliente = cliente_info['nombre']
                dni_cliente = cliente_info.get('dni', '')
                
                nombre_cliente = re.sub(r'[\\/*?:"<>|]', '', nombre_cliente).strip()
                nombre_cliente = nombre_cliente.replace(' ', '_')[:50]
                dni_cliente = str(dni_cliente).strip()
            except Exception as e:
                logger.error(f"Error al obtener datos del cliente: {str(e)}")
                nombre_cliente = "cliente"
                dni_cliente = ""
            
            resultado = generar_pdf_con_texto_y_imagen(
                file, 
                numero_cliente,
                excel_data=excel_file
            )
            
            if resultado.get('error'):
                logger.error(f"Error al generar PDF: {resultado.get('message')}")
                return Response(
                    {'error': resultado['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            fecha_actual = datetime.now().strftime("%Y%m%d")
            nombre_archivo = f"Nota_{numero_cliente}_{dni_cliente}_{nombre_cliente}_{fecha_actual}.pdf"
            
            response = HttpResponse(
                resultado['pdf'],
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
            
            return response
            
        except Exception as e:
            logger.error(f"Error en NotaGeneradaView: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error al procesar la solicitud'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ExcelUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        try:
            serializer = ExcelUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            excel_file = serializer.validated_data['excel_file']
            df = pd.read_excel(excel_file)
            df.columns = df.columns.str.lower().str.strip()
            
            required_columns = {'cuenta', 'dni', 'nombre'}
            if not required_columns.issubset(set(df.columns)):
                missing = required_columns - set(df.columns)
                return Response(
                    {'error': f'Faltan columnas: {missing}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'message': 'Excel procesado',
                'data': df.to_dict('records'),
                'columns': list(df.columns)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error en ExcelUploadView: {str(e)}")
            return Response(
                {'error': 'Error al procesar Excel'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )