import csv
from colorama import init, Fore
from difflib import SequenceMatcher

init(autoreset=True)


class Word:
    def __init__(self, kanji, kana, romaji, meaning, jlpt_level):
        self.kanji = kanji
        self.kana = kana
        self.romaji = romaji
        self.meaning = meaning
        self.jlpt_level = jlpt_level

    def __repr__(self):
        return f"Word({self.kanji}, {self.kana}, {self.romaji}, {self.meaning}, {self.jlpt_level})"


words = []


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


def check_solution(response: str, word: Word) -> (bool, float | None):
    if not response:
        return False, None
    ratio_resonse = 0.0
    for meaning in word.meaning.split(";"):
        clean_text = re.sub(r'\s*\(.*?\)\s*', '', meaning)
        tmp_ratio_resonse = SequenceMatcher(None, clean_text, response).ratio()
        ratio_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_resonse else ratio_resonse
    return ratio_resonse > 0.6, ratio_resonse


def main():
    for w in words[:]:
        if w.jlpt_level == "JLPT_5":
            print(w.kanji + "\t" + w.kana + " : ?")
            response = input()
            is_ok, ratio = check_solution(response, w)
            if is_ok:
                print(Fore.GREEN + "Good (" + str(ratio) + ") : " + Fore.BLACK + w.meaning)
            else:
                print(Fore.RED + "Nop (" + str(ratio) + ") : " + Fore.BLACK + w.meaning)
        print("")


if __name__ == '__main__':
    main()
