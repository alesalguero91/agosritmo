from .models import Cliente
from rest_framework import viewsets, permissions,status
from .serializers import ClienteSerializer
from rest_framework.response import Response
from rest_framework.decorators import action



class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    permission_classes=[permissions.AllowAny]
    serializer_class = ClienteSerializer
    lookup_field = 'nroCliente'

    def create(self, request, *args, **kwargs):
        nro_cliente = request.data.get('nroCliente')
        
        # Verificar si ya existe un cliente con ese número
        if Cliente.objects.filter(nroCliente=nro_cliente).exists():
            return Response(
                {"error": "Ya existe un cliente con este número."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si no existe, proceder con la creación normal
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
  