import logging
import requests

from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CommandHandler,
)
from telegram import Update

from hangman import Hangman
from hangmanpics import HANGMAN_PICS

# Create a custom formatter for INFO logs
info_logger = logging.getLogger("info_logger")
info_handler = logging.StreamHandler()
info_handler.setFormatter(logging.Formatter("[%(levelname)s] [%(asctime)s] %(message)s"))
info_logger.addHandler(info_handler)
info_logger.setLevel(logging.INFO)  # Set the log level for the custom logger

# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)


def log(chat_id, message, level=logging.INFO):
    log_format = f"[{chat_id}] {message}"
    info_logger.log(level, log_format)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global games
    games = [game for game in games if game.chat_id != update.effective_chat.id]
    game = Hangman(update.effective_chat.id)
    games.append(game)
    log(game.chat_id, "Game started")
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=game.print_board())
    
    return INGAME


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = next(filter(lambda x: x.chat_id == update.effective_chat.id, games), None)
    
    if game is None:
        log(update.effective_chat.id, "No game in progress for this chat", logging.WARNING)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="There is no game in progress. Use command /start to start a new game.",
        )
        return ConversationHandler.END
    
    await context.bot.send_message(chat_id=game.chat_id, text=game.print_board())
    
    return INGAME


async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    game = next(filter(lambda x: x.chat_id == update.effective_chat.id, games), None)
    guess = update.message.text.strip().lower()
    
    # why is the commandhandler not picking this stuff up?
    if guess.startswith("/"):
        await context.bot.send_message(chat_id=game.chat_id, text="This command can't be used right now")
        return INGAME
    
    log(update.effective_chat.id, f"Guess received: '{guess}'")
    
    if game is None:
        log(update.effective_chat.id, "No game in progress", logging.WARNING)
        return INGAME
    
    if guess in game.characters_tried or guess in game.words_tried:
        log(game.chat_id, f"Guess already been made: '{guess}'")
        await context.bot.send_message(chat_id=game.chat_id, text="This guess has already been made!")
        return INGAME
    
    if guess in game.word:
        log(game.chat_id, f"Correct guess '{guess}'")
        game_over = game.correct_guess(guess)
        if game_over:
            log(game.chat_id, "Game over (win)")
            await context.bot.send_message(chat_id=game.chat_id, text=game.print_board(show_word=True))
            await context.bot.send_message(chat_id=game.chat_id,
                                           text="You win!\n\nSee the /meaning of the word\n\nStart a new game with /start command")
            return ENDGAME
        else:
            await context.bot.send_message(chat_id=game.chat_id, text=game.print_board())
    elif guess == "".join(game.word):
        log(game.chat_id, f"Correct guess of entire word")
        await context.bot.send_message(chat_id=game.chat_id, text=game.print_board(show_word=True))
        await context.bot.send_message(chat_id=game.chat_id, text="You win!\n\nSee the /meaning of the word\n\nStart a new game with /start command")
        return ENDGAME
    else:
        log(game.chat_id, f"Incorrect guess '{guess}'")
        game_over = game.failed_guess(guess)
        
        await context.bot.send_message(chat_id=game.chat_id, text=game.print_board(show_word=game_over))
        
        if game_over:
            log(game.chat_id, "Game over (loss)")
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You lose!\n\nSee the /meaning\n\nUse the /start command to start a new game")
            return ENDGAME
    
    log(game.chat_id, "End of guess")
    return INGAME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    log(update.effective_chat.id, "Cancel requested")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelling...")
    return ConversationHandler.END


async def meaning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    guess = update.message.text.strip().lower()
    game = next(
        filter(lambda x: x.chat_id == update.effective_chat.id, games), None
    )
    log(update.effective_chat.id, f"Meaning of {game.word} requested")
    response = requests.get("https://api.dictionaryapi.dev/api/v2/entries/en/" + ''.join(game.word))
    log(update.effective_chat.id, response.json())
    meaning_text = response.json()[0]["meanings"][0]["definitions"][0]["definition"]
    await context.bot.send_message(chat_id=game.chat_id, text=meaning_text)


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message.text.strip().lower().removeprefix("/message").strip() #is the last strip() needed?
    
    if len(msg) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Message content is empty. Example message: ```/message Hello creator, I saw a bug...```")
        return
    
    log(update.effective_chat.id, f"Received message: {msg}")
    
    f = open("messages.txt", "a")
    f.write(f"update.effective_chat.id: {update.effective_chat.id}\nTime: {update.message.date}\nMessage: {msg}\n\n")
    f.close()
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Message recorded. Thank you!")
    await context.bot.send_message(chat_id=6191059960, text=f"{update.effective_user.full_name} sent a message:\n\n{msg}")


TOKEN = "6582149586:AAG8LDg2ivH9CtdA58CUXD5-KXQvTouRX4g"
games = []
INGAME, ENDGAME = range(2)
MY_CHAT_ID = 6191059960


if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={INGAME: [CommandHandler("status", status), MessageHandler(filters.TEXT, guess)],
                ENDGAME: [CommandHandler("meaning", meaning), CommandHandler("start", start)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("message", message))
    application.add_handler(conv_handler)

    application.run_polling()
