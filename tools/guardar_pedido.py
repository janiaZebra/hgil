import json
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_core.tools import Tool
from sqlalchemy.dialects import mysql

REMITENTE_EMAIL = os.getenv("REMITENTE_EMAIL")
REMITENTE_PASS = os.getenv("REMITENTE_PASS")
DESTINATARIO_EMAIL = os.getenv("DESTINATARIO_EMAIL")
ASUNTO_EMAIL = os.getenv("ASUNTO_EMAIL", "Nuevo pedido")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

BD_TABLA_PEDIDOS = os.getenv("BD_TABLA_PEDIDOS", "PEDIDOS")

SHEET_ID = "1qty3AW_7mcAppm5O--dB_9W_mAY5V2dFIvux2OBcHM4"
SHEET_PAGE = "Hoja 2"

pedido_id = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
JSON_TRANS_MODEL = os.getenv("JSON_TRANS_MODEL", "gpt-4.1-nano-2025-04-14")


def guardar_pedido(pedido: str, session_id: str) -> str:

    pedido_id = f"{datetime.now():%Y%m%d}-{session_id[:6]}-{random.randint(100, 999)}"

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = ("Texto del pedido: \n"
              f"{pedido}\n\n"
              "Devuélveme SOLO el JSON estructurado como debe estar")

    system_prompt = ('''Eres un asistente que transforma texto libre de pedidos en un JSON ESTRICTO con esta estructura:

{
  "articulos": [
    {
      "nombre": "string",
      "cantidad": int,
      "identificador": "string",
      "tipo_unidad": "UD|KG|ML|M2",  // UD para unidades, KG para kilogramos, ML para metros lineales, M2 para metros cuadrados
      "observacion": "string"  // Si no hay observación, dejar como "" (vacío)
    },
    // ...más artículos
  ]
}

Reglas:
- "articulos" es siempre una lista (puede estar vacía).
- Si algún campo falta en el texto, ponlo vacío ("")
- Siempre devuelve exactamente ese JSON (sin comentarios, sin texto adicional antes o después).
- Indicar el tipo de unidad en la cantidad.

Ejemplo de entrada:
11 unidades de chapa galvanizada 2000*1000*1 [CG20101]  BOQUILLA TUBERIAS 5.763-016.0 [08490] 4 unidades   TUBO NEGRO LISO DIN 5 [2440] 30KG 20 metros lineales de IPN 100 NV [11201]`

Ejemplo de salida:
{
  "articulos": [
    {
      "nombre": "CHAPA GALVANIZADA 2000*1000*1",
      "cantidad": 11,
      "identificador": "CG20101",
      "tipo_unidad": "UD",
      "observacion": ""
    },
    {
      "nombre": "BOQUILLA TUBERIAS 5.763-016.0",
      "cantidad": 4,
      "identificador": "08490",
      "tipo_unidad": "UD",
      "observacion": ""
    },
    {
      "nombre": "TUBO NEGRO LISO DIN 5",
      "cantidad": 30,
      "identificador": "2440",
      "tipo_unidad": "KG",
      "observacion": ""
    },
    {
      "nombre": "IPN 100 NV",
      "cantidad": 20,
      "identificador": "11201",
      "tipo_unidad": "ML",
      "observacion": ""
    }
  ]
}
''')

    response = client.chat.completions.create(
        model= JSON_TRANS_MODEL or "gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000
    )

    pedido_json = response.choices[0].message.content

    enviar_correo(pedido_id, pedido, session_id )
    insertar_google_sheets(pedido_id, pedido_json, session_id)
    # insertar_bbdd(pedido_id, pedido_json, session_id)

def enviar_correo(pedido_id: str, pedido: str, session_id: str) -> str:
    mensaje = MIMEMultipart()
    mensaje['From'] = REMITENTE_EMAIL
    mensaje['To'] = DESTINATARIO_EMAIL
    mensaje['Subject'] = ASUNTO_EMAIL

    inicio_correo = f"""Se ha recibido un nuevo pedido del cliente: <b>{session_id}</b> <br/>Pedido: {pedido_id}<br/>"""
    final_correo = f"""<br><br><b>Enviado desde Agente-HIERROS GIL <br><br>"""

    mensaje.attach(MIMEText(inicio_correo + "<br>" + pedido + "<br />" + final_correo, 'html'))

    try:
        servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
        servidor.ehlo()
        servidor.starttls()
        servidor.ehlo()
        servidor.login(REMITENTE_EMAIL, REMITENTE_PASS)
        servidor.send_message(mensaje)
        servidor.quit()
        print("Correo enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

    return "Pedido guardado correctamente."

def insertar_google_sheets(pedido_id, pedido_json, session_id):
    import json
    from googleapiclient.discovery import build
    from datetime import datetime

    creds = get_google_creds()
    service = build('sheets', 'v4', credentials=creds)
    time_now = datetime.now().isoformat(sep=' ', timespec='seconds')

    try:
        pedido_data = json.loads(pedido_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return "Error al procesar el pedido."

    if isinstance(pedido_data, dict):
        articulos = pedido_data.get("articulos", [])
    elif isinstance(pedido_data, list):
        articulos = pedido_data
    else:
        print("Formato inesperado de pedido_json:", type(pedido_data))
        return "Formato inesperado de pedido_json."


    pedido_raw = pedido_json
    articulos = pedido_data.get("articulos", [])

    values = []
    for articulo in articulos:
        nombre = articulo.get("nombre", "")
        cantidad = articulo.get("cantidad", "")
        identificador = articulo.get("identificador", "")
        tipo_unidad = articulo.get("tipo_unidad", "")
        observacion = articulo.get("observacion", " ")
        fila = [time_now, session_id, pedido_id, identificador, nombre, cantidad, tipo_unidad, observacion, " " , pedido_raw.replace('\n', '').replace('\r', '')]
        values.append(fila)

    if not values:
        print("No hay artículos para insertar.")
        return "No hay artículos en el pedido."

    body = {'values': values}

    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_PAGE}!A:A",
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()

    return "Pedido insertado correctamente."


def insertar_bbdd(pedido, session_id):
    con = mysql.connector.connect(
        host="localhost",
        user="root",
        password="zebra_admin_2025",
        database="STOCK"
    )
    cur = con.cursor()
    cur.execute("INSERT INTO PEDIDOS (time_now, cliente, pedido_id, pedido, ) VALUES (%s, %s, %s, %s)", (time_now, session_id, pedido_id, pedido))
    con.commit()
    con.close()


def get_google_creds():
    token_str = os.getenv("GOOGLE_TOKEN_JSON")
    if not token_str:
        raise Exception("No se encontró GOOGLE_TOKEN_JSON en variables de entorno")
    token_data = json.loads(token_str)
    creds = Credentials.from_authorized_user_info(token_data)
    return creds

def guardar_pedido_wrapper(pedido: str, **kwargs):
    session_id = kwargs.get("session_id", "desconocido")  # o lanzar error si no está
    return guardar_pedido(pedido, session_id)

def get_tools():
    return [
        Tool(
            name="guardar_pedido",
            func=guardar_pedido_wrapper,
            description=(
                "Guarda un pedido confirmado por el cliente"
                "Importante insertar toda la información del pedido. Nombre y medidas del producto, cantidad, identificador y observaciones si las hay. "
                "EJEMPLO ENTRADA: 11 unidades de chapa galvanizada 2000*1000*1 [CG20101]  BOQUILLA TUBERIAS 5.763-016.0 [08490] 4 unidades   TUBO NEGRO LISO DIN 5 [2440] 30KG "
            )
        )
    ]