import csv
from abc import ABC, abstractmethod
from collections import deque
from colorama import init, Back, Fore, Style
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
import argparse
import random, re
import json

init(autoreset=True)

# Pastel true-color backgrounds used for kanji in failed answers.
KUN_READING_COLOR = "\033[48;2;189;235;255m\033[38;2;0;0;0m"  # pale sky blue
ON_READING_COLOR = "\033[48;2;255;214;231m\033[38;2;0;0;0m"   # pale blush pink


def clean_field(field: str):
    return "; ".join(x.strip() for x in field.split(";"))


def print_radicals(radicals: list[str]):
    print("\t" + Back.LIGHTGREEN_EX + "Radicals" + Back.RESET + " : " + (",").join(radicals))


def get_back_color(field: str):
    if field == 'meaning':
        return Back.LIGHTCYAN_EX
    if field == 'meanings':
        return Back.LIGHTCYAN_EX
    elif field == 'romaji':
        return Back.LIGHTYELLOW_EX
    else:
        return Back.RESET


def wrap_back_color(field: str, text: str):
    return f"{get_back_color(field)} {text} {Back.RESET}"


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
        self.readings_on = element["readings_on"]
        self.readings_kun = element["readings_kun"]
        self.radicals = None if element["wk_radicals"] is None else ";".join(element["wk_radicals"])
        self.burn_meanings = False

    @staticmethod
    def fields() -> list[tuple[str, list[str], list[str]]]:
        return [('meanings', ['kanji'], [])]

    def help(self):
        print_radicals(self.radicals)

    def is_help(self):
        return self.meanings

    def jlpt(self) -> int:
        return self.jlpt_new


class Word:
    def __init__(self, index: int, word, kana, romaji, meaning, jlpt_level, kinds, tags, transitivity):
        self.index = index
        self.word = word
        self.kana = kana
        self.romaji = romaji
        self.meaning = meaning
        self.jlpt_level = int(jlpt_level.replace("JLPT_", ""))
        self.kinds: list[str] = kinds.split(';')
        self.tags: list[str] = tags.split(';')
        self.overlay_meaning = ""
        self.forbid_meaning = ""
        self.burn_meaning = False
        self.burn_romaji = False
        self.transitivity: str | None = None if transitivity == "" else transitivity

    @staticmethod
    def fields() -> list[tuple[str, list[str], list[str]]]:
        # First is what we have to guess;
        # Second is what is shown as help;
        # Third is additional information print on error.
        return [('meaning', ['word'], []),
                ('meaning', ['word', 'kana'], []),
                ('romaji', ['word'], ['meaning']),
                ('romaji', ['meaning'], ['word'])]

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

    def jlpt(self) -> int:
        return self.jlpt_level

    def __str__(self):
        return self.word


