#!/bin/bash

# Arrancar el bot de Twitter en segundo plano (con el simbolo &)
python bot_db.py &

# Arrancar el bot de Telegram en segundo plano
python telegrambot.py &

# Esperar a que terminen (truco para que el contenedor no se apague)
wait