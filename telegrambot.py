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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ID:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 ¡Hola! Envía frases en el formato:\n\n Autor : Libro : Categoria(opcional) : Frase"
    )

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ID:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return
    
    texto = update.message.text
    partes = [p.strip() for p in texto.split(':') if p.strip()]
    if len(partes) < 2: 
        await update.message.reply_text("⚠️ Formato incorrecto. Usa: Autor : Libro : Categoria(opcional) : Frase")
        return

    if len(partes) >= 2:
        autor = partes[0].strip()
        libro = partes[1].strip() if len(partes) > 2 else "Fragmentos"
        categoria = partes[2].strip() if len(partes) > 3 else "General"
        frase = partes[3].strip()
        
        try:
            
            with psycopg2.connect(DB_URL) as conn:
                cur = conn.cursor()
                
                # Manejamos la inserción de autor
                cur.execute("INSERT INTO autores (nombre) VALUES (%s) " \
                "ON CONFLICT (nombre) " \
                "DO UPDATE SET nombre=EXCLUDED.nombre RETURNING id;", (autor,))
                autor_id = cur.fetchone()[0]

                # Manejamos la insercion de libro
                cur.execute("INSERT INTO libros (titulo) VALUES (%s) " \
                "ON CONFLICT (titulo) " \
                "DO UPDATE SET titulo=EXCLUDED.titulo RETURNING id;", (libro,))
                libro_id = cur.fetchone()[0]

                # Manejamos la inserción de categoría
                cur.execute("INSERT INTO categorias (categoria) VALUES (%s)" \
                "ON CONFLICT (categoria)" \
                "DO UPDATE SET categoria=EXCLUDED.categoria RETURNING id;", (categoria,))
                categoria_id = cur.fetchone()[0]
                
                # Opción más segura: especificar dónde está el conflicto
                cur.execute("""
                    INSERT INTO autor_categorias (autor_id, categoria_id) 
                    VALUES (%s, %s) 
                    ON CONFLICT (autor_id, categoria_id) DO NOTHING;
                """, (autor_id, categoria_id))
                
                # Finalmente, insertamos la frase
                cur.execute("INSERT INTO frases (autor_id, frase, libro_id, publicado) VALUES (%s, %s, %s, %s);", (autor_id, frase, libro_id, False))
                conn.commit()
                await update.message.reply_text(f"✅ Guardado: {frase} - {autor}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error al guardar en la base de datos: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    
    print("📲 Bot de Telegram ESCUCHANDO...")
    app.run_polling()