class Question:
    def __init__(self, item: Kanji | Word, selected_field: tuple[str, list[str], list[str]] | None):
        self.item = item
        self.field = None
        self._burn = {}
        self.overlay_meaning = {}
        self.forbid_meaning = {}
        if isinstance(item, Word):
            self._burn['meaning__word'] = item.burn_meaning
            self._burn['meaning__word_kana'] = item.burn_meaning
            self._burn['romaji__word'] = item.burn_romaji
            self._burn['romaji__meaning'] = item.burn_romaji
            self.overlay_meaning['meaning__word'] = item.overlay_meaning
            self.overlay_meaning['meaning__word_kana'] = item.overlay_meaning
            self.overlay_meaning['romaji__word'] = ""
            self.overlay_meaning['romaji__meaning'] = ""
            self.forbid_meaning['meaning__word'] = item.forbid_meaning
            self.forbid_meaning['meaning__word_kana'] = item.forbid_meaning
            self.forbid_meaning['romaji__word'] = ""
            self.forbid_meaning['romaji__meaning'] = ""
        if isinstance(item, Kanji):
            self._burn['meanings__kanji'] = item.burn_meanings
            self.overlay_meaning['meanings__kanji'] = ""
            self.forbid_meaning['meanings__kanji'] = ""
        fields = [selected_field] if selected_field is not None else item.fields()
        for field in fields:
            field_name = field[0]
            if self._burn[field_name + "__" + "_".join(field[1])]:
                continue
            if self.is_questionnable(item, field_name):
                self.field = field
                return
        raise Exception("No field unburn for item : " + str(self.item))

    def is_questionnable(self, item: Kanji | Word, field_name: str) -> bool:
        if isinstance(item, Word):
            if field_name == 'meaning':
                if self._burn['meaning__word_kana']:
                    if len(list_kanji(item.word)) == 0:
                        # No Kanji in this word. No reason to ask romaji.
                        return False
            if is_katakana_present(item.word):
                # No ask romaji for katakana word.
                return False
            if field_name == 'romaji' and not is_kanji_present(item.word):
                # No ask romaji for kana word.
                return False
            return True
        else:
            if field_name == 'meanings':
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

    def reset(self):
        for field in self.item.fields():
            _add_entry_file(index, "", "burn_" + field[0] + ".txt")
            self._burn[field[0] + '__' + '_'.join(field[1])] = False
        print(f"The word '{getattr(self.item, field[0])}' has been reset.")

    def help(self):
        self.item.help()

    def is_help(self) -> bool:
        return self.item.is_help()

    def jlpt(self) -> str:
        return self.item.jlpt()

    def add_forbid(self, forbid: str):
        index = self.item.index
        _add_entry_file(index, forbid, "overlay_forbid_" + self.field[0] + ".txt")
        print(f"Add forbidden meaning '{forbid}' to the word '{words[index].word},{words[index].kana}'")

    def add_meaning(self, meaning: str):
        index = self.item.index
        _add_entry_file(index, meaning, "overlay_response_" + self.field[0] + ".txt")
        print(f"Add new meaning '{meaning}' to the word '{words[index].word},{words[index].kana}'")

    def print_word_details(self):
        if not isinstance(self.item, Word):
            return

        overlay_meanings = "; ".join(
            meaning.strip() for meaning in self.item.overlay_meaning.split(";") if meaning.strip()
        )
        forbidden_meanings = "; ".join(
            meaning.strip() for meaning in self.item.forbid_meaning.split(";") if meaning.strip()
        )
        kinds = ", ".join(kind for kind in self.item.kinds if kind) or "not specified"

        print(Fore.RESET + f"\tWord: {color_kanji_readings(self.item)}")
        print(f"\tKana: {self.item.kana}")
        print(f"\tRomaji: {self.item.romaji}")
        print(f"\tMeaning: {clean_field(self.item.meaning)}")
        if overlay_meanings:
            print(f"\tAdditional meanings: {overlay_meanings}")
        if forbidden_meanings:
            print(Fore.RED + f"\tForbidden meanings: {forbidden_meanings}" + Fore.RESET)
        print(f"\tTypes: {kinds}")
        if self.item.transitivity:
            print(f"\tTransitivity: {self.item.transitivity}")
        contained_kanji = list_kanji(self.item.word)
        if contained_kanji:
            print("\tKanji:")
            for kanji in contained_kanji:
                print(f"\t  {kanji.kanji}: {kanji.meanings}")

    def success(self, ratio: float):
        response = getattr(self.item, self.field[0])
        print(Fore.GREEN + "OK (" + str(ratio) + ")" + Fore.RESET + " : " + response)
        self.print_word_details()

    def error(self, ratio: float | None):
        response = getattr(self.item, self.field[0])
        print(Fore.RED + "KO (" + str(ratio) + ")" + Fore.RESET + " : " + response)
        self.print_word_details()

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
        if self.field[0] == "romaji" and isinstance(self.item, Word):
            response = normalize_romaji_response(response, self.item.kinds)
        solutions = re.sub(r'\s*\(.*?\)\s*', '', getattr(self.item, self.field[0])).split(";")
        solutions = solutions + self.overlay_meaning[self.field[0] + '__' + '_'.join(self.field[1])].split(";")
        forbids = self.forbid_meaning[self.field[0] + '__' + '_'.join(self.field[1])].split(";")
        should_be_exact = self.field[0] == "romaji"
        return check_field(response, solutions, forbids, should_be_exact)


