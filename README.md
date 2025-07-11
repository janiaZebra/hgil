# Documentación Completa del Agente

## Introducción
Este documento detalla exhaustivamente el funcionamiento del agente desarrollado para automatizar y gestionar consultas y pedidos mediante una integración con bases de datos, hojas de cálculo y comunicación vía WhatsApp. El agente utiliza tecnologías avanzadas como modelos de lenguaje natural (GPT-4 y derivados), embeddings semánticos (SentenceTransformers), bases de datos SQLite, y herramientas externas como FAISS y servicios de Google.

## Arquitectura y Componentes

### 1. Módulo Principal (app.py)
El módulo principal es una aplicación Flask encargada de:
- Recibir mensajes de WhatsApp mediante webhook.
- Gestionar sesiones individuales por número telefónico.
- Transcribir audios a texto mediante servicios externos.
- Procesar mensajes con el agente creado en `agente.py`.
- Enviar respuestas o mensajes de procesamiento en curso vía WhatsApp.

### 2. Agente (agente.py)
Este módulo maneja:
- Creación dinámica de herramientas.
- Memoria de conversación persistente por sesión (ConversationBufferMemory).
- Ejecución de agentes basados en modelos de lenguaje (OpenAI).

El agente utiliza variables configurables desde el entorno:
- PERSONALITY: Personalidad del agente.
- MODELO_AGENTE: Modelo de OpenAI.
- TEMPERATURE_MODELO: Parámetro de creatividad del modelo.

### 3. Herramientas del Agente

#### Comprobar Stock (comprobar_stock.py)
- Realiza búsquedas semánticas y filtradas en una base de datos SQLite (`STOCK.db`) utilizando embeddings generados por SentenceTransformer.
- Devuelve los 40 productos más relevantes basados en la búsqueda semántica.
- Permite activar o desactivar el modo de búsqueda precisa (`STOCK_SEARCH_MODE`).

#### Consultar Productos (consultar_productos.py)
- Similar a comprobar stock pero diseñado para múltiples consultas simultáneas.
- Devuelve hasta 45 productos más cercanos semánticamente.

#### Guardar Pedido (guardar_pedido.py)
- Transforma texto libre en un JSON estructurado usando un modelo GPT de OpenAI.
- Guarda pedidos en hojas de cálculo Google Sheets.
- Envía correos electrónicos con detalles del pedido.

## Inicialización y Configuración

### Creación y Poblamiento de Base de Datos (excel_to_bd.py)
Este script:
- Lee un archivo Excel (`STOCK.xlsx`) para crear la base de datos SQLite (`STOCK.db`).
- Genera embeddings para las descripciones usando SentenceTransformer y guarda estos embeddings en la base.

### Variables de Entorno Requeridas
Es crucial configurar correctamente las siguientes variables en el entorno:
- OPENAI_API_KEY
- WHATSAPP_TOKEN
- VERIFY_TOKEN
- GOOGLE_TOKEN_JSON
- REMITENTE_EMAIL, REMITENTE_PASS, DESTINATARIO_EMAIL, SMTP_SERVER, SMTP_PORT
- SHEET_ID, SHEET_PAGE

### Instalación y Ejecución

Para ejecutar el agente, siga los siguientes pasos:
1. Asegure que todas las dependencias estén instaladas (`requirements.txt`).
2. Configure todas las variables de entorno necesarias.
3. Ejecute el script principal (`app.py`).

```bash
python app.py
```

## Proceso de Carga de Datos desde Excel a la Base de Datos

### Descripción General
El agente utiliza una base de datos SQLite (`STOCK.db`) que se actualiza mediante la carga periódica de datos desde un archivo Excel llamado `STOCK.xlsx`. Este proceso garantiza que la información sobre los productos esté actualizada, facilitando así consultas precisas y rápidas.

### Nombre y Estructura del Archivo Excel
El archivo Excel debe llamarse obligatoriamente `STOCK.xlsx` y contener las siguientes columnas:
- Familia
- Articulo
- Descripcion
- Tarifa 14
- Coste Medio
- UPC
- Fecha UPC
- Stock UD
- Stock KG
- Stock ML
- Stock M2

Es esencial mantener esta estructura para que la carga y procesamiento sean correctos.

