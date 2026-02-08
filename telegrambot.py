from dotenv import load_dotenv
import logging
import psycopg2
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Lógica simple: Recibe mensaje -> Separa por ":" -> INSERT en DB


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
        text="👋 ¡Hola! Envía frases en el formato:\n\n Autor : Libro(opcional) : " \
        "Categoria(opcional) : Frase"
    )

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ID:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return
    
    texto = update.message.text
    # Split inteligente (máximo 3 cortes para permitir dos puntos en la frase)
    partes = [p.strip() for p in texto.split(':', 3) if p.strip()]

    if len(partes) == 4:
        autor_input, libro_input, categoria_input, frase = partes
    elif len(partes) == 3:
        autor_input, libro_input, frase = partes
        categoria_input = "General"
    elif len(partes) == 2:
        autor_input, frase = partes
        libro_input = "Fragmentos"
        categoria_input = "General"
    else:
        await update.message.reply_text("⚠️ Formato incorrecto. Usa: Autor" \
        " : Libro : Categoria : Frase")
        return

    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                
                # --- 1. BUSCAR AUTOR (Modo Inteligente) ---
                # Buscamos si algo en la BD se parece a lo que escribiste
                cur.execute("""
                    SELECT id, nombre FROM autores 
                    WHERE lower(f_unaccent(nombre)) 
                    LIKE lower(f_unaccent(%s))
                    LIMIT 1;
                """, (f"%{autor_input}%",)) # Agregamos % para buscar coincidencias parciales
                
                res = cur.fetchone()

                if res:
                    autor_id, nombre_real = res
                    # Opcional: Avisar si corrigió el nombre
                    if nombre_real.lower() != autor_input.lower():
                        print(f"🤓 Auto-corrección: '{autor_input}' -> '{nombre_real}'")
                else:
                    # Si no encuentra nada parecido, crea uno nuevo
                    cur.execute("INSERT INTO autores (nombre) VALUES (%s) RETURNING id;",
                    (autor_input,))
                    autor_id = cur.fetchone()[0]

                cats_obligatorias = ["General", "clasico"] 
                
                for cat_nombre in cats_obligatorias:
                    # A. Buscamos el ID de la categoría 
                    # (por si acaso cambia el ID en el futuro)
                    cur.execute("SELECT id FROM categorias " \
                    "WHERE lower(categoria) = lower(%s)",
                    (cat_nombre,))
                    cat_res = cur.fetchone()
                    
                    if cat_res:
                        cat_obligatoria_id = cat_res[0]
                    else:
                        # Si por alguna razón borraste 'General', la crea de nuevo
                        cur.execute("INSERT INTO categorias (categoria) " \
                        "VALUES (%s) RETURNING id",
                        (cat_nombre,))
                        cat_obligatoria_id = cur.fetchone()[0]
                    
                    # B. La vinculamos al autor (Si ya la tiene, no hace nada)
                    cur.execute("""
                        INSERT INTO autor_categorias (autor_id, categoria_id) 
                        VALUES (%s, %s) 
                        ON CONFLICT (autor_id, categoria_id) DO NOTHING;
                    """, (autor_id, cat_obligatoria_id))
                
                # --- 2. BUSCAR LIBRO (Modo Inteligente) ---
                cur.execute("""
                    SELECT id, titulo FROM libros 
                    WHERE lower(f_unaccent(titulo)) LIKE lower(f_unaccent(%s)) 
                    AND autor_id = %s
                    LIMIT 1;
                """, (f"%{libro_input}%", autor_id))
                
                res = cur.fetchone()

                if res:
                    libro_id, titulo_real = res
                else:
                    cur.execute("INSERT INTO libros (titulo, autor_id) VALUES (%s, %s) RETURNING id;",
                    (libro_input, autor_id))
                    libro_id = cur.fetchone()[0]

                # --- 3. BUSCAR CATEGORÍA (Modo Inteligente) ---
                # Esto ayuda con 'existencialista' -> 'Existencialismo'
                # OJO: Solo funciona si la palabra input está CONTENIDA
                # en la de la base de datos
                # Ej: Input "Existencial" encuentra "Existencialismo". 
                # Input "Existencialista" NO encuentra 
                # "Existencialismo" (porque sobra 'ista').
                # Truco: Escribe la raíz de la palabra.
                cur.execute("""
                    SELECT id, categoria FROM categorias 
                    WHERE lower(f_unaccent(categoria)) LIKE lower(f_unaccent(%s))
                    LIMIT 1;
                """, (f"%{categoria_input}%",))
                
                res = cur.fetchone()

                if res:
                    categoria_id, cat_real = res
                else:
                    # Si no existe, la creamos (con protección de conflicto por si acaso)
                    cur.execute("""
                        INSERT INTO categorias (categoria) VALUES (%s) 
                        ON CONFLICT (lower(f_unaccent(categoria))) 
                        DO UPDATE SET categoria=EXCLUDED.categoria 
                        RETURNING id;
                    """, (categoria_input,))
                    categoria_id = cur.fetchone()[0]
                
                # --- 4. RELACIÓN AUTOR-CATEGORÍA ---
                cur.execute("""
                    INSERT INTO autor_categorias (autor_id, categoria_id) 
                    VALUES (%s, %s) 
                    ON CONFLICT (autor_id, categoria_id) DO NOTHING;
                """, (autor_id, categoria_id))
                
                # --- 5. INSERTAR FRASE ---
                cur.execute("""
                    INSERT INTO frases (autor_id, libro_id, frase, publicado) 
                    VALUES (%s, %s, %s, FALSE)
                    ON CONFLICT (lower(f_unaccent(frase))) DO NOTHING;
                """, (autor_id, libro_id, frase))
                filas_afectadas = cur.rowcount 

                if filas_afectadas > 0:
                    # Mensaje más informativo
                    autor_display = nombre_real if 'nombre_real' in locals() else autor_input
                    libro_display = titulo_real if 'titulo_real' in locals() else libro_input
                    respuesta = f"✅ Guardado bajo:\n👤 {autor_display}\n📖 {libro_display}\n💬 {frase}"
                    await update.message.reply_text(respuesta)
                else:
                    await update.message.reply_text(f"👀 Esa frase ya existía.")
    
    except psycopg2.Error as e:
    
        await update.message.reply_text(f"❌ Error DB: {e.pgerror}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")



if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    
    print("📲 Bot de Telegram ESCUCHANDO...")
    app.run_polling()