class Session(ABC):
    def __init__(self):
        self.last_question = None
        self.questions_word = []
        self.questions_kanji = []
        self._build_questions()
        self._choose_questions_word_block()
        random.shuffle(self.questions_word)
        random.shuffle(self.questions_kanji)
        self.questions_word_length_initial = len(self.questions_word)
        self.questions_kanji_length_initial = len(self.questions_kanji)
        self.questions_length_initial = self.questions_word_length_initial + self.questions_kanji_length_initial
        self._pending_questions_word = 0
        self._pending_questions_kanji = 0
        self.good_answer = 0
        self.bad_answer = 0
        self.score = 0.0
        self.failed_questions = {}

    @abstractmethod
    def _build_questions(self) -> None:
        """Populate self.questions_word and self.questions_kanji."""

    def _choose_questions_word_block(self, block_size: int = 15) -> None:
        if len(self.questions_word) <= block_size:
            return

        block_count = (len(self.questions_word) + block_size - 1) // block_size
        while True:
            choice = input(
                f"{len(self.questions_word)} word questions found "
                f"({block_count} blocks of up to {block_size}). "
                f"Choose one or several blocks (1-{block_count}), "
                "or all (a|all): "
            ).strip().lower()

            if choice in ("a", "all"):
                return

            try:
                block_numbers = [
                    int(value)
                    for value in re.split(r"[\s,]+", choice)
                    if value
                ]
            except ValueError:
                block_numbers = []

            if (block_numbers
                    and all(1 <= number <= block_count for number in block_numbers)):
                # Preserve the CSV/block order and ignore duplicate selections.
                selected_blocks = set(block_numbers)
                self.questions_word = [
                    question
                    for index, question in enumerate(self.questions_word)
                    if index // block_size + 1 in selected_blocks
                ]
                return

            print(
                f"Please choose block numbers from 1 to {block_count}, "
                "separated by spaces or commas, or enter a/all."
            )

    @staticmethod
    def choose_word_field() -> tuple[str, list[str], list[str]]:
        exercise_choices = {}
        exercise_descriptions = []
        for index, field in enumerate(Word.fields(), start=1):
            answer_field, shown_fields, help_fields = field
            choice = str(index)
            exercise_choices[choice] = field

            description = f"{choice} - From {' and '.join(shown_fields)} to {wrap_back_color(answer_field, answer_field)}"
            if help_fields:
                description += f" (help: {' and '.join(help_fields)})"
            exercise_descriptions.append(description)

        while True:
            exercise = input(
                "Which kind of exercise?\n"
                + "\n".join(exercise_descriptions)
                + "\nYour choice: "
            ).strip()
            if exercise in exercise_choices:
                return exercise_choices[exercise]
            print(f"Please choose {', '.join(exercise_choices)}.")

    @staticmethod
    def build_session() -> "Session":
        while True:
            mode = input("What do you want to learn: Vocabulary (v) or Tag (t)? ").strip().lower()
            if mode in ("v", "t"):
                break
            print("Please choose Vocabulary (v) or Tag (t).")

        if mode == "t":
            available_tags = sorted({tag for word in words for tag in word.tags if tag})
            if not available_tags:
                raise ValueError("No tags were found in all_hiragana_with_pos.csv.")
            while True:
                tag_choice = input(
                    "Which tag do you want to review?\n"
                    + "\n".join(
                        f"{index} - {available_tag}"
                        for index, available_tag in enumerate(available_tags)
                    )
                    + "\nYour choice: "
                ).strip()

                if tag_choice in available_tags:
                    tag = tag_choice
                    break
                try:
                    tag_index = int(tag_choice)
                    tag = available_tags[tag_index] if tag_index >= 0 else None
                except (ValueError, IndexError):
                    tag = None

                if tag is not None:
                    break
                print("Please enter a tag name or one of the listed indexes.")

            jlpt_input = input("What JLPT level to review : All (a|all), or one/several levels (e.g. 1, 1 2, 2 4 5) ?")
            jlpt_levels = None if (jlpt_input.strip().lower() == "all" or jlpt_input.strip().lower() == "a") else [int(level) for level in jlpt_input.split()]
            return SessionTags(jlpt_levels, tag, Session.choose_word_field())

        r = input("What test : Kanji (k), Word (w), Both (b) ?")
        kind = None
        if r in ["w", "b"]:
            pos = input("What kind of word : All (a|all), Adjective (adj), Noun (noun), Adverb (adv), Verb (verb) ?")
            kind = POS_CHOICES.get(pos)

        word_field = None
        if r in ["w", "b"]:
            word_field = Session.choose_word_field()

        jlpt_input = input("What JLPT level to review : All (a|all), or one/several levels (e.g. 1, 1 2, 2 4 5) ?")
        jlpt_levels = None if (jlpt_input.strip().lower() == "all" or jlpt_input.strip().lower() == "a") else [int(level) for level in jlpt_input.split()]
        return SessionVocabulary(jlpt_levels, r, kind, word_field)

    def ask(self, subgroup_size: int = 7):
        if subgroup_size < 1:
            raise ValueError("subgroup_size must be greater than zero")

        next_question_number = 1
        subgroup = deque()

        def append_next_question() -> bool:
            nonlocal next_question_number
            if not self.questions_word and not self.questions_kanji:
                return False

            index = random.randint(0, len(self.questions_word) + len(self.questions_kanji) - 1)
            if index < len(self.questions_word):
                subgroup.append((self.questions_word.pop(), False, next_question_number))
                self._pending_questions_word += 1
            else:
                subgroup.append((self.questions_kanji.pop(), False, next_question_number))
                self._pending_questions_kanji += 1
            next_question_number += 1
            return True

        while len(subgroup) < subgroup_size and append_next_question():
            pass

        while subgroup:
            question, is_retry, question_number = subgroup.popleft()
            if not is_retry:
                if isinstance(question.item, Word):
                    self._pending_questions_word -= 1
                else:
                    self._pending_questions_kanji -= 1

            should_continue, is_correct = self.ask_question(question_number, question)
            if not should_continue:
                break
            if is_correct:
                append_next_question()
            else:
                subgroup.append((question, True, question_number))

        # we print the stat :
        total_answer = self.good_answer + self.bad_answer
        print(f"Good answer : {self.good_answer} / {total_answer}.")
        print(f"Bad answer : {self.bad_answer} / {total_answer}.")
        if total_answer > 0:
            print(f"Average score : {self.score / total_answer}.")
        self.print_failed_questions()

    def print_failed_questions(self) -> None:
        if not self.failed_questions:
            return

        print("\nFailed questions (worst first):")
        failed_questions = sorted(
            self.failed_questions.items(),
            key=lambda entry: (-len(entry[1]["attempts"]), entry[1]["question_number"]),
        )
        for position, (question, failure) in enumerate(failed_questions, start=1):
            attempts = failure["attempts"]
            shown_values = ", ".join(
                color_kanji_readings(question.item)
                if field == "word" and isinstance(question.item, Word)
                else getattr(question.item, field)
                for field in question.field[1]
            )
            expected_answer = getattr(question.item, question.field[0])
            attempt_label = "attempt" if len(attempts) == 1 else "attempts"

            print(
                f"{position}. Question {failure['question_number']}: {shown_values} -> "
                f"{question.field[0]} ({len(attempts)} failed {attempt_label})"
            )
            for attempt_number, (response, ratio) in enumerate(attempts, start=1):
                displayed_response = response if response else "<empty>"
                print(f"   Try {attempt_number}: {displayed_response} (score: {ratio})")
            print(f"   Try {len(attempts) + 1}: {expected_answer} (correct)")

    def ask_question(self, index: int, question: Question) -> tuple[bool, bool]:
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', type=str, nargs="+", help="Forbid a description of sentence from a solution.")
        parser.add_argument('-a', type=str, nargs="+", help="Add a description of sentence for a solution.")
        parser.add_argument('-b', action='store_true', help="Burn the last question.")
        parser.add_argument('-u', action='store_true', help="Unburn the last question.")
        parser.add_argument('-r', action='store_true', help="Reset the last question.")
        parser.add_argument('-s', action='store_true', help="Stop the session.")
        flag = False
        help = False
        while True:
            if not help:
                remaining_kanji = len(self.questions_kanji) + self._pending_questions_kanji
                remaining_word = len(self.questions_word) + self._pending_questions_word
                question.ask(f"[{str(index)}/{self.questions_length_initial} (k:{str(remaining_kanji)}/{str(self.questions_kanji_length_initial)}, w:{str(remaining_word)}/{str(self.questions_word_length_initial)}) JLPT:{question.jlpt()}]")
            if help:
                question.help()
            flag = False
            response = input(f"{Fore.BLUE}")
            print(Fore.RESET, end="")
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
            elif args.r:
                flag = True
                self.last_question.reset()
            elif args.s:
                return False, False
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
            self.good_answer = self.good_answer + 1
        else:
            question.error(ratio)
            if not help and not isinstance(question.item, Word):
                question.help()
            self.bad_answer = self.bad_answer + 1
            failure = self.failed_questions.setdefault(
                question,
                {"question_number": index, "attempts": []},
            )
            failure["attempts"].append((response, ratio))
        self.score = self.score + (0.0 if ratio is None else ratio)
        print("")
        self.last_question = question
        return True, is_ok


