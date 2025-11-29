import csv
from colorama import init, Fore
from difflib import SequenceMatcher
from pathlib import Path
import argparse
import random, re
import json

init(autoreset=True)


class Kanji:
    def __init__(self, kanji: str, element):
        self.kanji = kanji
        self.strokes = int(element["strokes"])
        self.grade = None if element["grade"] is None else int(element["grade"])
        self.freq = None if element["freq"] is None else int(element["freq"])
        self.jlpt_old = None if element["jlpt_old"] is None else int(element["jlpt_old"])
        self.jlpt_new = None if element["jlpt_new"] is None else int(element["jlpt_new"])
        self.meanings = element["meanings"]
        self.radicals = element["wk_radicals"]


class Word:
    def __init__(self, index: int, word, kana, romaji, meaning, jlpt_level):
        self.index = index
        self.word = word
        self.kana = kana
        self.romaji = romaji
        self.meaning = meaning
        self.jlpt_level = jlpt_level
        self.forbid = ""
        self.overlay_meaning = ""
        self.burn_meaning = False
        self.burn_romaji = False

    def burn_word_meaning(self):
        _add_entry_file(self.index, "o", "burn_meaning.txt")
        print(f"The word '{self.word},{self.kana}' has been burned.")
        self.burn_meaning = True

    def burn_word_romaji(self):
        _add_entry_file(self.index, "o", "burn_romaji.txt")
        print(f"The word '{self.word},{self.kana}' has been burned.")
        self.burn_romaji = True

    def unburn_word_meaning(self):
        _add_entry_file(self.index, "", "burn_meaning.txt")
        print(f"The word '{self.word},{self.kana}' has been unburned.")
        self.burn_meaning = False

    def unburn_word_romaji(self):
        _add_entry_file(self.index, "", "burn_romaji.txt")
        print(f"The word '{self.word},{self.kana}' has been unburned.")
        self.burn_romaji = False


class Session:
    def __init__(self, words: list[Word]):
        self.last_word = None
        self.words = words


def load_kanji() -> dict[str, Kanji]:
    kanjis = {}
    file_path = Path("kanji.json")
    with open(file_path, "r", encoding="utf-8") as f:
        for kanji, info in json.load(f).items():
            kanjis[kanji] = Kanji(kanji, info)
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
    path = Path("overlay_meaning.txt")
    index = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            words[index].overlay_meaning = line
            index = index + 1
except:
    print("Err")


try:
    path = Path("burn_meaning.txt")
    lines = []

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

    for index in range(len(lines)):
        words[index].burn_meaning = lines[index] == 'o'
except:
    print("Err")


try:
    path = Path("burn_romaji.txt")
    lines = []

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

    for index in range(len(lines)):
        words[index].burn_romaji = lines[index] == 'o'
except:
    print("Err")


count_word = len(words)

word_id = random.randint(0, count_word - 1)


def check_solution(response: str, word: Word) -> (bool, float | None):
    if not response:
        return False, None
    ratio_resonse = 0.0
    ratio_forbid_resonse = 0.0
    if word.burn_meaning:
        ratio_resonse = SequenceMatcher(None, word.romaji, response).ratio()
    else:
        meanings = re.sub(r'\s*\(.*?\)\s*', '', word.meaning)
        for meaning in meanings.split(";"):
            tmp_ratio_resonse = SequenceMatcher(None, meaning, response).ratio()
            ratio_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_resonse else ratio_resonse
        # Here the overlay :
        for overlay_meaning in word.overlay_meaning.split(";"):
            tmp_ratio_resonse = SequenceMatcher(None, overlay_meaning, response).ratio()
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
    for word in words[:]:
        if word.jlpt_level == f"JLPT_{jlpt}":
            if word.burn_meaning:
                if len(list_kanji(word.word)) == 0:
                    # No Kanji in this word. No reason to ask romaji.
                    continue
                if is_katakana_present(word.word):
                    # No ask romaji for katakana word.
                    continue
            if not word.burn_meaning or not word.burn_romaji:
                session_words.append(word)
    random.shuffle(session_words)
    return session_words


def list_burn(jlpt: int):
    session_words = []
    for w in words[:]:
        if w.jlpt_level == f"JLPT_{jlpt}":
            if w.burn_meaning:
                session_words.append(w)
    random.shuffle(session_words)
    return session_words


