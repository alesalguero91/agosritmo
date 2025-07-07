from django.db import models


class Cliente(models.Model):
    nroCliente = models.CharField(max_length=10)
    dni= models.CharField(max_length=10)
    Nombre = models.CharField(max_length=30)

