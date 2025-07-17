import os
import traceback
import uuid

import requests
import pandas as pd
import tempfile

from fastapi import FastAPI, Request, UploadFile, File, Query, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles

from agente import chat
from jania import env
from excel_to_bd import excel_a_sqlite, poblar_embeddings

WHATSAPP_TOKEN = env("WHATSAPP_TOKEN")
VERIFY_TOKEN = env("VERIFY_TOKEN")
OPENAI_API_KEY = env("OPENAI_API_KEY")

ENDPOINT_OUT_MSG = env("ENDPOINT_OUT_MSG")
ENDPOINT_RETREIVE_MEDIA = env("ENDPOINT_RETREIVE_MEDIA")
ENDPOINT_TRANSCRIPTIONS_AUDIO = env("ENDPOINT_TRANSCRIPTIONS_AUDIO")
AUDIO_TRANSCRIPTION_MODEL = env("AUDIO_TRANSCRIPTION_MODEL")
MOSTRAR_PROCESANDO = str(env("MOSTRAR_PROCESANDO", "true")).lower() == "true"

SESSION_TELEFONOS = {}
PROCESSED_MESSAGES = set()

WEB_PASSWORD = env("WEB_PASSWORD")

app = FastAPI()

def check_password(request: Request):
    pw = request.headers.get("X-Web-Password")
    if pw != WEB_PASSWORD:
        raise HTTPException(status_code=403, detail="Acceso denegado.")

@app.get("/webhook")
async def webhook_get(hub_mode: str = Query(None, alias="hub.mode"),
                     hub_verify_token: str = Query(None, alias="hub.verify_token"),
                     hub_challenge: str = Query(None, alias="hub.challenge")):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge or "", status_code=200)
    return PlainTextResponse("Unauthorized", status_code=403)

@app.post("/webhook")
async def webhook_post(request: Request):
    try:
        body = await request.json()
        value = body["entry"][0]["changes"][0]["value"]
        metadata = value.get("metadata", {})
        to_number = metadata.get("display_phone_number")
        if to_number != TELEFONO_WA:
            print(f"Ignorando mensaje para {to_number}, solo proceso {TELEFONO_WA}")
            return JSONResponse(content={"status": "not_for_this_number"}, status_code=200)

        msg = value["messages"][0]
        msg_id = msg.get("id")

        if not msg_id or msg_id.strip() == "":
            pass
        else:
            if msg_id in PROCESSED_MESSAGES:
                print(f"Mensaje duplicado recibido: {msg_id}")
                return JSONResponse(content={"status": "duplicate"}, status_code=200)
            PROCESSED_MESSAGES.add(msg_id)

        phone, msg_type = msg["from"], msg["type"]
        SESSION_TELEFONOS[phone] = phone
        send_message_to_whatsapp(phone, None, typing_indicator=True, msg_id=msg_id)

        def get_user_text(m):
            if m["type"] == "text":
                return m["text"]["body"]
            if m["type"] == "audio":
                media_id = m["audio"]["id"]
                url = requests.get(ENDPOINT_RETREIVE_MEDIA.format(media_id=media_id),
                                   headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}).json().get("url")
                if not url: return "Error al obtener audio"
                temp = f"audio_{uuid.uuid4()}.ogg"
                try:
                    with open(temp, "wb") as f:
                        f.write(requests.get(url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}).content)
                    with open(temp, "rb") as f:
                        return requests.post(
                            ENDPOINT_TRANSCRIPTIONS_AUDIO,
                            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                            files={"file": f}, data={"model": AUDIO_TRANSCRIPTION_MODEL}
                        ).json().get("text", "No se pudo transcribir el audio.")
                except Exception as e:
                    print("Error al procesar audio:", e)
                    return "Error al procesar audio"
                finally:
                    if os.path.exists(temp): os.remove(temp)
            return None

        user_text = get_user_text(msg)
        if user_text is None:
            if MOSTRAR_PROCESANDO:
                send_message_to_whatsapp(phone, "Procesando... ⚙️")
            send_message_to_whatsapp(phone, "Disculpa pero todavía no soporto este tipo de mensajes...")
            return JSONResponse(content={"status": "unsupported_type"})

        if MOSTRAR_PROCESANDO:
            send_message_to_whatsapp(phone, "Procesando... ⚙️")

        respuesta = chat(phone, user_text)
        send_message_to_whatsapp(phone, respuesta)
        return JSONResponse(content={"status": "message_processed"})
    except Exception as e:
        print("Error general:", e)
        traceback.print_exc()
        return JSONResponse(content={"status": "error"}, status_code=500)