class SessionVocabulary(Session):
    def __init__(self, jlpt_levels: list[int] | None, test: str, kind: str = None,
                 word_field=None):
        self.jlpt_levels = jlpt_levels
        self.test = test
        self.kind = kind
        self.word_field = word_field
        super().__init__()

    def _build_questions(self) -> None:
        if self.test in ["w", "b"]:
            for word in words[:]:
                if self.jlpt_levels is None or word.jlpt() in self.jlpt_levels:
                    if self.kind is not None and self.kind not in word.kinds:
                        continue
                    try:
                        self.questions_word.append(Question(word, self.word_field))
                    except:
                        pass # This item is burned.
        if self.test in ["k", "b"]:
            for kanji in kanjis.values():
                if self.jlpt_levels is None or kanji.jlpt() in self.jlpt_levels:
                    try:
                        self.questions_kanji.append(Question(kanji))
                    except:
                        pass # This item is burned.


class SessionTags(Session):
    def __init__(self, jlpt_levels: list[int] | None, tag: str, word_field: tuple[str, list[str], list[str]]):
        self.jlpt_levels = jlpt_levels
        self.tag = tag
        self.word_field = word_field
        super().__init__()

    def _build_questions(self) -> None:
        for word in words[:]:
            if self.tag not in word.tags:
                continue
            if self.jlpt_levels is not None and word.jlpt() not in self.jlpt_levels:
                continue
            try:
                self.questions_word.append(Question(word, self.word_field))
            except:
                pass # This item is burned.


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


