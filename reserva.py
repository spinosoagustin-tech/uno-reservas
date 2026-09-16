import requests
import time
import re
import os
from datetime import datetime

# ==========================
# CONFIGURACIÓN
# ==========================

EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["PASSWORD"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ACTIVIDAD = "GAP"
HORA = "14:40"

def enviar_telegram(mensaje):

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje
        }
    )

# ==========================
# LOGIN AUTOMÁTICO
# ==========================

print("🔐 Iniciando sesión...")

s = requests.Session()

login_payload = {
    "email": EMAIL,
    "password": PASSWORD
}

r = s.post(
    "https://interactivo.unobahiaclub.com/api/auth/signin",
    json=login_payload
)

print("Login status:", r.status_code)

if "IsessionId" not in s.cookies.get_dict():
    raise Exception("❌ No se obtuvo IsessionId")

print("✅ Login exitoso")

enviar_telegram(
    f"🔐 Login exitoso\n"
    f"Actividad: {ACTIVIDAD}\n"
    f"Hora: {HORA}"
)

# ==========================
# BUSCAR CLASE
# ==========================

print("\n🔎 Buscando clase...")

horarios = s.get(
    "https://interactivo.unobahiaclub.com/api/horarios/hoy?ouId=1"
).json()

objetivo = None

for clase in horarios:

    nombre = clase["actividades"]["nombre"]

    if (
        ACTIVIDAD.upper() in nombre.upper()
        and clase["desde"] == HORA
    ):
        objetivo = clase
        break

if objetivo is None:
    raise Exception("❌ No encontré la clase")

horario_id = objetivo["id"]

print("\n✅ Clase encontrada")
print("ID:", horario_id)
print("Actividad:", objetivo["actividades"]["nombre"])
print("Hora:", objetivo["desde"])
print("Estado:", objetivo["reservableData"]["message"])

# ==========================
# SI FALTAN MUCHOS MINUTOS,
# DORMIR HASTA 10 SEGUNDOS
# ANTES DE LA APERTURA
# ==========================

mensaje = objetivo["reservableData"]["message"]

if objetivo["reservableData"]["reservable"] == 0:

    minutos_match = re.search(
        r"(\d+)\s+minutos?",
        mensaje
    )

    if minutos_match:

        minutos = int(
            minutos_match.group(1)
        )

        if minutos > 1:

            segundos = minutos * 60 - 10

            print(
                f"\n😴 Faltan aproximadamente {minutos} minutos."
            )

            print(
                f"Esperando {segundos} segundos antes de entrar en modo agresivo..."
            )

            time.sleep(segundos)

print("\n🚀 Modo agresivo activado")

# ==========================
# ESPERA ACTIVA
# ==========================

while True:

    detalle = s.get(
        f"https://interactivo.unobahiaclub.com/api/horarios/{horario_id}/reservable-data"
    ).json()

    reservable = detalle["reservableData"]["reservable"]
    mensaje = detalle["reservableData"]["message"]

    print(
        datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "|",
        mensaje
    )

    if reservable == 1:

        print("\n🔥 ¡SE HABILITÓ!")

        fecha_url = datetime.now().strftime(
            "%a %b %d %Y %H:%M:%S GMT-0300"
        )

        url = (
            f"https://interactivo.unobahiaclub.com"
            f"/api/reservas/{horario_id}/{fecha_url}"
        )

        payload = {
            "horario_id": horario_id,
            "fecha": datetime.now().isoformat()
        }

        inicio = time.time()

        r = s.post(
            url,
            json=payload
        )

        latencia = round(
            (time.time() - inicio) * 1000
        )

        print("\n====================")
        print("RESULTADO RESERVA")
        print("====================")

        print("Status:", r.status_code)
        print(f"Latencia POST: {latencia} ms")

        try:
            print(r.json())
        except:
            print(r.text)

if r.status_code == 200:

    print("\n✅ RESERVA EXITOSA")

    enviar_telegram(
        f"✅ RESERVA EXITOSA\n\n"
        f"Actividad: {ACTIVIDAD}\n"
        f"Hora: {HORA}\n"
        f"Latencia: {latencia} ms"
    )

elif r.status_code == 409:

    print(
        "\n⚠️ Ya tenías la reserva o la clase se completó"
    )

    enviar_telegram(
        f"❌ No se pudo reservar\n\n"
        f"Actividad: {ACTIVIDAD}\n"
        f"Hora: {HORA}"
    )

else:

    print("\n❌ Error inesperado")

    enviar_telegram(
        f"❌ Error inesperado\n\n"
        f"Actividad: {ACTIVIDAD}\n"
        f"Hora: {HORA}\n"
        f"Status: {r.status_code}"
    )

break

time.sleep(0.2)
