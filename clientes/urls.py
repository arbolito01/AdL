# clientes/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clientes, name='lista_clientes'),
    path('crear/', views.crear_cliente, name='crear_cliente'),
    path('editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('desactivar/<int:pk>/', views.desactivar_cliente, name='desactivar_cliente'),
    path('eliminar/<int:pk>/', views.eliminar_cliente, name='eliminar_cliente'),
]