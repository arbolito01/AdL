# api/views.py

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from gestion_red.connect import connect_mikrotik, connect_olt, execute_olt_command
from librouteros.query import Key

from django.conf import settings 
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@csrf_exempt
@require_POST
def crear_cliente_api(request):
    """
    Endpoint para crear un cliente en MikroTik y OLT a través de la API.
    Recibe datos en formato JSON.
    """
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre')
        onu_sn = data.get('onu_sn')
        plan_servicio = data.get('plan_servicio')
        pppoe_password = data.get('pppoe_password', 'password_generada')

        if not all([nombre, onu_sn, plan_servicio]):
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos.'}, status=400)

        api = None
        tn = None
        try:
            # Configuración en la OLT (REAL)
            logging.info("Iniciando aprovisionamiento en OLT...")
            tn = connect_olt()
            
            # Comandos de ejemplo para la OLT ZTE
            execute_olt_command(tn, "configure terminal")
            execute_olt_command(tn, "interface gpon_olt-1/1/1")
            execute_olt_command(tn, f"onu pre-config-mode serial-number {onu_sn}")
            execute_olt_command(tn, "exit")
            
            logging.info(f"ONU {onu_sn} pre-configurada en OLT.")

            # Configuración en el MikroTik
            api = connect_mikrotik()
            secrets = api.path('ppp', 'secret')
            secrets.add(
                name=nombre, 
                password=pppoe_password, 
                service='pppoe', 
                profile=plan_servicio
            )
            logging.info(f"Cliente {nombre} creado en MikroTik a través de la API.")

        except Exception as e:
            logging.error(f'Error al configurar equipos para {nombre}: {e}')
            return JsonResponse({'success': False, 'message': f'Error al configurar equipos: {e}'}, status=500)

        finally:
            if api:
                api.close()
            if tn:
                tn.close()

        return JsonResponse({'success': True, 'message': 'Cliente creado y aprovisionado con éxito.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {e}'}, status=500)

@csrf_exempt
@require_POST
def desactivar_cliente_api(request):
    """
    Endpoint para desactivar un cliente en MikroTik y OLT a través de la API.
    """
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre')
        onu_sn = data.get('onu_sn')

        if not all([nombre, onu_sn]):
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos.'}, status=400)

        api = None
        tn = None
        try:
            # Desactivar en MikroTik
            api = connect_mikrotik()
            secrets = api.path('ppp', 'secret')
            user = secrets.get(query={Key('name'): nombre})
            if user:
                secrets.disable(user[0]['.id'])
            logging.info(f"Cliente {nombre} desactivado en MikroTik a través de la API.")

            # Desactivar en la OLT
            logging.info(f"Iniciando desactivación en OLT para cliente {nombre}...")
            tn = connect_olt()
            execute_olt_command(tn, "configure terminal")
            execute_olt_command(tn, f"no onu service {onu_sn}")
            execute_olt_command(tn, "exit")
            logging.info(f"Servicio de ONU {onu_sn} desactivado en OLT.")

        except Exception as e:
            logging.error(f'Error al desactivar cliente {nombre}: {e}')
            return JsonResponse({'success': False, 'message': f'Error al desactivar cliente: {e}'}, status=500)
        
        finally:
            if api:
                api.close()
            if tn:
                tn.close()

        return JsonResponse({'success': True, 'message': 'Cliente desactivado con éxito.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {e}'}, status=500)

@csrf_exempt
@require_POST
def reconectar_cliente_api(request):
    """
    Endpoint para reconectar un cliente en MikroTik y OLT a través de la API.
    """
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre')
        onu_sn = data.get('onu_sn')

        if not all([nombre, onu_sn]):
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos.'}, status=400)

        api = None
        tn = None
        try:
            # Reconectar en MikroTik
            api = connect_mikrotik()
            secrets = api.path('ppp', 'secret')
            user = secrets.get(query={Key('name'): nombre})
            if user:
                secrets.enable(user[0]['.id'])
            logging.info(f"Cliente {nombre} reconectado en MikroTik a través de la API.")

            # Reconectar en la OLT
            logging.info(f"Iniciando reconexión en OLT para cliente {nombre}...")
            tn = connect_olt()
            execute_olt_command(tn, "configure terminal")
            execute_olt_command(tn, f"onu service {onu_sn}")
            execute_olt_command(tn, "exit")
            logging.info(f"Servicio de ONU {onu_sn} reconectado en OLT.")

        except Exception as e:
            logging.error(f'Error al reconectar cliente {nombre}: {e}')
            return JsonResponse({'success': False, 'message': f'Error al reconectar cliente: {e}'}, status=500)
        
        finally:
            if api:
                api.close()
            if tn:
                tn.close()

        return JsonResponse({'success': True, 'message': 'Cliente reconectado con éxito.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {e}'}, status=500)


@csrf_exempt
@require_POST
def cambiar_puerto_olt_api(request):
    """
    Endpoint para cambiar un cliente de puerto PON en la OLT.
    """
    try:
        data = json.loads(request.body)
        onu_sn = data.get('onu_sn')
        nuevo_puerto = data.get('nuevo_puerto')
        
        if not all([onu_sn, nuevo_puerto]):
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos.'}, status=400)
            
        tn = None
        try:
            logging.info(f"Iniciando cambio de puerto para la ONU {onu_sn} al puerto {nuevo_puerto} a través de la API.")
            tn = connect_olt()
            # Comando de ejemplo para cambiar de puerto. Debe adaptarse al modelo de tu OLT.
            comando = f'pon port change onu {onu_sn} to {nuevo_puerto}'
            execute_olt_command(tn, "configure terminal")
            execute_olt_command(tn, comando)
            execute_olt_command(tn, "exit")
            
            logging.info(f"ONU {onu_sn} migrada al puerto {nuevo_puerto} con éxito.")
        except Exception as e:
            logging.error(f'Error al cambiar de puerto en la OLT para {onu_sn}: {e}')
            return JsonResponse({'success': False, 'message': f'Error en la OLT: {e}'}, status=500)
        finally:
            if tn:
                tn.close()
                
        return JsonResponse({'success': True, 'message': f'ONU {onu_sn} cambiada al puerto {nuevo_puerto} con éxito.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {e}'}, status=500)

@csrf_exempt
@require_POST
def migrar_cliente_olt_api(request):
    """
    Endpoint para migrar un cliente entre diferentes OLTs.
    """
    try:
        data = json.loads(request.body)
        onu_sn = data.get('onu_sn')
        nueva_olt_ip = data.get('nueva_olt_ip')

        if not all([onu_sn, nueva_olt_ip]):
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos.'}, status=400)
            
        logging.info(f"Iniciando migración de la ONU {onu_sn} a la nueva OLT en {nueva_olt_ip}.")
        
        # Este es un punto de inicio. La lógica para conectarse a una OLT diferente
        # requiere que las credenciales para la nueva OLT estén disponibles.
        # Por ahora, se simula el proceso.
        
        # Si la lógica fuera exitosa:
        # return JsonResponse({'success': True, 'message': f'ONU {onu_sn} migrada con éxito a la OLT en {nueva_olt_ip}.'})

        return JsonResponse({'success': False, 'message': 'Funcionalidad de migración de OLT no implementada completamente en el back-end de AdL.'}, status=501)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {e}'}, status=500)