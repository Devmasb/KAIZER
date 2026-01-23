import telebot
import subprocess
from telebot import types

TOKEN = "8218293709:AAHhtbiAsVtG3HHflIunyzgv5q2uP41F5DI"
CHAT_ID = 1155988084  # tu chat ID personal para seguridad

bot = telebot.TeleBot(TOKEN)

# Variable temporal para flujo de configuración
esperando_coef = False


def ejecutar_systemctl(comando):
    try:
        resultado = subprocess.run(
            ["sudo", "systemctl", comando, "kaizer"],
            capture_output=True,
            text=True
        )
        return f"systemctl {comando} kaizer ejecutado correctamente.\n{resultado.stdout}"
    except subprocess.CalledProcessError as e:
        return f"⚠️ Error al ejecutar systemctl {comando} kaizer:\n{e.stderr}"


def leer_config():
    config = {}
    try:
        with open("config.env") as f:
            for line in f:
                if "=" in line:
                    clave, valor = line.strip().split("=", 1)
                    config[clave] = valor
    except FileNotFoundError:
        pass
    return config


def actualizar_config(clave, valor):
    config = leer_config()
    config[clave] = valor
    with open("config.env", "w") as f:
        for k, v in config.items():
            f.write(f"{k}={v}\n")


@bot.message_handler(commands=['menu'])
def menu(message):
    if message.chat.id == CHAT_ID:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("▶️ Iniciar bot", callback_data="startbot")
        btn2 = types.InlineKeyboardButton("⏹️ Detener bot", callback_data="stopbot")
        btn3 = types.InlineKeyboardButton("📊 Estado bot", callback_data="statusbot")
        btn4 = types.InlineKeyboardButton("⚙️ Configurar coeficiente", callback_data="setcoef")
        btn5 = types.InlineKeyboardButton("🔀 Toggle DETENER_EN_POSITIVO", callback_data="toggle_detener")
        btn6 = types.InlineKeyboardButton("🔄 Toggle RETOMAR_ESTADO", callback_data="toggle_retomar")
        markup.add(btn1, btn2, btn3)
        markup.add(btn4, btn5, btn6)

        bot.send_message(message.chat.id, "Selecciona una opción:", reply_markup=markup)
    else:
        bot.reply_to(message, "❌ No autorizado")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global esperando_coef
    if call.message.chat.id == CHAT_ID:
        if call.data == "startbot":
            salida = ejecutar_systemctl("start")
            bot.send_message(call.message.chat.id, salida)
        elif call.data == "stopbot":
            salida = ejecutar_systemctl("stop")
            bot.send_message(call.message.chat.id, salida)
        elif call.data == "restartbot":
            salida = ejecutar_systemctl("restart")
            bot.send_message(call.message.chat.id, salida)
        elif call.data == "statusbot":
            salida = ejecutar_systemctl("status")
            bot.send_message(call.message.chat.id, salida)
        elif call.data == "setcoef":
            esperando_coef = True
            bot.answer_callback_query(call.id, "Configurar coeficiente")
            bot.send_message(call.message.chat.id, "📐 Introduce el valor de COEFICIENTE_ESCALA:")
        elif call.data == "toggle_detener":
            config = leer_config()
            estado_actual = config.get("DETENER_EN_POSITIVO", "false").lower()
            nuevo_estado = "false" if estado_actual == "true" else "true"
            actualizar_config("DETENER_EN_POSITIVO", nuevo_estado)
            bot.send_message(call.message.chat.id, f"🔀 DETENER_EN_POSITIVO cambiado a {nuevo_estado.upper()} en config.env")
        elif call.data == "toggle_retomar":
            config = leer_config()
            estado_actual = config.get("RETOMAR_ESTADO", "false").lower()
            nuevo_estado = "false" if estado_actual == "true" else "true"
            actualizar_config("RETOMAR_ESTADO", nuevo_estado)
            bot.send_message(call.message.chat.id, f"🔄 RETOMAR_ESTADO cambiado a {nuevo_estado.upper()} en config.env")
    else:
        bot.answer_callback_query(call.id, "❌ No autorizado")


@bot.message_handler(func=lambda message: True)
def recibir_valor(message):
    global esperando_coef
    if esperando_coef and message.chat.id == CHAT_ID:
        try:
            coef = float(message.text)
            actualizar_config("COEFICIENTE_ESCALA", str(coef))
            bot.reply_to(message, f"✅ COEFICIENTE_ESCALA configurado en {coef} y guardado en config.env")
            print(f"Nuevo COEFICIENTE_ESCALA: {coef}")
        except ValueError:
            bot.reply_to(message, "⚠️ Valor inválido, debe ser numérico.")
        esperando_coef = False


print("Bot de control con menú y configuración iniciado...")
bot.polling()