import os
import config
import requests
from flask import Flask, request, jsonify
import uuid
from agente import chat

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ENDPOINT_OUT_MSG = os.getenv("ENDPOINT_OUT_MSG", config.ENDPOINT_OUT_MSG)
ENDPOINT_RETREIVE_MEDIA = os.getenv("ENDPOINT_RETREIVE_MEDIA", config.ENDPOINT_RETREIVE_MEDIA)
ENDPOINT_TRANSCRIPTIONS_AUDIO = os.getenv("ENDPOINT_TRANSCRIPTIONS_AUDIO", config.ENDPOINT_TRANSCRIPTIONS_AUDIO)
AUDIO_TRANSCRIPTION_MODEL = os.getenv("AUDIO_TRANSCRIPTION_MODEL", config.AUDIO_TRANSCRIPTION_MODEL)
MOSTRAR_PROCESANDO = os.getenv("MOSTRAR_PROCESANDO", str(config.MOSTRAR_PROCESANDO)).lower() == "true"

FLASK_DEBUG_MODE = os.getenv("FLASK_DEBUG_MODE", str(config.FLASK_DEBUG_MODE)).lower() == "true"
FLASK_PORT = int(os.getenv("FLASK_PORT", config.FLASK_PORT))

SESSION_TELEFONOS = {}
PROCESSED_MESSAGES = set()


app = Flask(__name__)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Unauthorized", 403

    try:
        msg = request.json["entry"][0]["changes"][0]["value"]["messages"][0]
        msg_id = msg.get("id")
        if msg_id in PROCESSED_MESSAGES:
            print(f"Mensaje duplicado recibido: {msg_id}")
            return jsonify({"status": "duplicate"}), 200
        PROCESSED_MESSAGES.add(msg_id)

        phone, msg_type = msg["from"], msg["type"]
        SESSION_TELEFONOS[phone] = phone

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
            return jsonify({"status": "unsupported_type"})

        if MOSTRAR_PROCESANDO:
            send_message_to_whatsapp(phone, "Procesando... ⚙️")

        respuesta = chat(phone, user_text)
        send_message_to_whatsapp(phone, respuesta)
        return jsonify({"status": "message_processed"})
    except Exception as e:
        print("Error general:", e)
        return jsonify({"status": "error"}), 500



@app.route("/out_msg", methods=["GET", "POST"])
def out_msg():
    data = request.args if request.method == "GET" else (request.get_json(silent=True) or {})
    return send_message_to_whatsapp(data.get("phone"), data.get("text"))


def send_message_to_whatsapp(phone, text):
    r = requests.post(
        ENDPOINT_OUT_MSG,
        headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "messaging_product": "whatsapp",
            "to": phone,
            "text": {"body": text}
        }
    )
    res = r.json()
    print(res)
    return r.json()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

