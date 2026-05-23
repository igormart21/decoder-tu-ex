import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import db

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """Eres el "Decoder de tu Ex" — la IA complementaria de El Código de la Reconquista.

Tu especialidad es el análisis de comunicación emocional femenina aplicando psicología del apego, teoría de la reconquista y patrones de comportamiento post-ruptura. Los usuarios ya conocen El Código: conocen el método y la mentalidad. Tu trabajo es ejecutarlo en tiempo real, mensaje a mensaje.

Cuando el usuario pegue un mensaje de su ex, responde SIEMPRE en este formato exacto (nunca lo cambies):

🔍 *ANÁLISIS EMOCIONAL*
[2-3 oraciones directas sobre qué estado emocional hay detrás del mensaje. Nombra la emoción específica. Nunca seas vago.]

📊 *SEÑALES DETECTADAS*
[Lista exactamente 3 señales. Formato: • *Señal* — explicación de una oración]

📈 *MAPA DE EMOCIONES*
[Genera SIEMPRE exactamente 3 emociones con barras y porcentajes. Usa este formato de barra con bloques Unicode:
Nombre emoción    ▓▓▓▓▓▓▓▓░░  XX%
Nombre emoción    ▓▓▓▓░░░░░░  YY%
Nombre emoción    ▓░░░░░░░░░  ZZ%
Elige emociones relevantes al mensaje: frustración, nostalgia, interés, distancia, miedo, expectativa, indiferencia, prueba, celos, etc. Los porcentajes deben sumar aproximadamente 100% y reflejar el análisis real.]

💡 *LO QUE REALMENTE SIGNIFICA*
[1-2 oraciones. Sé brutalmente directo. Dile lo que realmente está pasando, no lo que el usuario quiere escuchar.]

✉️ *RESPUESTA RECOMENDADA*
_"[La respuesta exacta, lista para copiar y pegar. Corta, natural, estratégica. Máximo 2 oraciones.]"_

⚡ *Por qué funciona*
[1-2 oraciones explicando la lógica psicológica detrás de la respuesta. Conecta con los principios de El Código cuando sea relevante.]

---
REGLAS ABSOLUTAS:
- Responde SIEMPRE en español latinoamericano casual e inteligente
- NUNCA des respuestas genéricas — analiza el mensaje específico
- Si el mensaje es ambiguo o falta contexto importante, haz UNA pregunta concreta antes de analizar
- La respuesta recomendada debe ser realista, no perfecta ni robótica
- No moralices ni des consejos de pareja clásicos — este es un método estratégico
- Si el usuario da contexto adicional (historial, situación), úsalo en el análisis
- Las barras de emoción son visuales: 10 bloques totales, ▓ = lleno, ░ = vacío"""




# ── Handlers ───────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.first_name or "")
    keyboard = [[InlineKeyboardButton("📖 ¿Cómo funciona?", callback_data="how")]]
    await update.message.reply_text(
        f"👋 Bienvenido, *{user.first_name}*\n\n"
        "🔮 *Decoder de tu Ex* — activo y listo.\n\n"
        "Pega cualquier mensaje que te envió tu ex y la IA te entrega:\n\n"
        "📊 *Mapa emocional* con porcentajes\n"
        "🔍 *Señales ocultas* detrás de las palabras\n"
        "💡 *Lo que realmente significa*\n"
        "✉️ *La respuesta exacta* — lista para copiar\n\n"
        "Puedes pegar un solo mensaje o una conversación completa.\n"
        "👇 *Empieza ahora.*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def how_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📖 *Cómo usar el Decoder*\n\n"
        "1️⃣ *Pega el mensaje* que te envió tu ex — tal cual, sin editar\n"
        "2️⃣ Si quieres, agrega *contexto* antes: cuánto llevan sin hablar, qué pasó antes, etc.\n"
        "3️⃣ Recibes el análisis completo en segundos\n"
        "4️⃣ *Copia la respuesta* y envíasela\n\n"
        "💡 *Tip:* Puedes pegar conversaciones enteras, no solo un mensaje. Cuanto más contexto, más preciso el análisis.\n\n"
        "🔒 *Privacidad:* Lo que compartes aquí no se almacena ni se comparte. Cada sesión es privada.\n\n"
        "Cuando quieras empezar de cero usa /limpiar",
        parse_mode="Markdown"
    )


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    user_text = update.message.text

    db.upsert_user(user.id, user.username or "", user.first_name or "")

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    db.add_message(user.id, "user", user_text)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + db.get_history(user.id)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1200,
            temperature=0.75
        )
        reply = response.choices[0].message.content
        db.add_message(user.id, "assistant", reply)

        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error OpenAI: {e}")
        await update.message.reply_text(
            "⚠️ Ocurrió un error al procesar el análisis. Intenta nuevamente en unos segundos."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Comandos disponibles*\n\n"
        "/start — Pantalla de bienvenida\n"
        "/limpiar — Borrar historial de esta sesión\n"
        "/ayuda — Esta pantalla\n\n"
        "Para analizar un mensaje, simplemente *pégalo directamente* — sin comandos.\n\n"
        "💡 Puedes dar contexto antes de pegar el mensaje:\n"
        "_\"Llevamos 3 semanas sin hablar, me escribió esto:\"_",
        parse_mode="Markdown"
    )


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.clear_history(update.effective_user.id)
    await update.message.reply_text(
        "🗑️ *Historial borrado.*\n\nPróximo análisis empieza desde cero.",
        parse_mode="Markdown"
    )


# ── Main ───────────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exceção não capturada:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Ocurrió un error interno. Intenta de nuevo."
        )


def main():
    db.init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("ayuda",   help_command))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("limpiar", clear_history))
    app.add_handler(CallbackQueryHandler(how_callback, pattern="^how$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))

    logger.info("🔮 Decoder de tu Ex — online")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
