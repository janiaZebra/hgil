import smtplib
from email.mime.text import MIMEText

REMITENTE_EMAIL = "jzebra0001@gmail.com"
REMITENTE_PASS = "dnwvoeqmkycdrbdj"
DESTINATARIO_EMAIL = "janiaserrano@hotmail.com,daniel.perez@zebraventures.eu"
ASUNTO_EMAIL = "Pedido de prueba"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Cuerpo del email
mensaje = MIMEText("Este es un correo de prueba enviado por script SMTP.")
mensaje["Subject"] = ASUNTO_EMAIL
mensaje["From"] = REMITENTE_EMAIL
mensaje["To"] = DESTINATARIO_EMAIL

try:
    # Conexión y login SMTP
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(REMITENTE_EMAIL, REMITENTE_PASS)
    # Envío
    server.sendmail(REMITENTE_EMAIL, DESTINATARIO_EMAIL.split(','), mensaje.as_string())
    server.quit()
    print("Correo enviado correctamente.")
except Exception as e:
    print("Error al enviar el correo:")
    print(e)
