from dotenv import load_dotenv
import logging
import psycopg2
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# print(telegram.__version__)
# Lógica simple: Recibe mensaje -> Separa por "|" -> INSERT en DB

load_dotenv()
TOKEN = os.getenv('TTOKEN')
ID = int(os.getenv('TELEGRAMID'))
DB_URL = os.getenv('DB_URL')  

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)


async def start(update:Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ID:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 ¡Hola! Envía frases en el formato:\n\n Autor : Libro(opcional) : Categoria(opcional) : Frase"
    )

async def manejar_mensaje(update:Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ID:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return
    
    texto = update.message.text
    partes = [p.strip() for p in texto.split(':') if p.strip()]
    if len(partes) < 2: 
        await update.message.reply_text("⚠️ Formato incorrecto. Usa: Autor : Libro(opcional) : Categoria(opcional) : Frase")
        return

    # logica para manejar distintos tipos de mensajes 
    if len(partes) == 4:
        autor, libro, categoria, frase = partes
    elif len(partes) == 3:
        autor, libro, frase = partes
        categoria = "General"
    elif len(partes) == 2:
        autor, frase = partes
        libro = "Fragmentos"
        categoria = "General"
    else:
        await update.message.reply_text("⚠️ Formato: Autor : Libro : Categoria : Frase")
        return

    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur: # Usamos 'with' para el cursor también
                
                # --- 1. MANEJO DEL AUTOR ---
                # Buscamos usando tu función mágica 'f_unaccent' para ser tolerantes a fallos
                cur.execute("""
                    SELECT id FROM autores 
                    WHERE lower(f_unaccent(nombre)) = lower(f_unaccent(%s));
                """, (autor,))
                res = cur.fetchone()

                if res:
                    autor_id = res[0] # Ya existía, usamos su ID
                else:
                    # No existe, lo creamos
                    cur.execute("INSERT INTO autores (nombre) " \
                    "VALUES (%s) RETURNING id;", (autor,))
                    autor_id = cur.fetchone()[0]

                # --- 2. MANEJO DEL LIBRO ---
                # Buscamos el libro que coincida en Título Y Autor
                cur.execute("""
                    SELECT id FROM libros 
                    WHERE lower(f_unaccent(titulo)) = lower(f_unaccent(%s)) 
                    AND autor_id = %s;
                """, (libro, autor_id))
                res = cur.fetchone()

                if res:
                    libro_id = res[0]
                else:
                    cur.execute("INSERT INTO libros (titulo, autor_id) " \
                    "VALUES (%s, %s) RETURNING id;", (libro, autor_id))
                    libro_id = cur.fetchone()[0]

                # --- 3. MANEJO DE CATEGORÍA ---
                # Aquí asumimos que categorias sigue teniendo un constraint simple, 
                # pero usamos la misma lógica segura por si acaso.
                cur.execute("SELECT id FROM categorias WHERE categoria = %s;", (categoria,))
                res = cur.fetchone()

                if res:
                    categoria_id = res[0]
                else:
                    # Usamos ON CONFLICT aquí por si acaso la tabla categorias es simple
                    # Si falla, puedes cambiarlo al estilo SELECT/INSERT como arriba
                    cur.execute("""
                        INSERT INTO categorias (categoria) 
                        VALUES (%s) 
                        ON CONFLICT (categoria) 
                        DO UPDATE SET categoria=EXCLUDED.categoria 
                        RETURNING id;
                    """, (categoria,))
                    categoria_id = cur.fetchone()[0]
                
                # --- 4. RELACIÓN AUTOR-CATEGORÍA ---
                cur.execute("""
                    INSERT INTO autor_categorias (autor_id, categoria_id) 
                    VALUES (%s, %s) 
                    ON CONFLICT (autor_id, categoria_id) DO NOTHING;
                """, (autor_id, categoria_id))
                
                # --- 5. INSERTAR LA FRASE (Lógica Pro) ---
            cur.execute("""
                INSERT INTO frases (autor_id, libro_id, frase, publicado) 
                VALUES (%s, %s, %s, FALSE)
                ON CONFLICT (lower(f_unaccent(frase))) DO NOTHING;
            """, (autor_id, libro_id, frase))
            
            # Verificamos qué pasó
            filas_afectadas = cur.rowcount 

            if filas_afectadas > 0:
                await update.message.reply_text(f"✅ Guardado: {frase[:30]}... - {autor}")
            else:
                # Si rowcount es 0, significa que el DO NOTHING entró en acción
                await update.message.reply_text(f"👀 Ojo: Esa frase de {autor} ya existía en la base de datos.")
                await update.message.reply_text(f"✅ Guardado: {frase[:30]}... - {autor}")
    except psycopg2.Error as e:
        # Capturamos errores específicos de base de datos
        await update.message.reply_text(f"❌ Error de Base de Datos: {e.pgerror}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error general: {e}")
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    
    print("📲 Bot de Telegram ESCUCHANDO...")
    app.run_polling()