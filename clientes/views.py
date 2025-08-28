# clientes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Cliente
from .forms import ClienteForm
from datetime import date
from django.db.models import Q
from django.contrib.auth.decorators import login_required

# Importa las librerías de conexión
from librouteros import connect
import paramiko
import time
from librouteros.query import Key


# --- Función de SIMULACIÓN de la OLT ---
def simular_olt_comando(comando):
    """
    Función que simula la ejecución de un comando en la OLT.
    Esto evita que el sistema falle si no hay una OLT real conectada.
    """
    print(f"SIMULACIÓN: Comando de OLT ejecutado: {comando}")
    # Aquí podrías añadir lógica para simular errores si fuera necesario.
    return True


# Conexión al MikroTik
def connect_mikrotik():
    api = connect(
        username=settings.MIKROTIK_USER,
        password=settings.MIKROTIK_PASSWORD,
        host=settings.MIKROTIK_IP
    )
    return api


@login_required
def dashboard(request):
    """
    Vista principal que muestra un resumen del estado de los equipos.
    """
    api = None
    context = {}

    try:
        api = connect_mikrotik()
        
        system_health = list(api.path('system', 'health'))
        if system_health:
            health_data = system_health[0]
            context['cpu_load'] = health_data.get('cpu-load', 'N/A')
            context['free_memory'] = health_data.get('free-memory', 'N/A')
            context['voltage'] = health_data.get('voltage', 'N/A')
            context['temperature'] = health_data.get('temperature', 'N/A')
            
        ppp_active = list(api.path('ppp', 'active'))
        context['active_users_count'] = len(ppp_active)
        
        ppp_secrets = list(api.path('ppp', 'secret'))
        context['total_users_count'] = len(ppp_secrets)

        system_resource = list(api.path('system', 'resource'))
        if system_resource:
            context['uptime'] = system_resource[0].get('uptime', 'N/A')

    except Exception as e:
        context['error_message'] = f'Error al conectar con MikroTik: {e}'

    finally:
        if api:
            api.close()
    
    return render(request, 'clientes/dashboard.html', context)


@login_required
def lista_clientes(request):
    query = request.GET.get('q')
    if query:
        clientes = Cliente.objects.filter(
            Q(nombre__icontains=query) |
            Q(telefono__icontains=query) |
            Q(onu_sn__icontains=query)
        )
    else:
        clientes = Cliente.objects.all()
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})


@login_required
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()

            api = None
            try:
                # 1. --- LÓGICA de SIMULACIÓN de la OLT ---
                print("Iniciando simulación de configuración de OLT...")
                simular_olt_comando("configure terminal")
                simular_olt_comando(f"interface gpon 0/1")
                simular_olt_comando(f"onu add {cliente.onu_sn} serial-number {cliente.onu_sn}")
                simular_olt_comando("exit")
                
                # 2. Configuración en el MikroTik
                api = connect_mikrotik()
                secrets = api.path('ppp', 'secret')
                secrets.add(
                    name=cliente.nombre, 
                    password='password_generada', 
                    service='pppoe', 
                    profile=cliente.plan_servicio
                )

            except Exception as e:
                cliente.delete()
                return render(request, 'error.html', {'error_message': f'Error al configurar equipos: {e}'})

            finally:
                if api:
                    api.close()

            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'clientes/crear_cliente.html', {'form': form})


@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/editar_cliente.html', {'form': form})


@login_required
def detalle_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    
    api = None
    mikrotik_status = None
    try:
        api = connect_mikrotik()
        active_users = api.path('ppp', 'active')
        active_client = list(active_users.get(query={Key('name'): cliente.nombre}))
        
        if active_client:
            mikrotik_status = "Conectado"
        else:
            mikrotik_status = "Desconectado"
            
    except Exception as e:
        mikrotik_status = f"Error al conectar con MikroTik: {e}"

    finally:
        if api:
            api.close()
            
    return render(request, 'clientes/detalle_cliente.html', {
        'cliente': cliente, 
        'mikrotik_status': mikrotik_status
    })


@login_required
@require_POST
def desactivar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if cliente.activo:
        api = None
        try:
            # 1. Desactivar en MikroTik
            api = connect_mikrotik()
            secrets = api.path('ppp', 'secret')
            
            user = secrets.get(query={Key('name'): cliente.nombre})
            if user:
                secrets.disable(user[0]['.id'])

            # 2. --- LÓGICA de SIMULACIÓN de la OLT ---
            print("Iniciando simulación de desactivación de OLT...")
            simular_olt_comando(f'service remove {cliente.onu_sn}')
            
            cliente.activo = False
            cliente.fecha_desactivacion = date.today()
            cliente.save()

        except Exception as e:
            return render(request, 'error.html', {'error_message': f'Error al desactivar cliente: {e}'})
        
        finally:
            if api:
                api.close()
                
    return redirect('lista_clientes')


@login_required
@require_POST
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    api = None
    try:
        # 1. Eliminar de MikroTik
        api = connect_mikrotik()
        secrets = api.path('ppp', 'secret')
        
        user = secrets.get(query={Key('name'): cliente.nombre})
        if user:
            secrets.remove(user[0]['.id'])

        # 2. --- LÓGICA de SIMULACIÓN de la OLT ---
        print("Iniciando simulación de eliminación de OLT...")
        simular_olt_comando(f'no service {cliente.onu_sn}')
        
        cliente.delete()
        
    except Exception as e:
        return render(request, 'error.html', {'error_message': f'Error al eliminar cliente: {e}'})

    finally:
        if api:
            api.close()

    return redirect('lista_clientes')