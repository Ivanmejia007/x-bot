async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ID:
        return # Ignorar silenciosamente o enviar error

    texto = update.message.text
    # Dividir y limpiar cada parte
    partes = [p.strip() for p in texto.split('|')]
    
    if len(partes) < 2: 
        await update.message.reply_text("⚠️ Formato: Autor | Frase | Libro | Categoria")
        return

    autor, frase = partes[0], partes[1]
    libro = partes[2] if len(partes) > 2 else "Fragmentos"
    categoria = partes[3] if len(partes) > 3 else "General"

    try:
        # Uso de 'with' para asegurar que la conexión se cierre pase lo que pase
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # 1. Autor
                cur.execute("INSERT INTO autores (nombre) VALUES (%s) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING id;", (autor,))
                autor_id = cur.fetchone()[0]

                # 2. Libro
                cur.execute("INSERT INTO libros (titulo) VALUES (%s) ON CONFLICT (titulo) DO UPDATE SET titulo=EXCLUDED.titulo RETURNING id;", (libro,))
                libro_id = cur.fetchone()[0]

                # 3. Categoría
                cur.execute("INSERT INTO categorias (categoria) VALUES (%s) ON CONFLICT (categoria) DO UPDATE SET categoria=EXCLUDED.categoria RETURNING id;", (categoria,))
                categoria_id = cur.fetchone()[0]

                # 4. Relación Autor-Categoría
                cur.execute("INSERT INTO autor_categorias (autor_id, categoria_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (autor_id, categoria_id))

                # 5. Frase
                cur.execute("INSERT INTO frases (autor_id, frase, libro_id, publicado) VALUES (%s, %s, %s, False);", (autor_id, frase, libro_id))
                
            conn.commit() # Confirmar cambios
        await update.message.reply_text(f"✅ ¡Guardado con éxito!")
    except Exception as e:
        logging.error(f"Error DB: {e}")
        await update.message.reply_text(f"❌ Error al guardar.")