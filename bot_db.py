import tweepy
import time
import os
from dotenv import load_dotenv 
import psycopg2

load_dotenv()

client = tweepy.Client(
    consumer_key=os.getenv('AK'),
    consumer_secret=os.getenv('AKS'),
    access_token=os.getenv('AT'),
    access_token_secret=os.getenv('ATS')
)

DB_URL = os.getenv('DB_URL')

def obtener_frase_db():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        query = """
        SELECT f.id, f.frase, a.nombre, f.libro, c.id
        FROM frases f
        JOIN autores a ON f.autor_id = a.id
        JOIN autor_categorias ac ON a.id = ac.autor_id
        JOIN categorias c ON ac.categoria_id = c.id
        WHERE f.publicado = FALSE 
        ORDER BY RANDOM() 
        LIMIT 1;
        """
        cur.execute(query)      
        frase = cur.fetchone()
        cur.close()
        conn.close()
        return frase
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

def obtener_remate(categoria_id):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    # Lógica de categorías según el autor
    query = "SELECT texto FROM remates WHERE categoria_id = %s ORDER BY RANDOM() LIMIT 1;"
    cur.execute(query, (categoria_id,))
    res = cur.fetchone()
    conn.close()
    
    return res[0] if res else "Facts."

def marcar_frase_como_publicada_db(id_frase):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("UPDATE frases SET publicado = TRUE WHERE id = %s;", (id_frase,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error al marcar frase como publicada: {e}")


def publicar_frase():
    publicado_con_exito = False
    while not publicado_con_exito:
        print("Intentando publicar una frase...", flush=True)
        frase_data = obtener_frase_db()
        if not frase_data:
            print("No hay frases disponibles para publicar.")
            return False  # Salir de la función si no hay frases
        id_frase, frase, autor, libro, categoria_id = frase_data
        libro_display = libro if libro else "Fragmentos"
        remate = obtener_remate(categoria_id)
        tweet_content = f'"{frase}", {remate}\n\n- {autor}, {libro_display}'
        # --- VALIDACIÓN DE LONGITUD ---
        if len(tweet_content) > 280:
            print(f"⚠️ Tweet demasiado largo ({len(tweet_content)} caracteres). Saltando...")
            # Opcional: Podrías marcarla como 'error' en la DB o simplemente ignorarla por hoy
            marcar_frase_como_publicada_db(id_frase) 
            time.sleep(1) # Pequeña pausa de cortesía
            continue  # Intentar con otra frase
        # --- PUBLICAR EN TWITTER ---
        try:
            client.create_tweet(text=tweet_content)
            print(f"Frase publicada exitosamente. ID: {id_frase}", flush=True)
            marcar_frase_como_publicada_db(id_frase)
            publicado_con_exito = True
        except Exception as e:
            print(f"Error en la API de tweeter: {e}", flush=True)
            return False
    return True
        
if __name__ == "__main__":
    while True:
        intento = publicar_frase()
        if intento:
            print("Publicación completada. Esperando para la siguiente...")
            time.sleep(5400)  # Espera 1.5 horas antes de la siguiente publicación
        else:
            print("No se publicó ninguna frase. Reintentando en 30 minutos...")
            time.sleep(600)  # Espera 10 minutos si no se publicó ninguna frase
            