def _add_entry_file(index: int, text: str, file: str):
    path = Path(file)
    lines = []

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

    while len(lines) <= index:
        lines.append("")

    if lines[index] != "":
        lines[index] = lines[index] + ";"
    lines[index] = text

    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def overlay_add_forbid(index: int, meaning: str):
    _add_entry_file(index, meaning, "overlay_forbid.txt")
    print(f"Add forbidden meaning '{meaning}' to the word '{words[index].kanji},{words[index].kana}'")


def overlay_add_meaning(index: int, meaning: str):
    _add_entry_file(index, meaning, "overlay_meaning.txt")
    print(f"Add new meaning '{meaning}' to the word '{words[index].kanji},{words[index].kana}'")


def list_kanji(text: str) -> list[Kanji]:
    tmp_kanjis = []
    for letter in text:
        if letter in kanjis:
            tmp_kanjis.append(kanjis[letter])
    return tmp_kanjis


def is_katakana_present(text: str):
    katakana = "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶー・ヽヾ"
    for character in text:
        if character in katakana:
            return True
    return False


def show_help(word_kanji: str):
    for kanji in list_kanji(word_kanji):
        meanings = ", ".join(kanji.meanings)
        print(f"\t{kanji.kanji} : {meanings}")


def is_help(word_kanji: str):
    for letter in word_kanji:
        if letter in kanjis:
            if len(word_kanji) > 1:
                return True
            else:
                return False
    return False


def ask_word(session: Session, item: int, word: Word):
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', type=str, nargs="+", help="Forbid a word of sentence from a solution.")
    parser.add_argument('-a', type=str, nargs="+", help="Add a word of sentence for a solution.")
    parser.add_argument('-b', action='store_true', help="Burn the last question (It will never been ask anymore).")
    parser.add_argument('-u', action='store_true', help="Unburn the last question.")
    flag = False
    help = False
    while True:
        if not help:
            if word.burn_meaning:
                print(f"[{item}/{len(session.words)}] {word.word} : romaji ?")
            else:
                print(f"[{item}/{len(session.words)}] {word.word} \t {word.kana} : meaning ?")
        if help:
            show_help(word.word)
        flag = False
        response = input()
        args, unknown = parser.parse_known_args(response.split())
        if args.f is not None:
            flag = True
            if session.last_word is None:
                print("No previous word")
            else:
                overlay_add_forbid(session.last_word.index, ' '.join(args.f))
        elif args.a is not None:
            flag = True
            if session.last_word is None:
                print("No previous word")
            else:
                overlay_add_meaning(session.last_word.index, ' '.join(args.a))
        elif args.b:
            flag = True
            if session.last_word.burn_meaning:
                session.last_word.burn_word_romaji()
            else:
                session.last_word.burn_word_meaning()
        elif args.u:
            flag = True
            if session.last_word.burn_meaning:
                session.last_word.unburn_word_meaning()
            else:
                session.last_word.unburn_word_romaji()
        elif response == "":
            # Print help
            if help:
                break
            else:
                if is_help(word.word):
                    help = True
                else:
                    break
        else:
            break
    is_ok, ratio = check_solution(response, word)
    meaning = word.meaning
    if word.overlay_meaning != "":
        meaning = meaning + ";" + word.overlay_meaning
    if is_ok:
        save_result(word.index, is_ok)
        if word.burn_meaning:
            print(Fore.GREEN + "Good (" + str(ratio) + ") : " + Fore.BLACK + word.romaji)
        else:
            print(Fore.GREEN + "Good (" + str(ratio) + ") : " + Fore.BLACK + meaning)
    else:
        if word.burn_meaning:
            print(Fore.RED + "Nop (" + str(ratio) + ") : " + Fore.BLACK + word.romaji + " (" + word.meaning + ")")
        else:
            forbid_test = " (forbid = " + Fore.RED + word.forbid + Fore.BLACK + ")" if word.forbid != "" else ""
            print(Fore.RED + "Nop (" + str(ratio) + ") : " + Fore.BLACK + meaning + forbid_test)
        show_help(word.word)
    print("")
    session.last_word = word


def main():
    item = 0
    words = prepare_test(5)

    session = Session(words)

    for word in words:
        item = item + 1
        ask_word(session, item, word)


if __name__ == '__main__':
    main()
