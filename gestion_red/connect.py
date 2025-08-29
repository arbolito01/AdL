# gestion_red/connect.py

from librouteros import connect
from django.conf import settings
import telnetlib
import time

def connect_mikrotik():
    """
    Establece y devuelve una conexión a la API de MikroTik.
    """
    api = connect(
        username=settings.MIKROTIK_USER,
        password=settings.MIKROTIK_PASSWORD,
        host=settings.MIKROTIK_IP
    )
    return api

def connect_olt():
    """
    Establece y devuelve una conexión Telnet a la OLT.
    """
    try:
        tn = telnetlib.Telnet(settings.OLT_IP)
        time.sleep(1)
        tn.read_until(b"Username:")
        tn.write(settings.OLT_USER.encode('ascii') + b"\n")
        tn.read_until(b"Password:")
        tn.write(settings.OLT_PASSWORD.encode('ascii') + b"\n")
        time.sleep(1)

        output = tn.read_until(b"#", timeout=5).decode('ascii')

        if "#" not in output:
            raise Exception("No se pudo conectar a la OLT. Verifique las credenciales.")
            
        return tn
    except Exception as e:
        raise Exception(f"Error al conectar con la OLT por Telnet: {e}")

def execute_olt_command(tn, command):
    """
    Ejecuta un comando en la OLT y devuelve la salida.
    """
    tn.write(command.encode('ascii') + b'\n')
    time.sleep(2)
    output = tn.read_until(b"#", timeout=5).decode('ascii')
    
    output_lines = output.split('\n')
    cleaned_output = [line for line in output_lines if command not in line and line.strip()]
    
    return "\n".join(cleaned_output)