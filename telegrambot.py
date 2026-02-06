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
        text="👋 ¡Hola! Envía frases en el formato:\n\n Autor | Frase | Libro | Categoria |"
    )

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ID:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return
    
    texto = update.message.text
    partes = texto.split('|')
    if len(partes) < 2: 
        await update.message.reply_text("⚠️ Formato incorrecto. Usa: Autor | Frase | Libro")
        return

    if len(partes) >= 2:
        autor = partes[0].strip()
        frase = partes[1].strip()
        libro = partes[2].strip() if len(partes) > 2 else "Fragmentos"
        categoria = partes[3].strip() if len(partes) > 3 else "General"
        
        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            
            # Manejamos la inserción de autor
            cur.execute("SELECT id FROM autores WHERE nombre ILIKE %s", (autor,))
            resultado_autor = cur.fetchone()
            if resultado_autor:
                autor_id = resultado_autor[0]
            else:
                cur.execute("INSERT INTO autores (nombre) VALUES (%s) RETURNING id;", (autor,))
                autor_id = cur.fetchone()[0]
            cur.execute("SELECT id FROM categorias WHERE categoria ILIKE %s", (categoria,))
            resultado_categoria = cur.fetchone()
            # Manejamos la inserción de categoría
            if resultado_categoria:
                categoria_id = resultado_categoria[0]
            else:
                cur.execute("INSERT INTO categorias (categoria) VALUES (%s) RETURNING id;", (categoria,))
                categoria_id = cur.fetchone()[0]
            # Opción más segura: especificar dónde está el conflicto
            cur.execute("""
                INSERT INTO autor_categorias (autor_id, categoria_id) 
                VALUES (%s, %s) 
                ON CONFLICT (autor_id, categoria_id) DO NOTHING;
            """, (autor_id, categoria_id))
            # Finalmente, insertamos la frase
            cur.execute("INSERT INTO frases (autor_id, frase, libro, publicado) VALUES (%s, %s, %s, %s);", (autor_id, frase, libro, False))
            conn.commit()
            cur.close()
            conn.close()
            await update.message.reply_text(f"✅ Guardado: {frase} - {autor}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error al guardar en la base de datos: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    
    print("📲 Bot de Telegram ESCUCHANDO...")
    app.run_polling()