from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'direccion', 'telefono', 'onu_sn', 'plan_servicio', 'activo']
        labels = {
            'nombre': 'Nombre completo',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'onu_sn': 'Número de Serie (ONU)',
            'plan_servicio': 'Plan de Servicio',
            'activo': 'Estado (Activo)'
        }