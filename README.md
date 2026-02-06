# 📚 Philosophy Bot: Pipeline de Telegram a X (Twitter)

Este proyecto es un sistema automatizado de **ETL (Extract, Transform, Load)** y publicación programada. Permite capturar frases filosóficas a través de un bot de Telegram, almacenarlas en una base de datos **PostgreSQL** y publicarlas automáticamente en **X (Twitter)** con un formato personalizado.



## 🛠️ Tecnologías y Herramientas

* **Lenguaje:** Python 3.x 
* **Base de Datos:** PostgreSQL (psycopg2) 
* **APIs:** * Twitter API v2 (Tweepy) 
    * Telegram Bot API (python-telegram-bot) 
* **Entorno:** Python-dotenv para gestión de credenciales 

## 🏗️ Arquitectura del Sistema

1.  **Ingesta (Telegram):** El script `telegrambot.py` recibe mensajes, los procesa y los inserta en la base de datos. Solo el usuario autorizado (definido por ID) puede añadir frases. 
2.  **Base de Datos:** Estructura relacional que vincula frases con autores y categorías. Incluye un sistema de control para no repetir publicaciones (`publicado = FALSE`). 
3.  **Publicación (Twitter):** El script `bot_db.py` selecciona una frase aleatoria, verifica que no exceda los 280 caracteres, le añade un "remate" según su categoría y la publica. 

## 📁 Estructura del Proyecto

* `bot_db.py`: Gestiona la lógica de selección y publicación en X. 
* `telegrambot.py`: Gestiona la recepción de datos vía Telegram. 
* `requirements.txt`: Lista de dependencias del proyecto. 
* `.env`: Archivo (protegido) con tokens de acceso y URLs de conexión. 

## 🚀 Configuración

### 1. Instalación de Dependencias

bash
pip install -r requirements.txt


### 2. Variables de Entorno (.env)
Crea un archivo .env en la raíz con las siguientes variables:
#### Twitter Keys
AK='tu_consumer_key'
AKS='tu_consumer_secret'
AT='tu_access_token'
ATS='tu_access_token_secret'

#### Telegram Config
TTOKEN='tu_telegram_bot_token'
TELEGRAMID='tu_id_de_usuario'

#### Database URL
DB_URL='postgresql://usuario:password@localhost:5432/nombre_db'

## MODO DE USO.
Carga de Datos (Telegram)
Envía un mensaje al bot de Telegram siguiendo este formato: Autor | Frase | Libro | Categoría

Ejemplo: Friedrich Nietzsche | Dios ha muerto | Así habló Zaratustra | Existencialismo

Ejecución del Publicador
Para iniciar el ciclo de publicaciones automáticas:

    Bash
    python bot_db.py
    El bot intentará publicar cada 1.5 horas. 

Si no hay frases disponibles, reintentará en 30 minutos. 

Si el tweet es demasiado largo, marcará la frase y pasará a la siguiente automáticamente. 

Desarrollado con fines de automatización y difusión de pensamiento filosófico.

