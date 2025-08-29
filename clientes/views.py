# clientes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Cliente
from .forms import ClienteForm
from datetime import date
from django.db.models import Q
from django.contrib.auth.decorators import login_required
import logging
from librouteros import connect
from librouteros.query import Key
from gestion_red.connect import connect_mikrotik, connect_olt, execute_olt_command

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            tn = None
            try:
                # 1. Configuración en la OLT (REAL)
                logging.info("Iniciando aprovisionamiento en OLT...")
                tn = connect_olt()
                
                # Comandos de ejemplo para la OLT ZTE
                execute_olt_command(tn, "configure terminal")
                execute_olt_command(tn, "interface gpon_olt-1/1/1")
                execute_olt_command(tn, f"onu pre-config-mode serial-number {cliente.onu_sn}")
                execute_olt_command(tn, "exit")
                
                logging.info(f"ONU {cliente.onu_sn} pre-configurada en OLT.")

                # 2. Configuración en el MikroTik
                api = connect_mikrotik()
                secrets = api.path('ppp', 'secret')
                secrets.add(
                    name=cliente.nombre, 
                    password='password_generada', 
                    service='pppoe', 
                    profile=cliente.plan_servicio
                )
                logging.info(f"Cliente {cliente.nombre} creado en MikroTik.")

            except Exception as e:
                if cliente:
                    cliente.delete()
                logging.error(f'Error al configurar equipos para {cliente.nombre}: {e}')
                return render(request, 'error.html', {'error_message': f'Error al configurar equipos: {e}'})

            finally:
                if api:
                    api.close()
                if tn:
                    tn.close()

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
        tn = None
        try:
            # 1. Desactivar en MikroTik
            api = connect_mikrotik()
            secrets = api.path('ppp', 'secret')
            
            user = secrets.get(query={Key('name'): cliente.nombre})
            if user:
                secrets.disable(user[0]['.id'])
            logging.info(f"Cliente {cliente.nombre} desactivado en MikroTik.")

            # 2. Desactivar en la OLT
            logging.info(f"Iniciando desactivación en OLT para cliente {cliente.nombre}...")
            tn = connect_olt()
            execute_olt_command(tn, "configure terminal")
            execute_olt_command(tn, f"no onu service {cliente.onu_sn}")
            execute_olt_command(tn, "exit")
            logging.info(f"Servicio de ONU {cliente.onu_sn} desactivado en OLT.")
            
            # 3. Actualizar la base de datos local
            cliente.activo = False
            cliente.fecha_desactivacion = date.today()
            cliente.save()

        except Exception as e:
            logging.error(f'Error al desactivar cliente {cliente.nombre}: {e}')
            return render(request, 'error.html', {'error_message': f'Error al desactivar cliente: {e}'})
        
        finally:
            if api:
                api.close()
            if tn:
                tn.close()
                
    return redirect('lista_clientes')


@login_required
@require_POST
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    api = None
    tn = None
    try:
        # 1. Eliminar de MikroTik
        api = connect_mikrotik()
        secrets = api.path('ppp', 'secret')
        
        user = secrets.get(query={Key('name'): cliente.nombre})
        if user:
            secrets.remove(user[0]['.id'])
        logging.info(f"Cliente {cliente.nombre} eliminado de MikroTik.")

        # 2. Eliminar de la OLT
        logging.info(f"Iniciando eliminación en OLT para cliente {cliente.nombre}...")
        tn = connect_olt()
        execute_olt_command(tn, "configure terminal")
        execute_olt_command(tn, f"no onu {cliente.onu_sn}")
        execute_olt_command(tn, "exit")
        logging.info(f"ONU {cliente.onu_sn} eliminada de OLT.")
        
        # 3. Eliminar de la base de datos local
        cliente.delete()
        
    except Exception as e:
        logging.error(f'Error al eliminar cliente {cliente.nombre}: {e}')
        return render(request, 'error.html', {'error_message': f'Error al eliminar cliente: {e}'})

    finally:
        if api:
            api.close()
        if tn:
            tn.close()

    return redirect('lista_clientes')