# api/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('crear/', views.crear_cliente_api, name='crear_cliente_api'),
    path('desactivar/', views.desactivar_cliente_api, name='desactivar_cliente_api'),
    path('reconectar/', views.reconectar_cliente_api, name='reconectar_cliente_api'),
    path('cambiar_puerto/', views.cambiar_puerto_olt_api, name='cambiar_puerto_olt_api'),
    path('migrar_olt/', views.migrar_cliente_olt_api, name='migrar_cliente_olt_api'),
]