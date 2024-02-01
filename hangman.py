import random
from hangmanpics import HANGMAN_PICS

with open("words.txt") as words_file:
    words = words_file.read().splitlines()

class Hangman:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.word = list(random.choice(words))
        self.failed_attempts = 0
        self.characters_tried = []
        self.words_tried = []

    def failed_guess(self, g):
        self.failed_attempts += 1
        (self.characters_tried if len(g) == 1 else self.words_tried).append(g)
        return self.failed_attempts >= 6 # len(handman_pics)-1

    def correct_guess(self, g):
        self.characters_tried.append(g)

        return set(self.word).issubset(set(self.characters_tried))

    def print_board(self, show_word=False):
        message = ""
        message += HANGMAN_PICS[self.failed_attempts]
        message += "\n\n"
        message += "".join(letter if letter in self.characters_tried else " _ " for letter in self.word) if not show_word else "".join(self.word)
        message += "\n\n"
        message += " ".join(sorted([char for char in self.characters_tried if char not in self.word]))
        message += "\n\n"
        message += " ".join(sorted(self.words_tried))
        
        return message