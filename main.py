import logging
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CommandHandler,
)
from telegram import Update
import random
import requests

# To-do list
'''
To-do:
  - clean the printing of the hangman
  - keep track of games played + won (in a txt file?)
  - 1v1 mode?
  - uddate bot commands to be status not print
  - buy me a coffee button
  - ignore commands from guesses
  - /message command to send bugs, features, etc. Concat these msgs to a text file, then send me a private message when a new one appears
  - Sort Hangman object cleanup/re-use
  - Make more use of Hangman class, and maybe seperate file so this main code is cleaner
'''

# Create a custom formatter for INFO logs
info_logger = logging.getLogger("info_logger")
info_handler = logging.StreamHandler()
info_handler.setFormatter(
    logging.Formatter("[%(levelname)s] [%(asctime)s] %(message)s")
)
info_logger.addHandler(info_handler)
info_logger.setLevel(logging.INFO)  # Set the log level for the custom logger

# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)


def log(chat_id, message, level=logging.INFO):
    log_format = f"[{chat_id}] {message}"
    info_logger.log(level, log_format)


TOKEN = "6582149586:AAG8LDg2ivH9CtdA58CUXD5-KXQvTouRX4g"
HANGMAN_PICS = [
'''
   +-------+
   |     |
         |
         |
         |
         |
=========''',
'''
   +-------+
   |     |
   O     |
         |
         |
         |
=========''',
'''
   +-------+
   |     |
   O     |
   |     |
         |
         |
=========''',
'''
   +-------+
   |     |
   O     |
  /|     |
         |
         |
=========''',
'''
   +-------+
   |     |
   O     |
  /|\    |
         |
         |
=========''',
'''
   +-------+
   |     |
   O     |
  /|\    |
  /      |
         |
=========''',
'''
   +-------+
   |     |
   O     |
  /|\    |
  / \    |
         |
=========''',
]

games = []

with open("words.txt") as words_file:
    words = words_file.read().splitlines()

max_attempts = len(HANGMAN_PICS) - 1


class Hangman:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.word = list(random.choice(words))
        self.failed_attempts = 0
        self.characters_tried = []
        self.words_tried = []

    def failed_guess(self, g):
        self.failed_attempts += 1
        if len(g) == 1:
            self.characters_tried.append(g)
        else:
            self.words_tried.append(g)

        if self.failed_attempts >= max_attempts:
            return True
        else:
            return False

    def correct_guess(self, g):
        self.characters_tried.append(g)

        if set(self.word).issubset(set(self.characters_tried)):
            return True

        return False

    def print_board(self, show_word=False):
        if show_word:
            return (
                HANGMAN_PICS[self.failed_attempts]
                + "\n\n"
                + "".join(self.word)
                + "\n\n"
                + " ".join(sorted([char for char in self.characters_tried if char not in self.word]))
                + "\n\n"
                + " ".join(sorted(self.words_tried))
            )
        else:
            return (
                HANGMAN_PICS[self.failed_attempts]
                + "\n\n"
                + "".join(
                    letter if letter in self.characters_tried else " _ "
                    for letter in self.word
                )
                + "\n\n"
                + " ".join(sorted([char for char in self.characters_tried if char not in self.word]))
                + "\n\n"
                + " ".join(sorted(self.words_tried))
            )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global games
    games = [game for game in games if game.chat_id != update.effective_chat.id]
    game = Hangman(update.effective_chat.id)
    games.append(game)
    log(game.chat_id, "Game started")

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=game.print_board()
    )

    return INGAME


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = next(
        filter(lambda x: x.chat_id == update.effective_chat.id, games), None
    )

    if game is None:
        log(update.effective_chat.id, "No game in progress for this chat", logging.WARNING)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="There is no game in progress. Use command /start to start a new game.",
        )
        return ConversationHandler.END

    await context.bot.send_message(chat_id=game.chat_id, text=game.print_board())

    return INGAME


async def make_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    guess = update.message.text.strip().lower()
    
    if guess.startswith("/"):
        return INGAME

    game = next(
        filter(lambda x: x.chat_id == update.effective_chat.id, games), None
    )

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
    log(update.effective_chat.id, f"Received message: {update.message.text.strip().lower()}")

INGAME, ENDGAME = range(2)

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={INGAME: [CommandHandler("status", status), MessageHandler(filters.TEXT, make_guess)],
                ENDGAME: [CommandHandler("meaning", meaning), CommandHandler("start", start)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("message", message))
    application.add_handler(conv_handler)

    application.run_polling()
