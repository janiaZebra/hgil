FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Si tu app depende de algún otro archivo (por ejemplo, config.py o agente.py), asegúrate de que estén presentes en el mismo directorio al construir la imagen.

ENV PORT=8080

# Google Cloud Run recomienda gunicorn para producción, pero si quieres debug puro puedes usar flask directamente (no recomendado en producción)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
