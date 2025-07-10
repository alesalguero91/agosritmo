from django.urls import path
from .views import PDFUploadView, NotaGeneradaView, subir_archivo_view, ExcelUploadView

urlpatterns = [
    path('upload-pdf/', PDFUploadView.as_view(), name='upload-pdf'),
    path('generar-nota/', NotaGeneradaView.as_view(), name='generar-nota'),
 #   path('generar-nota-word/', NotaGeneradaViewEnWord.as_view(), name="generar-word") 
    path('formulario/', subir_archivo_view, name='subir_archivo'),
    path('procesar-excel/', ExcelUploadView.as_view(), name='procesar excel')
  
]