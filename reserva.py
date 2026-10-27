import requests
import time
import re
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==========================
# CONFIGURACIÓN
# ==========================

EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["PASSWORD"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["CHAT_ID"]

ACTIVIDAD = os.environ["ACTIVIDAD"]
HORA = os.environ["HORA"]
ZONA_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

def ahora_arg():
    return datetime.now(ZONA_ARG)


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
# ESPERA PREVIA
# ==========================
#
# El modo agresivo comienza
# aproximadamente 5 minutos
# antes de que se habilite.
# ==========================

mensaje = objetivo["reservableData"]["message"]

if objetivo["reservableData"]["reservable"] == 0:

    segundos_espera = None

    # Caso 1:
    # "Reservable a partir de 14:45"

    hora_match = re.search(
        r"Reservable a partir de\s+(\d{1,2}):(\d{2})",
        mensaje,
        re.IGNORECASE
    )

    if hora_match:

        hora_apertura = int(hora_match.group(1))
        minuto_apertura = int(hora_match.group(2))

        ahora = ahora_arg()

        apertura = ahora.replace(
            hour=hora_apertura,
            minute=minuto_apertura,
            second=0,
            microsecond=0
        )

        # Si la hora indicada ya pasó hoy,
        # interpretamos que corresponde al día siguiente.
        if apertura <= ahora:
            apertura += timedelta(days=1)

        inicio_agresivo = apertura - timedelta(minutes=5)

        segundos_espera = (
            inicio_agresivo - ahora
        ).total_seconds()

        print(
            f"\n🕐 Hora actual ARG: "
            f"{ahora.strftime('%H:%M:%S')}"
        )

        print(
            f"🎯 Apertura informada: "
            f"{apertura.strftime('%H:%M:%S')}"
        )

        print(
            f"🚀 Modo agresivo programado para: "
            f"{inicio_agresivo.strftime('%H:%M:%S')}"
        )

    # Caso 2:
    # "Faltan 20 minutos"

    else:

        minutos_match = re.search(
            r"(\d+)\s+minutos?",
            mensaje
        )

        if minutos_match:

            minutos = int(
                minutos_match.group(1)
            )

            if minutos > 5:
                segundos_espera = (
                    minutos - 5
                ) * 60

    # Esperar solamente si corresponde

    if (
        segundos_espera is not None
        and segundos_espera > 0
    ):

        print(
            f"😴 Esperando aproximadamente "
            f"{round(segundos_espera)} segundos..."
        )

        time.sleep(segundos_espera)

# ==========================
# MODO AGRESIVO
# ==========================

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
        ahora_arg().strftime("%H:%M:%S.%f")[:-3],
        "|",
        mensaje
    )

    if reservable == 1:

        print("\n🔥 ¡SE HABILITÓ!")

        fecha_url = ahora_arg().strftime(
            "%a %b %d %Y %H:%M:%S GMT-0300"
        )

        url = (
            f"https://interactivo.unobahiaclub.com"
            f"/api/reservas/{horario_id}/{fecha_url}"
        )

        payload = {
            "horario_id": horario_id,
            "fecha": ahora_arg().isoformat()
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
