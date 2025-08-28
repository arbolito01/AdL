import os
import django
from django.conf import settings
from routeros_api import RouterOsApiPool

# Carga la configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_red.settings')
django.setup()

api = None
try:
    # 1. Creamos el objeto de conexión
    api = RouterOsApiPool(settings.MIKROTIK_IP, username=settings.MIKROTIK_USER, password=settings.MIKROTIK_PASSWORD, plaintext_login=True)

    # 2. Obtenemos el objeto de la API a partir de la conexión
    api_client = api.get_api()

    print("Conexión a MikroTik exitosa. Probando la API...")

    # 3. Usamos el objeto 'api_client' para ejecutar comandos
    secrets = api_client.call("/ppp/secret/print")
    print("\nUsuarios PPPoE:")
    for secret in secrets:
        print(f"- {secret['name']}")

except Exception as e:
    print(f"Error al conectar con MikroTik: {e}")

finally:
    # 4. Cerramos la conexión para liberar recursos
    if api:
        api.disconnect()
    print("Conexión cerrada.")