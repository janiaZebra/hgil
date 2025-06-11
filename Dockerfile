FROM python:3.12-slim
# Establece el directorio de trabajo
WORKDIR /app
# Instala dependencias del sistema necesarias (ajustá según necesidades reales)
# RUN apt-get update && apt-get install -y \
#     gcc \
#     g++ \
#     libffi-dev \
#     curl \
#     wget \
#     dnsutils \
#     --no-install-recommends && rm -rf /var/lib/apt/lists/*
# Actualiza el sistema e instala dependencias necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# Copia e instala dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt -f https://download.pytorch.org/whl/cpu/torch_stable.html
# RUN pip install --no-cache-dir -f https://download.pytorch.org/whl/cpu/torch_stable.html torch==2.2.2+cpu
# RUN pip install --no-cache-dir --upgrade -r requirements.txt
# Copia el código fuente
COPY ../.. /app/
# Expone el puerto 8080 (puerto usado por uvicorn)
EXPOSE 8000
# Comando para iniciar la aplicación
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["python", "app.py"]