import csv
from colorama import init, Back, Fore
from difflib import SequenceMatcher
from pathlib import Path
import argparse
import random, re
import json

init(autoreset=True)


def get_back_color(field: str):
    if field == 'meaning':
        return Back.LIGHTCYAN_EX
    if field == 'meanings':
        return Back.LIGHTCYAN_EX
    elif field == 'romaji':
        return Back.LIGHTYELLOW_EX
    else:
        return Back.RESET


class Kanji:
    def __init__(self, index: int, kanji: str, element):
        self.index = index
        self.kanji = kanji
        self.strokes = int(element["strokes"])
        self.grade = None if element["grade"] is None else int(element["grade"])
        self.freq = None if element["freq"] is None else int(element["freq"])
        self.jlpt_old = None if element["jlpt_old"] is None else int(element["jlpt_old"])
        self.jlpt_new = None if element["jlpt_new"] is None else int(element["jlpt_new"])
        self.meanings = ";".join(element["meanings"])
        self.radicals = None if element["wk_radicals"] is None else ";".join(element["wk_radicals"])
        self.burn_meanings = False

    @staticmethod
    def fields() -> list[tuple[str, list[str]]]:
        return [('meanings', ['kanji'], [])]

    def help(self):
        print(f"\t{self.radicals}")

    def is_help(self):
        return self.meanings


class Word:
    def __init__(self, index: int, word, kana, romaji, meaning, jlpt_level):
        self.index = index
        self.word = word
        self.kana = kana
        self.romaji = romaji
        self.meaning = meaning
        self.jlpt_level = jlpt_level
        self.overlay_meaning = ""
        self.forbid_meaning = ""
        self.burn_meaning = False
        self.burn_romaji = False

    @staticmethod
    def fields() -> list[tuple[str, list[str]]]:
        return [('meaning', ['word', 'kana'], []),
                ('romaji', ['word'], ['meaning'])]

    def help(self):
        for kanji in list_kanji(self.word):
            print(f"\t{kanji.kanji} : {kanji.meanings}")

    def is_help(self) -> bool:
        for letter in self.word:
            if letter in kanjis:
                if len(self.word) > 1:
                    return True
                else:
                    return False
        return False

    def __str__(self):
        return self.word


