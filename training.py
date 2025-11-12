import csv
from colorama import init, Fore
from difflib import SequenceMatcher
from pathlib import Path

init(autoreset=True)


class Word:
    def __init__(self, index: int, kanji, kana, romaji, meaning, jlpt_level):
        self.index = index
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
    index = 0
    for row in reader:
        # row = [kanji, kana, romaji, meaning, jlpt_level]
        index = index + 1
        if len(row) != 5:
            continue  # ignore les lignes mal formées
        word = Word(index - 1, *row)
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


def save_result(index: int, flag: bool, ) -> None:
    if not flag:
        return

    path = Path("result.txt")
    lines = []

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

    while len(lines) <= index:
        lines.append("0")

    try:
        value = int(lines[index])
    except ValueError:
        value = 0
    lines[index] = str(value + 1)

    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def prepare_test(jlpt: int):
    session_words = []
    for w in words[:]:
        if w.jlpt_level == f"JLPT_{jlpt}":
            session_words.append(w)
    random.shuffle(session_words)
    return session_words


def main():
    item = 0
    session_words = prepare_test(5)
    for w in session_words:
        item = item + 1
        print(f"[{item}/{len(session_words)}] {w.kanji} \t {w.kana} : ?")
        response = input()
        is_ok, ratio = check_solution(response, w)
        if is_ok:
            save_result(w.index, is_ok)
            print(Fore.GREEN + "Good (" + str(ratio) + ") : " + Fore.BLACK + w.meaning)
        else:
            print(Fore.RED + "Nop (" + str(ratio) + ") : " + Fore.BLACK + w.meaning)
        print("")


if __name__ == '__main__':
    main()
