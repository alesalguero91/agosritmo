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

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def subir_archivo_view(request):
    return render(request, "lectorpdf/lectorpdf.html")

class PDFUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        try:
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Error de validación: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['pdf_file']
            additional_data = serializer.validated_data.get('additional_data')
            
            data = process_pdf_or_image(file, additional_data=additional_data)
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error en PDFUploadView: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NotaGeneradaView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        try:
            serializer = PDFUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Errores de serializador: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['pdf_file']
            additional_data = serializer.validated_data.get('additional_data')
            excel_file = request.FILES.get('excel_file')
            
            if not excel_file:
                logger.error("No se proporcionó archivo Excel")
                return Response(
                    {'error': 'Debe proporcionar un archivo Excel'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            resultado = generar_pdf_con_texto_y_imagen(
                file, 
                additional_data,
                excel_data=excel_file
            )
            
            if resultado.get('error'):
                logger.error(f"Error al generar PDF: {resultado.get('message')}")
                return Response(
                    {'error': resultado['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            response = FileResponse(
                resultado['pdf'],
                content_type='application/pdf',
                headers={
                    'Content-Disposition': 'attachment; filename="nota_generada.pdf"',
                    'Access-Control-Expose-Headers': 'Content-Disposition'
                }
            )
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


"""    
class NotaGeneradaViewEnWord(APIView):
    def post(self, request):
        serializer = PDFUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['pdf_file']
            try:
                # Generar documento Word en lugar de PDF
                nuevo_docx = generar_word_con_texto_y_imagen(file)
                return HttpResponse(
                    nuevo_docx.getvalue(),
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    headers={'Content-Disposition': 'attachment; filename="nota_generada.docx"'}
                )
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

"""