class Question:
    def __init__(self, item: Kanji | Word):
        self.item = item
        self.field = None
        self._burn = {}
        self.overlay_meaning = {}
        self.forbid_meaning = {}
        if isinstance(item, Word):
            self._burn['meaning__word_kana'] = item.burn_meaning
            self._burn['romaji__word'] = item.burn_romaji
            self.overlay_meaning['meaning__word_kana'] = item.overlay_meaning
            self.overlay_meaning['romaji__word'] = ""
            self.forbid_meaning['meaning__word_kana'] = item.forbid_meaning
            self.forbid_meaning['romaji__word'] = ""
        if isinstance(item, Kanji):
            self._burn['meanings__kanji'] = item.burn_meanings
            self.overlay_meaning['meanings__kanji'] = ""
            self.forbid_meaning['meanings__kanji'] = ""
        for field in item.fields():
            field_name = field[0]
            if self._burn[field_name + "__" + "_".join(field[1])]:
                continue
            if self.is_questionnable(item, field_name):
                self.field = field
                return
        raise Exception("No field unburn for item : " + str(self.item))

    def is_questionnable(self, item: Kanji | Word, field: str) -> bool:
        if isinstance(item, Word):
            if field == 'meaning':
                if self._burn['meaning__word_kana']:
                    if len(list_kanji(item.word)) == 0:
                        # No Kanji in this word. No reason to ask romaji.
                        return False
            if is_katakana_present(item.word):
                # No ask romaji for katakana word.
                return False
            if field == 'romaji' and not is_kanji_present(item.word):
                # No ask romaji for kana word.
                return False
            return True
        else:
            if field == 'meanings':
                if self._burn['meanings__kanji']:
                    return False
            return True

    def ask(self, prefix: str):
        print(f"{prefix} {', '.join([getattr(self.item, field) for field in self.field[1]])} : {get_back_color(self.field[0])}{self.field[0]}{Back.RESET} ?")

    def burn(self):
        index = self.item.index
        _add_entry_file(index, "o", "burn_" + self.field[0] + ".txt")
        print(f"The word '{getattr(self.item, self.field[0])}' has been burned.")
        self._burn[self.field[0] + '__' + '_'.join(self.field[1])] = True

    def unburn(self):
        index = self.item.index
        _add_entry_file(index, "", "burn_" + self.field[0] + ".txt")
        print(f"The word '{getattr(self.item, self.field[0])}' has been unburned.")
        self._burn[self.field[0] + '__' + '_'.join(self.field[1])] = False

    def help(self):
        self.item.help()

    def is_help(self) -> bool:
        return self.item.is_help()

    def add_forbid(self, forbid: str):
        index = self.item.index
        _add_entry_file(index, forbid, "overlay_forbid_" + self.field[0] + ".txt")
        print(f"Add forbidden meaning '{forbid}' to the word '{words[index].word},{words[index].kana}'")

    def add_meaning(self, meaning: str):
        index = self.item.index
        _add_entry_file(index, meaning, "overlay_response_" + self.field[0] + ".txt")
        print(f"Add new meaning '{meaning}' to the word '{words[index].word},{words[index].kana}'")

    def success(self, ratio: float):
        response = getattr(self.item, self.field[0])
        if self.overlay_meaning[self.field[0] + '__' + '_'.join(self.field[1])] != "":
            response = '; '.join((response + ";" + self.overlay_meaning[self.field[0] + '__' + '_'.join(self.field[1])]).split(";"))
        print(Fore.GREEN + "Good (" + str(ratio) + ") : " + Fore.BLACK + response)

    def error(self, ratio: float):
        response = '; '.join((getattr(self.item, self.field[0]) + ";" + self.overlay_meaning[self.field[0] + '__' + '_'.join(self.field[1])]).split(";"))
        forbid = '; '.join(self.forbid_meaning[self.field[0] + '__' + '_'.join(self.field[1])].split(";"))
        forbid = " (forbid = " + Fore.RED + forbid + Fore.BLACK + ")" if forbid != "" else ""
        other_field = []
        for field in self.field[2]:
            other_field.append(getattr(self.item, field))
        print(Fore.RED + "Nop (" + str(ratio) + ") : " + Fore.BLACK + response + forbid + "; " + Fore.BLACK + ", ".join(other_field))

    def save_result(self, flag: bool, ) -> None:
        if not flag:
            return

        path = Path("word_result_meaning.txt")
        lines = []

        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]

        while len(lines) <= self.item.index:
            lines.append("0")

        try:
            value = int(lines[self.item.index])
        except ValueError:
            value = 0
        lines[self.item.index] = str(value + 1)

        with path.open("w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    def check_solution(self, response: str) -> (bool, float | None):
        if not response:
            return False, None
        solutions = re.sub(r'\s*\(.*?\)\s*', '', getattr(self.item, self.field[0])).split(";")
        solutions = solutions + self.overlay_meaning[self.field[0] + '__' + '_'.join(self.field[1])].split(";")
        forbids = self.forbid_meaning[self.field[0] + '__' + '_'.join(self.field[1])].split(";")
        return check_field(response, solutions, forbids)


class Session:
    def __init__(self, jlpt: int, test: str):
        self.last_question = None
        self.questions_word = []
        self.questions_kanji = []
        if test in ["w", "b"]:
            for word in words[:]:
                if word.jlpt_level == f"JLPT_{jlpt}":
                    try:
                        self.questions_word.append(Question(word))
                    except:
                        pass # This item is burned.
        if test in ["k", "b"]:
            for kanji in kanjis.values():
                if kanji.jlpt_new == jlpt:
                    try:
                        self.questions_kanji.append(Question(kanji))
                    except:
                        pass # This item is burned.
        random.shuffle(self.questions_word)
        random.shuffle(self.questions_kanji)
        self.questions_word_length_initial = len(self.questions_word)
        self.questions_kanji_length_initial = len(self.questions_kanji)
        self.questions_length_initial = self.questions_word_length_initial + self.questions_kanji_length_initial

    def ask(self):
        count = 1
        while self.questions_word or self.questions_kanji:
            index = random.randint(0, len(self.questions_word) + len(self.questions_kanji) - 1)
            question = None
            if index < len(self.questions_word):
                question = self.questions_word.pop()
            else:
                question = self.questions_kanji.pop()
            self.ask_question(count, question)
            count = count + 1

    def ask_question(self, index: int, question: Question):
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', type=str, nargs="+", help="Forbid a description of sentence from a solution.")
        parser.add_argument('-a', type=str, nargs="+", help="Add a description of sentence for a solution.")
        parser.add_argument('-b', action='store_true', help="Burn the last question.")
        parser.add_argument('-u', action='store_true', help="Unburn the last question.")
        flag = False
        help = False
        while True:
            if not help:
                question.ask(f"[{str(index)}/{self.questions_length_initial} (k:{str(len(self.questions_kanji))}/{str(self.questions_kanji_length_initial)}, w:{str(len(self.questions_word))}/{str(self.questions_word_length_initial)})]")
            if help:
                question.help()
            flag = False
            response = input()
            args, unknown = parser.parse_known_args(response.split())
            if args.f is not None:
                flag = True
                if self.last_question is None:
                    print("No previous word")
                else:
                    self.last_question.add_forbid(' '.join(args.f))
            elif args.a is not None:
                flag = True
                if self.last_question is None:
                    print("No previous word")
                else:
                    self.last_question.add_meaning(' '.join(args.a))
            elif args.b:
                flag = True
                self.last_question.burn()
            elif args.u:
                flag = True
                self.last_question.unburn()
            elif response == "":
                # Print help
                if help:
                    break
                else:
                    if question.is_help():
                        help = True
                    else:
                        break
            else:
                break
        is_ok, ratio = question.check_solution(response)
        if is_ok:
            question.save_result(is_ok)
            question.success(ratio)
        else:
            question.error(ratio)
            if not help:
                question.help()
        print("")
        self.last_question = question


def load_kanji() -> dict[str, Kanji]:
    kanjis = {}
    file_path = Path("kanji.json")
    with open(file_path, "r", encoding="utf-8") as f:
        index = 0
        for kanji, info in json.load(f).items():
            kanjis[kanji] = Kanji(index, kanji, info)
            index = index + 1
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
    path = Path("overlay_forbid_meaning.txt")
    index = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            words[index].forbid_meaning = line
            index = index + 1
except:
    print("Err")

try:
    path = Path("overlay_response_meaning.txt")
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


try:
    path = Path("burn_meanings.txt")
    lines = []

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

    for index in range(len(lines)):
        kanjis[list(kanjis.keys())[index]].burn_meanings = lines[index] == 'o'
except:
    print("Err")


def check_field(response: str, solutions: list[str], forbids: list[str]) -> (bool, float | None):
    ratio_resonse = 0.0
    ratio_forbid_resonse = 0.0
    for solution in solutions:
        tmp_ratio_resonse = SequenceMatcher(None, solution, response).ratio()
        ratio_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_resonse else ratio_resonse
    for forbid in forbids:
        tmp_ratio_resonse = SequenceMatcher(None, forbid, response).ratio()
        ratio_forbid_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_forbid_resonse else ratio_forbid_resonse
    return (False if ratio_forbid_resonse > 0.85 else ratio_resonse > 0.6,
            0.0 if ratio_forbid_resonse > 0.85 else ratio_resonse)


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


def is_kanji_present(text: str) -> bool:
    return len(list_kanji(text)) != 0


def main():
    r = input("What test : Kanji, Word, Both ?")
    session = Session(5, r)
    session.ask()


if __name__ == '__main__':
    main()
