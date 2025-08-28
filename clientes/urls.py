# clientes/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'), # <-- Esta es la nueva ruta principal
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/crear/', views.crear_cliente, name='crear_cliente'),
    path('clientes/editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/detalle/<int:pk>/', views.detalle_cliente, name='detalle_cliente'),
    path('clientes/desactivar/<int:pk>/', views.desactivar_cliente, name='desactivar_cliente'),
    path('clientes/eliminar/<int:pk>/', views.eliminar_cliente, name='eliminar_cliente'),
]