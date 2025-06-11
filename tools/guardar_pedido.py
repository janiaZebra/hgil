import json
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
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


def guardar_pedido(pedido: str, session_id: str) -> str:
    enviar_correo(pedido, session_id)
    insertar_google_sheets(pedido, session_id)
    # insertar_bbdd(pedido, session_id)

def enviar_correo(pedido: str, session_id: str) -> str:
    mensaje = MIMEMultipart()
    mensaje['From'] = REMITENTE_EMAIL
    mensaje['To'] = DESTINATARIO_EMAIL
    mensaje['Subject'] = ASUNTO_EMAIL

    inicio_correo = f"""Se ha recibido un nuevo pedido del cliente: <b>{session_id}</b> <br/>Pedido: {pedido_id}<br/>"""
    final_correo = f"""<br><br><b>Enviado desde Agente-HIERROS GIL <br><br>"""

    mensaje.attach(MIMEText(inicio_correo + "<br>" + pedido + "<br />" + final_correo, 'html'))

    try:
        servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        servidor.starttls()
        servidor.login(REMITENTE_EMAIL, REMITENTE_PASS)
        servidor.send_message(mensaje)
        servidor.quit()
        print("Correo enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

    return "Pedido guardado correctamente."

def insertar_google_sheets(pedido, session_id):
    creds = get_google_creds()
    service = build('sheets', 'v4', credentials=creds)

    values = [[time_now, session_id, pedido_id, pedido]]
    body = {'values': values}

    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_PAGE}!A:A",
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()

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
            )
        )
    ]