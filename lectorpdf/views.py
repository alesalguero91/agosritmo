from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import PDFUploadSerializer, ExcelUploadSerializer
from .utils.pdf_processing import process_pdf_or_image
from django.http import HttpResponse
from .utils.pdf_generator import generar_pdf_con_texto_y_imagen
import pandas as pd
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def subir_archivo_view(request):
#    return render(request, 'lectorpdf/lectorpdf.html', status=200)
    return render(request, "lectorpdf/lectorpdf.html")

class PDFUploadView(APIView):
    def post(self, request):
        serializer = PDFUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['pdf_file']
            additional_data = serializer.validated_data.get('additional_data', None)
            
            try:
                data = process_pdf_or_image(file, additional_data=additional_data)
                return Response(data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NotaGeneradaView(APIView):
    def post(self, request):
        print("Datos recibidos:", request.data)
        print("Archivos recibidos:", request.FILES)
        
        serializer = PDFUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['pdf_file']
            additional_data = serializer.validated_data.get('additional_data', None)
            excel_file = request.FILES.get('excel_file', None)
            
            if not excel_file:
                return Response(
                    {'error': 'Debe proporcionar un archivo Excel con los datos de clientes'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                resultado = generar_pdf_con_texto_y_imagen(
                    file, 
                    additional_data,
                    excel_data=excel_file
                )
                
                if resultado.get('error'):
                    return Response(
                        {'error': resultado['message']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                response = HttpResponse(
                    resultado['pdf'],
                    content_type='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename="nota_generada.pdf"'}
                )
                return response
            
            except Exception as e:
                print(f"Error en NotaGeneradaView: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        print("Errores de serializador:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExcelUploadView(APIView):
    def post(self, request):
        serializer = ExcelUploadSerializer(data=request.data)
        if serializer.is_valid():
            excel_file = serializer.validated_data['excel_file']
            
            try:
                df = pd.read_excel(excel_file)
                df.columns = df.columns.str.lower().str.strip()
                print("Columnas encontradas:", df.columns.tolist())
                
                required_columns = {'cuenta', 'dni', 'nombre'}
                if not required_columns.issubset(set(df.columns)):
                    missing = required_columns - set(df.columns)
                    return Response(
                        {'error': f'Faltan columnas requeridas: {missing}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                data = df.to_dict('records')
                
                return Response({
                    'message': 'Archivo Excel procesado correctamente',
                    'data': data,
                    'columns': list(df.columns)
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                print(f"Error en ExcelUploadView: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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