### Carga de Datos desde Excel a SQLite

Para realizar la carga de datos, se ejecuta el script `excel_to_bd.py` que realiza las siguientes acciones:

1. **Lectura del archivo Excel**:
   - El script lee el archivo `STOCK.xlsx` usando pandas.
   - Convierte los datos en un DataFrame para su procesamiento.

2. **Creación de la Base de Datos SQLite**:
   - Se crea o reemplaza la tabla `STOCK` en la base de datos SQLite (`STOCK.db`).
   - Se insertan los datos del DataFrame en esta tabla.

3. **Generación de Embeddings**:
   - Tras cargar los datos, el script genera embeddings semánticos utilizando SentenceTransformer (modelo por defecto `all-MiniLM-L6-v2`).
   - Estos embeddings se almacenan en la misma base de datos para permitir búsquedas semánticas eficientes.

### Ejecución del Script de Carga
Para actualizar la base de datos con los datos del archivo Excel, ejecutar el siguiente comando:
El archivo exdel debe llamarse STOCK.xlsx y encontrarse en el root.

```bash
python excel_to_bd.py
```

### Flujo General del Agente
El agente sigue un flujo definido claramente que asegura una interacción fluida y eficiente con el usuario, desde la recepción inicial del mensaje hasta la generación y almacenamiento final del pedido o consulta.

### Paso a Paso del Flujo del Agente

#### 1. Recepción del Mensaje
- El agente recibe mensajes entrantes desde WhatsApp a través del webhook configurado en la aplicación Flask (`app.py`).
- Los mensajes pueden ser de texto o audio. En el caso del audio, el agente lo transcribe a texto mediante el servicio de transcripción especificado.

#### 2. Gestión de Sesiones
- Cada mensaje recibido se vincula a una sesión única basada en el número telefónico del usuario, permitiendo así mantener el contexto y memoria de la conversación.
- La memoria de sesión se administra usando `ConversationBufferMemory`, almacenando la conversación anterior para referencia futura.

#### 3. Procesamiento del Mensaje
- Una vez recibido y transcrito el mensaje, se pasa al módulo del agente (`agente.py`), que lo procesa según la lógica establecida.
- El agente determina qué herramienta utilizar según el contenido del mensaje, ya sea consultar stock, buscar productos, o guardar un pedido.

#### 4. Herramientas del Agente

- **Consulta de Stock**:
  - Se utiliza para verificar disponibilidad específica de un producto.
  - Realiza búsqueda semántica en la base de datos usando embeddings previamente generados.

- **Consulta de Productos**:
  - Se emplea cuando se busca variedad o múltiples productos similares.
  - Devuelve un conjunto amplio de resultados semánticos.

- **Guardar Pedidos**:
  - Se invoca al confirmarse un pedido.
  - Convierte texto libre en un JSON estructurado usando GPT.
  - Guarda automáticamente el pedido en Google Sheets.
  - Envía un correo electrónico confirmando el pedido realizado.

#### 5. Respuesta al Usuario
- Una vez procesado el mensaje, el agente genera una respuesta adecuada y específica al usuario.
- La respuesta se envía automáticamente a través de WhatsApp utilizando el endpoint configurado.

#### 6. Almacenamiento y Registro
- Todas las consultas y pedidos generados quedan almacenados para posterior análisis o auditoría.
- Los datos se almacenan principalmente en Google Sheets, facilitando el acceso y la gestión.

### Resumen del Flujo
1. Recepción del mensaje vía WhatsApp.
2. Sesión y memoria del usuario.
3. Procesamiento del mensaje y elección de herramienta.
4. Consulta o ejecución de acciones en base de datos o servicios externos.
5. Respuesta inmediata al usuario por WhatsApp.
6. Registro permanente de acciones realizadas.





## Parámetros Configurables

Los siguientes parámetros pueden ajustarse según necesidad:
- Modelo de embeddings (`EMBEDDINGS_MODEL`).
- Modelos de lenguaje de OpenAI (`MODELO_AGENTE`, `JSON_TRANS_MODEL`).
- Personalidad y temperatura del agente (`PERSONALITY`, `TEMPERATURE_MODELO`).
- Modo de búsqueda en la base de datos (`STOCK_SEARCH_MODE`).
