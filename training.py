import csv
from colorama import init, Fore
from difflib import SequenceMatcher
from pathlib import Path
import argparse
import random, re
import json

init(autoreset=True)


class Kanji:
    def __init__(self, element):
        self.strokes = int(element["strokes"])
        self.grade = None if element["grade"] is None else int(element["grade"])
        self.freq = None if element["freq"] is None else int(element["freq"])
        self.jlpt_old = None if element["jlpt_old"] is None else int(element["jlpt_old"])
        self.jlpt_new = None if element["jlpt_new"] is None else int(element["jlpt_new"])
        self.meanings = element["meanings"]
        self.radicals = element["wk_radicals"]


class Word:
    def __init__(self, index: int, kanji, kana, romaji, meaning, jlpt_level):
        self.index = index
        self.kanji = kanji
        self.kana = kana
        self.romaji = romaji
        self.meaning = meaning
        self.jlpt_level = jlpt_level
        self.forbid = ""
        self.description = ""

    def __repr__(self):
        return f"Word({self.kanji}, {self.kana}, {self.romaji}, {self.meaning}, {self.jlpt_level})"


def load_kanji() -> dict[str, Kanji]:
    kanjis = {}
    file_path = Path("kanji.json")
    with open(file_path, "r", encoding="utf-8") as f:
        for kanji, info in json.load(f).items():
            kanjis[kanji] = Kanji(info)
    return kanjis


words = []
kanjis = load_kanji()


with open('all_hiragana.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Ignore la première ligne (en-tête)
    index = 0
    for row in reader:
        # row = [kanji, kana, romaji, meaning, jlpt_level]
        index = index + 1
        if len(row) != 5:
            raise Exception("Malformed line : " + str(row))
        word = Word(index - 1, *row)
        words.append(word)

try:
    path = Path("overlay_forbid.txt")
    index = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            words[index].forbid = line
            index = index + 1
except:
    print("Err")

try:
    path = Path("overlay_description.txt")
    index = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            words[index].description = line
            index = index + 1
except:
    print("Err")

count_word = len(words)

word_id = random.randint(0, count_word - 1)


def check_solution(response: str, word: Word) -> (bool, float | None):
    if not response:
        return False, None
    ratio_resonse = 0.0
    ratio_forbid_resonse = 0.0
    meanings = re.sub(r'\s*\(.*?\)\s*', '', word.meaning)
    for meaning in meanings.split(";"):
        tmp_ratio_resonse = SequenceMatcher(None, meaning, response).ratio()
        ratio_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_resonse else ratio_resonse
    # Here the overlay :
    for description in word.description.split(";"):
        tmp_ratio_resonse = SequenceMatcher(None, description, response).ratio()
        ratio_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_resonse else ratio_resonse
    for forbid in word.forbid.split(";"):
        tmp_ratio_resonse = SequenceMatcher(None, forbid, response).ratio()
        ratio_forbid_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_forbid_resonse else ratio_forbid_resonse
    return (False if ratio_forbid_resonse > 0.85 else ratio_resonse > 0.6,
            0.0 if ratio_forbid_resonse > 0.85 else ratio_resonse)


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
            if not is_word_burn(w):
                session_words.append(w)
    random.shuffle(session_words)
    return session_words


def _add_entry_file(index: int, description: str, file: str):
    path = Path(file)
    lines = []

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

    while len(lines) <= index:
        lines.append("")

    if lines[index] != "":
        lines[index] = lines[index] + ";"
    lines[index] = description

    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def _get_entry_file(index: int, file: str) -> str | None:
    path = Path(file)
    lines = []

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

    while len(lines) <= index:
        return None

    return lines[index]


def is_word_burn(word: Word):
    return _get_entry_file(word.index, "burn.txt") == 'o'


def overlay_add_forbid(index: int, description: str):
    _add_entry_file(index, description, "overlay_forbid.txt")
    print(f"Add forbidden description '{description}' to the word '{words[index].kanji},{words[index].kana}'")


def overlay_add_description(index: int, description: str):
    _add_entry_file(index, description, "overlay_description.txt")
    print(f"Add new description '{description}' to the word '{words[index].kanji},{words[index].kana}'")


def burn_word(index: int):
    _add_entry_file(index, "o", "burn.txt")
    print(f"The word '{words[index].kanji},{words[index].kana}' has been burned.")


def show_help(word_kanji: str):
    for letter in word_kanji:
        if letter in kanjis:
            kanji = kanjis[letter]
            meanings = ", ".join(kanji.meanings)
            print(f"\t{letter} : {meanings}")


def main():
    item = 0
    session_words = prepare_test(5)
    previous_w = None
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', type=str, nargs="+", help="Forbid a word of sentence from a solution.")
    parser.add_argument('-a', type=str, nargs="+", help="Add a word of sentence for a solution.")
    parser.add_argument('-b', action='store_true', help="Burn the last question (It will never been ask anymore).")
    for w in session_words:
        item = item + 1
        while True:
            print(f"[{item}/{len(session_words)}] {w.kanji} \t {w.kana} : ?")
            response = input()
            args, unknown = parser.parse_known_args(response.split())
            if args.f is not None:
                if previous_w is None:
                    print("No previous word")
                else:
                    overlay_add_forbid(previous_w.index, ' '.join(args.f))
            elif args.a is not None:
                if previous_w is None:
                    print("No previous word")
                else:
                    overlay_add_description(previous_w.index, ' '.join(args.a))
            elif args.b:
                burn_word(previous_w.index)
            else:
                break
        is_ok, ratio = check_solution(response, w)
        meaning = w.meaning
        if w.description != "":
            meaning = meaning + ";" + w.description
        if is_ok:
            save_result(w.index, is_ok)
            print(Fore.GREEN + "Good (" + str(ratio) + ") : " + Fore.BLACK + meaning)
        else:
            forbid_test = " (forbid = " + Fore.RED + w.forbid + Fore.BLACK + ")" if w.forbid != "" else ""
            print(Fore.RED + "Nop (" + str(ratio) + ") : " + Fore.BLACK + meaning + forbid_test)
            show_help(w.kanji)
        print("")
        previous_w = w

if __name__ == '__main__':
    main()