with open('all_hiragana_with_pos.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Ignore la première ligne (en-tête)
    index = 0
    for row in reader:
        # row = [expression, reading, romaji, meaning, tags, kinds, tags]
        index = index + 1
        if len(row) != 8:
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


def normalize_romaji_response(response: str, kinds: list[str]) -> str:
    """Ignore an optional trailing ``suru`` for noun/suru-verb entries."""
    if "noun" in kinds and "suru verb" in kinds:
        return re.sub(r"\s*suru\s*$", "", response)
    return response


def check_field(response: str, solutions: list[str], forbids: list[str], should_be_exact: bool) -> (bool, float | None):
    ration_response_limit = 1.0 if should_be_exact else 0.6
    ratio_resonse = 0.0
    ratio_forbid_resonse = 0.0
    for solution in solutions:
        tmp_ratio_resonse = SequenceMatcher(None, solution, response).ratio()
        ratio_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_resonse else ratio_resonse
    for forbid in forbids:
        tmp_ratio_resonse = SequenceMatcher(None, forbid, response).ratio()
        ratio_forbid_resonse = tmp_ratio_resonse if tmp_ratio_resonse > ratio_forbid_resonse else ratio_forbid_resonse
    return (False if ratio_forbid_resonse > 0.85 else ratio_resonse >= ration_response_limit,
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


def _hiragana(text: str) -> str:
    """Normalize katakana before comparing it with kanji.json readings.

    ``word.kana`` and the readings in kanji.json are not guaranteed to use the
    same kana alphabet.  Comparing everything as hiragana avoids treating, for
    example, ガク and がく as different readings.
    """
    return "".join(
        chr(ord(character) - 0x60) if "ァ" <= character <= "ヶ" else character
        for character in text
    )


def _reading_variants(reading: str) -> list[str]:
    """Return the dictionary reading plus common compound sound changes.

    The pronunciation found inside a word is sometimes different from the
    isolated dictionary reading.  For example, 学 is listed as がく but is
    pronounced がっ in 学校.  These variants let the matcher recognize a few
    common changes; they are heuristics, not a complete model of Japanese.
    """
    reading = _hiragana(reading.lstrip("-").split(".", 1)[0].replace("-", ""))
    variants = [reading]
    voiced_initials = {
        "か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
        "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
        "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
        "は": "ば", "ひ": "び", "ふ": "ぶ", "へ": "べ", "ほ": "ぼ",
    }
    if reading and reading[0] in voiced_initials:
        variants.append(voiced_initials[reading[0]] + reading[1:])
    if reading.endswith(("く", "き", "ち", "つ")):
        variants.append(reading[:-1] + "っ")
    if reading.endswith("ち"):
        variants.append(reading[:-1])
    return list(dict.fromkeys(variant for variant in variants if variant))


def _kanji_reading_candidates(character: str) -> list[tuple[str, str]]:
    kanji = kanjis.get(character)
    if kanji is None:
        return []

    candidates = []
    for reading_type, readings in (("kun", kanji.readings_kun), ("on", kanji.readings_on)):
        for reading in readings:
            candidates.extend((variant, reading_type) for variant in _reading_variants(reading))
    return sorted(
        set(candidates),
        key=lambda candidate: (-len(candidate[0]), 0 if candidate[1] == "kun" else 1, candidate[0]),
    )


def _classify_kanji_readings(expression: str, kana: str) -> list[str | None]:
    """Match each character in a word to its kun- or on-yomi reading.

    A Word stores the complete kana pronunciation, but not the part belonging
    to each kanji.  We therefore have to align the expression with that kana
    and infer whether every matched kanji reading is kun- or on-yomi.

    A kanji can have several candidate readings, so a choice that matches at
    the current position may fail later in the word.  ``match`` consequently
    uses backtracking, while ``lru_cache`` prevents the same pair of positions
    from being evaluated repeatedly.
    """
    normalized_kana = _hiragana(kana)

    @lru_cache(maxsize=None)
    def match(expression_index: int, kana_index: int):
        if expression_index == len(expression):
            return () if kana_index == len(normalized_kana) else None

        character = expression[expression_index]
        candidates = _kanji_reading_candidates(character)
        # 々 repeats the preceding kanji and therefore shares its candidates.
        if character == "々" and expression_index:
            candidates = _kanji_reading_candidates(expression[expression_index - 1])

        if not candidates:
            # Kana and punctuation must appear literally in the pronunciation;
            # None tells the coloring step to leave this character unchanged.
            literal = _hiragana(character)
            if normalized_kana.startswith(literal, kana_index):
                remainder = match(expression_index + 1, kana_index + len(literal))
                if remainder is not None:
                    return (None,) + remainder
            return None

        for reading, reading_type in candidates:
            if normalized_kana.startswith(reading, kana_index):
                remainder = match(expression_index + 1, kana_index + len(reading))
                if remainder is not None:
                    return (reading_type,) + remainder
        return None

    result = match(0, 0)
    return list(result) if result is not None else [None] * len(expression)


def color_kanji_readings(word: Word) -> str:
    """Color kanji backgrounds for failed-answer output only.

    Applying the colors is simple; most of the preceding code exists to infer
    the reading type because Word does not store it per kanji.
    """
    reading_types = _classify_kanji_readings(word.word, word.kana)
    backgrounds = {"kun": KUN_READING_COLOR, "on": ON_READING_COLOR}
    return "".join(
        backgrounds[reading_type] + character + Style.RESET_ALL
        if reading_type is not None else character
        for character, reading_type in zip(word.word, reading_types)
    )


def is_katakana_present(text: str):
    katakana = "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶー・ヽヾ"
    for character in text:
        if character in katakana:
            return True
    return False


def is_kanji_present(text: str) -> bool:
    return len(list_kanji(text)) != 0


POS_CHOICES = {
    "all": None,
    "noun": "noun",
    "adj": "adjective",
    "adv": "adverb",
    "verb": "verb",
}


def main():
    session = Session.build_session()
    session.ask()


if __name__ == '__main__':
    main()
