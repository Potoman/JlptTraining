import csv
from colorama import init, Fore, Style

init(autoreset=True)

# Définition de la classe pour représenter un mot
class Word:
    def __init__(self, kanji, kana, romaji, meaning, jlpt_level):
        self.kanji = kanji
        self.kana = kana
        self.romaji = romaji
        self.meaning = meaning
        self.jlpt_level = jlpt_level

    def __repr__(self):
        return f"Word({self.kanji}, {self.kana}, {self.romaji}, {self.meaning}, {self.jlpt_level})"

# Liste pour stocker tous les mots
words = []

# Lecture du fichier CSV
with open('all_hiragana.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Ignore la première ligne (en-tête)
    for row in reader:
        # row = [kanji, kana, romaji, meaning, jlpt_level]
        if len(row) != 5:
            continue  # ignore les lignes mal formées
        word = Word(*row)
        words.append(word)

count_word = len(words)
import random, re

word_id = random.randint(0, count_word - 1)

def check_solution(response: str, word: Word) -> bool:
    if not response:
        return False
    for meaning in word.meaning.split(";"):
        clean_text = re.sub(r'\s*\(.*?\)\s*', '', meaning)
        if clean_text == response:
            return True
    return False

# Vérification
for w in words[:]:  # affiche les 5 premiers
    if w.jlpt_level == "JLPT_5":
        print(w.kanji + "\t" + w.kana + " : ?")
        response = input()
        if check_solution(response, w):
            print(Fore.GREEN + "Good ! " + Fore.BLACK + w.meaning)
        else:
            print(Fore.RED + "Nop ! " + Fore.BLACK + w.meaning)
    print("")

