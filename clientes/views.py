from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Cliente
from .forms import ClienteForm
from datetime import date
from django.conf import settings

# Importa las librerías de conexión
from routeros_api import RouterOsApiPool
import paramiko
import time

def lista_clientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})

def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()

            ssh_client = None
            api = None
            try:
                # 1. Configuración en la OLT (usando Paramiko para SSH)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=settings.OLT_IP, username=settings.OLT_USER, password=settings.OLT_PASSWORD)

                # Estos comandos son solo un ejemplo, adáptalos a tu OLT
                commands_olt = [
                    "configure terminal",
                    f"interface gpon 0/1", # Reemplaza con tu interfaz PON
                    f"onu add {cliente.onu_sn} serial-number {cliente.onu_sn}",
                    "exit"
                ]
                
                for command in commands_olt:
                    stdin, stdout, stderr = ssh_client.exec_command(command)
                    time.sleep(1)

                # 2. Configuración en el MikroTik (usando la API)
                api = RouterOsApiPool(settings.MIKROTIK_IP, username=settings.MIKROTIK_USER, password=settings.MIKROTIK_PASSWORD, plaintext_login=True)
                api_client = api.get_api()
                api_client.add_ppp_secret(
                    name=cliente.nombre, 
                    password='password_generada', 
                    service='pppoe', 
                    profile=cliente.plan_servicio
                )

            except Exception as e:
                # Si falla la configuración de los equipos, revertimos el cliente en la BD
                cliente.delete()
                return render(request, 'error.html', {'error_message': f'Error al configurar equipos: {e}'})

            finally:
                if ssh_client:
                    ssh_client.close()
                if api:
                    api.disconnect()

            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'clientes/crear_cliente.html', {'form': form})

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

@require_POST
def desactivar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if cliente.activo:
        ssh_client = None
        api = None
        try:
            # Desactivar en la OLT y MikroTik
            # Lógica API real (reemplazar con tus comandos)
            
            api = RouterOsApiPool(settings.MIKROTIK_IP, username=settings.MIKROTIK_USER, password=settings.MIKROTIK_PASSWORD, plaintext_login=True)
            api_client = api.get_api()
            
            # Buscar el usuario PPPoE por nombre para obtener su ID
            user = api_client.find_ppp_secret(name=cliente.nombre)
            if user:
                api_client.disable_ppp_secret(id=user['.id'])

            # Lógica para OLT (ejemplo)
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(hostname=settings.OLT_IP, username=settings.OLT_USER, password=settings.OLT_PASSWORD)
            stdin, stdout, stderr = ssh_client.exec_command(f'service remove {cliente.onu_sn}') # Comando ficticio
            
            cliente.activo = False
            cliente.fecha_desactivacion = date.today()
            cliente.save()

        except Exception as e:
            return render(request, 'error.html', {'error_message': f'Error al desactivar cliente: {e}'})
        
        finally:
            if ssh_client:
                ssh_client.close()
            if api:
                api.disconnect()
                
    return redirect('lista_clientes')

@require_POST
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    ssh_client = None
    api = None
    try:
        # Eliminar de la OLT y MikroTik
        # Lógica API real (reemplazar con tus comandos)
        
        api = RouterOsApiPool(settings.MIKROTIK_IP, username=settings.MIKROTIK_USER, password=settings.MIKROTIK_PASSWORD, plaintext_login=True)
        api_client = api.get_api()
        
        # Buscar el usuario PPPoE por nombre para obtener su ID
        user = api_client.find_ppp_secret(name=cliente.nombre)
        if user:
            api_client.remove_ppp_secret(id=user['.id'])

        # Lógica para OLT (ejemplo)
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=settings.OLT_IP, username=settings.OLT_USER, password=settings.OLT_PASSWORD)
        stdin, stdout, stderr = ssh_client.exec_command(f'no service {cliente.onu_sn}') # Comando ficticio
        
        cliente.delete()
        
    except Exception as e:
        return render(request, 'error.html', {'error_message': f'Error al eliminar cliente: {e}'})

    finally:
        if ssh_client:
            ssh_client.close()
        if api:
            api.disconnect()

    return redirect('lista_clientes')