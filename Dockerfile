FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# --- NUEVO: Damos permisos de ejecución al script ---
RUN chmod +x start.sh

# --- NUEVO: Ejecutamos el script capitán ---
CMD ["./start.sh"]