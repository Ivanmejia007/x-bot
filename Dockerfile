# 1. Usamos una versión ligera de Python como base
FROM python:3.9-slim

# 2. Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiamos el archivo de dependencias
COPY requirements.txt .

# 4. Instalamos las librerías (como tweepy, psycopg2-binary, python-dotenv)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el resto de tu código (tu script .py y el .env)
COPY . .
