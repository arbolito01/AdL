import os
import sys
import django
from django.conf import settings
from librouteros import connect
from librouteros.query import Key

# Carga la configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_red.settings')
django.setup()

api = None
try:
    # 1. Creamos el objeto de conexión
    api = connect(
        username=settings.MIKROTIK_USER,
        password=settings.MIKROTIK_PASSWORD,
        host=settings.MIKROTIK_IP
    )

    print("Conexión a MikroTik exitosa. Probando la API...")

    # 2. Usamos la API para ejecutar comandos
    secrets = api.path('ppp', 'secret')
    # La corrección está en esta línea:
    users = list(secrets)

    print("\nUsuarios PPPoE:")
    for user in users:
        print(f"- {user[Key('name')]}")

except Exception as e:
    print(f"Error al conectar con MikroTik: {e}")

finally:
    # 3. Cerramos la conexión para liberar recursos
    if api:
        api.close()
    print("Conexión cerrada.")