@app.post("/out_msg")
async def out_msg_post(request: Request):
    data = await request.json()
    return send_message_to_whatsapp(data.get("phone"), data.get("text"))

@app.get("/out_msg")
async def out_msg_get(phone: str = Query(None), text: str = Query(None)):
    return send_message_to_whatsapp(phone, text)

def send_message_to_whatsapp(phone, text, typing_indicator=False, msg_id=None):
    payload = {
        "messaging_product": "whatsapp"
    }
    if typing_indicator and msg_id:
        payload["status"] = "read"
        payload["message_id"] = msg_id
        payload["typing_indicator"] = {"type": "text"}
    else:
        payload["to"] = phone
        payload["text"] = {"body": text}
    r = requests.post(
        ENDPOINT_OUT_MSG,
        headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )
    try:
        res = r.json()
    except Exception:
        res = {"error": "No se pudo decodificar respuesta"}
    print(res)
    return JSONResponse(content=res)

# ---- ZONA PROTEGIDA POR CONTRASEÑA ----

@app.post("/upload_excel")
async def upload_excel_post(
    request: Request,
    excel: UploadFile = File(...),
):
    check_password(request)
    if not excel.filename:
        return PlainTextResponse("No se seleccionó ningún archivo",
                                 headers={"Content-Type": "text/plain; charset=utf-8"})
    content = await excel.read()
    print("Tamaño del archivo recibido:", len(content))
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(excel.filename)[-1]) as tmp:
            tmp.write(content)
            filepath = tmp.name
        excel_a_sqlite(excel_file=filepath, db_file='STOCK.db', tabla='STOCK')
        poblar_embeddings(db_file='STOCK.db', tabla='STOCK')
        return PlainTextResponse('¡Archivo subido y base de datos actualizada con éxito!',
                                 headers={"Content-Type": "text/plain; charset=utf-8"})
    except Exception as e:
        return PlainTextResponse(f'Error: {e}',
                                 headers={"Content-Type": "text/plain; charset=utf-8"})

@app.get("/upload_excel")
async def upload_excel_get(request: Request):
    check_password(request)
    html = '''
        <h2>Subir nuevo Excel de stock</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="excel" accept=".xlsx,.xls" required>
            <button type="submit">Subir y Actualizar Base de Datos</button>
        </form>
    '''
    return HTMLResponse(content=html)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())

@app.post("/preview_excel")
async def preview_excel(
    request: Request,
    excel: UploadFile = File(...),
):
    check_password(request)
    if not excel.filename:
        return HTMLResponse("<div style='color:red;'>No se seleccionó ningún archivo</div>",
                            headers={"Content-Type": "text/html; charset=utf-8"})
    try:
        df = pd.read_excel(excel.file)
        tabla_html = df.head(20).to_html(index=False, classes="excel-table", border=1)
        return HTMLResponse(
            f'''
            <div><b>Vista previa (primeras 20 filas):</b></div>
            <div style="overflow:auto;max-width:100vw">{tabla_html}</div>
            ''',
            headers={"Content-Type": "text/html; charset=utf-8"}
        )
    except Exception as e:
        return HTMLResponse(
            f"<div style='color:red;'>Error al leer el Excel: {e}</div>",
            headers={"Content-Type": "text/html; charset=utf-8"}
        )
