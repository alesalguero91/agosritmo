from django.urls import path
from .views import  subir_archivo_view, ProcesarNotaView




urlpatterns = [
    path('', subir_archivo_view, name='subir_archivo'),
    path('procesar-nota/', ProcesarNotaView.as_view(), name='procesar_nota'),
]