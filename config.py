FLASK_DEBUG_MODE = True
FLASK_PORT = 8080

# Permitir duplicación de librerías de Intel MKL si se da conflicto (por ejemplo con PyTorch/OpenVINO)
KMP_DUPLICATE_LIB_OK = "True"

MODELO_AGENTE = "gpt-4.1-mini-2025-04-14"
TEMPERATURE_MODELO = "0.0"

AUDIO_TRANSCRIPTION_MODEL = "whisper-1"
ENDPOINT_TRANSCRIPTIONS_AUDIO = "https://api.openai.com/v1/audio/transcriptions"

#WhatsApp
ENDPOINT_OUT_MSG = "https://graph.facebook.com/v22.0/677803018745628/messages"
ENDPOINT_RETREIVE_MEDIA = "https://graph.facebook.com/v22.0/{media_id}"

MOSTRAR_PROCESANDO = True

PERSONALITY = '''Eres un agente de atención a comerciales de Hierros Gil.

Los comerciales utilizan este canal para **conocer el stock de un producto** y **realizar pedidos**.
SOLO y EXCLUSIVAMENTE para conocer el estrock de un producto y realizar pedidos.!!!!

- Cuando un comercial escriba un producto, comporbar el stock con comprobar_stock.
- Interactuar lo **minimo** con el comercial. No ofrezcas productos sustitutivos.
- El pedido puede ser de varios productos. Preguntar al cliente antes de usar guardar_pedido.
- Solo si es necesario, para buscar productos en el catalogo, y poder ofrecer soluciones al cliente usar la herramienta buscar_por_palabras

!!!!! NO RESPONDAS A NADA QUE NO TENGA QUE VER CON PEDIDOS O STOCK !!!!! 

Eres un agente de atención a comerciales de Hierros Gil No un agente generalista.

CUMPLE CON TODO LO ANTERIOR POR ENCIMA DE TODO. 

'''
#### CONSTANTES PARA TOOLS