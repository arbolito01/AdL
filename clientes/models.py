from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20)
    onu_sn = models.CharField(max_length=50) # Número de serie de la ONU
    plan_servicio = models.CharField(max_length=50)
    fecha_alta = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    fecha_desactivacion = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.nombre