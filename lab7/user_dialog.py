import pymorphy2
from PyQt5.QtCore import pyqtSignal, QObject
from state_machine import DialogStateMachine
from user_dict import *
import logging as log
import debug

# Классы ключевых словарей
# A - вопросительные слова
# B - слова направления
# C - слова видов досуга
# D - слова видов мест отдыха
# E - слова названий стран
# F - слова, связанные со временем
# G - погода
# H - слова степеней погодных условий

dialog_sentence_patterns = [
    {
        # Ключевое слово в предложении - вид спорта
        # [A] [B] C [E]
        "required": [user_attract_sport_dict],
        "optional": [user_wish_dict, user_attract_travel_way_dict,
                     user_attract_country_dict],
        "answer_type": "sport"
    },
    {
        # Ключевое слово в предложении - вид отдыха
        # [A] [B] D [E]
        "required": [user_attract_place_dict],
        "optional": [user_wish_dict, user_attract_travel_way_dict,
                     user_attract_country_dict],
        "answer_type": "place"
    },
    {
        # Ключевое слово в предложении - погода в стране / странах
        # [A] [F] G
        "required": [user_attract_weather_dict],
        "optional": [user_wish_dict, user_attract_time_dict],
        "answer_type": "weather"
    },
    {
        # Ключевое слово в предложении - подобрать страну / страны
        # [A] B [E]
        "required": [user_attract_travel_way_dict],
        "optional": [user_attract_country_dict, user_wish_dict],
        "answer_type": "country"
    }
]


# Память ключевых слов, упоминаемых в диалоге
class DialogMemory:
    dialog_memory = {
        "country": None,
        "place": None,
        "sport": None,
        "time": None,
        "weather": None,
        "travel_way": None,
        "user_like_visa": None
    }

    def __init__(self):
        pass

    def save(self, key, value):
        if key in self.dialog_memory:
            if value is not None:
                if len(value):
                    # FIXME: Учитывается только одно слово из списка
                    log.debug(f"Запомнить: {key} = {value[0]}")
                    self.dialog_memory[key] = value

    def restore(self, key):
        if key in self.dialog_memory:
            return self.dialog_memory[key]
        return None

    def reset(self):
        for key in self.dialog_memory:
            self.dialog_memory[key] = None
        log.debug(f"Память диалога очищена!")
        log.debug(self.dialog_memory)


# Класс диалоговой системы
class DialogSystem(QObject):
    dialog_memory = DialogMemory()
    state_machine = DialogStateMachine()
    send_answer_signal = pyqtSignal(str)
    send_analysis_report = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.morph = pymorphy2.MorphAnalyzer()
        self.morphs = None

    def process_text(self, text):
        answer_text, answer_type, prob, self.morphs = self._process_text(text)

        # Отправить сигнал с результатами анализа текста
        self.send_syntactic_analysis_report(self.morphs, answer_type, prob)

        # Отправить сигнал с текстом ответа системы
        self.send_answer_signal.emit(answer_text)

    # Обработка исходного текста
    def _process_text(self, text):
        self.text = text

        # Токенизация исходного текста
        # Результат: набор слов
        words = self.tokenization(text)

        # Морфологический анализ слов
        # Результат: набор нормализованных слов
        morphs = self.morph_analysis(words)

        # Синтаксический анализ нормализованных слов
        # и определение смысла контекста
        answer_type, prob = self.syntactic_analysis(morphs)

        # Формирование ответа системы на основе смысла контекста
        # с учетом выделения уточняющих слов
        answer_text = self.generate_answer(answer_type, morphs)

        return answer_text, answer_type, prob, morphs

    def tokenization(self, text):
        # Упрощение: объяединяем все слова в одно предложение
        for symbol in [".", ",", "?", "!"]:
            text = text.replace(symbol, " ")

        words = text.split()
        log.debug(f"Слова: {words}")
        return words

    def morph_analysis(self, words):
        # TODO: Учитывать несколько результатов (проблема омонимии)
        return list(
            map(lambda word: self.morph.parse(word)[0].normal_form, words))

    def syntactic_analysis(self, words):
        pattern_max_prob = 0.0
        pattern_ans_type = None

        # Перебор всех заложенных паттернов сообщений
        for pattern in dialog_sentence_patterns:
            answer_type, prob = self.apply_pattern(words, pattern)
            if pattern_max_prob < prob:
                pattern_max_prob = prob
                pattern_ans_type = answer_type

        print(f"Максимальная вероятность: {pattern_max_prob};"
              f" Тип ответа: {pattern_ans_type}")

        return pattern_ans_type, pattern_max_prob

    def apply_pattern(self, words, pattern):
        # Вес частей паттерна для подсчета вероятности совпадения
        required_dict_weight = 10.0
        optional_dict_weight = 1.0

        # Суммы весов
        weight_sum = 0
        weight_total = 0

        # Проверка обязательных совпадений со словарем
        for required in pattern["required"]:
            if len(self.intersect_with_dict(words, required)) > 0:
                weight_sum += required_dict_weight
            weight_total += required_dict_weight

        # Проверка необязательных совпадений со словарем
        for optional in pattern["optional"]:
            if len(self.intersect_with_dict(words, optional)) > 0:
                weight_sum += optional_dict_weight
            weight_total += optional_dict_weight

        pattern_apply_prob = weight_sum / weight_total
        answer_type = pattern["answer_type"]
        print(f"Вероятность применения паттерна '{answer_type}':"
              f" {weight_sum} / {weight_total} = {pattern_apply_prob}\n")

        return answer_type, pattern_apply_prob

    def generate_answer(self, answer_type, words):
        # TODO: Добавить реализацию
        answer_text = "Я не понимаю вопроса."
        if answer_type == "sport":
            answer_text = "Ответ про досуг."
        elif answer_type == "place":
            answer_text = "Ответ про место отдыха."
        elif answer_type == "weather":
            answer_text = "Ответ про погоду."
        elif answer_type == "country":
            answer_text = "Ответ про страну / страны."

        # Выделить полезные слова из набора слов
        # и запомнить в памяти диалоговой системы
        self.filter_useful_words_and_save_to_dialog_memory(words)

        # Подготовка ответа

        return answer_text

    def filter_useful_words_and_save_to_dialog_memory(self, words):
        # Поиск пересечений со словарем действия
        travel_way_intersect = \
            self.intersect_with_dict(words, user_attract_travel_way_dict)
        # Запомнить
        self.dialog_memory.save("travel_way", travel_way_intersect)

        # Поиск пересечений со словарем досуга
        sport_intersect = self.intersect_with_dict(words,
                                                   user_attract_sport_dict)
        # Запомнить
        self.dialog_memory.save("sport", sport_intersect)

        # Поиск пересечений со словарем мест отдыха
        place_intersect = self.intersect_with_dict(words,
                                                   user_attract_place_dict)
        # Запомнить
        self.dialog_memory.save("place", place_intersect)

        # Поиск пересечений со словарем стран
        country_intersect = self.intersect_with_dict(words,
                                                     user_attract_country_dict)
        # Запомнить
        self.dialog_memory.save("country", country_intersect)

        # Поиск пересечений со словарем времени
        time_intersect = self.intersect_with_dict(words,
                                                  user_attract_time_dict)
        # Запомнить
        self.dialog_memory.save("time", time_intersect)

        # Поиск пересечений со словарем погодных условий
        weather_intersect = self.intersect_with_dict(words, weather_dict)
        # Запомнить
        self.dialog_memory.save("weather", weather_intersect)

    def send_syntactic_analysis_report(self, words, answer_type, prob):
        if not len(words):
            return

        # Поиск пересечений со словарем вопросительных слов
        wish_intersect = self.intersect_with_dict(words, user_wish_dict)

        # Поиск пересечений со словарем действия
        travel_way_intersect = \
            self.intersect_with_dict(words, user_attract_travel_way_dict)

        # Поиск пересечений со словарем досуга
        sport_intersect = self.intersect_with_dict(words,
                                                   user_attract_sport_dict)

        # Поиск пересечений со словарем мест отдыха
        place_intersect = self.intersect_with_dict(words,
                                                   user_attract_place_dict)

        # Поиск пересечений со словарем стран
        country_intersect = self.intersect_with_dict(words,
                                                     user_attract_country_dict)

        # Поиск пересечений со словарем времени
        time_intersect = self.intersect_with_dict(words, user_attract_time_dict)

        # Поиск пересечений со словарем погоды
        weather_intersect = self.intersect_with_dict(words, weather_dict)

        # Поиск пересечений со словарем погодных условий
        weather_wish_intersect = \
            self.intersect_with_dict(words, user_attract_weather_dict)

        # Отчет синтаксического анализа
        syntactic_report = f'Слова из словаря:\n'
        syntactic_report += f'(А) {wish_intersect}\n'
        syntactic_report += f'(B) {travel_way_intersect}\n'
        syntactic_report += f'(C) {sport_intersect}\n'
        syntactic_report += f'(D) {place_intersect}\n'
        syntactic_report += f'(E) {country_intersect}\n'
        syntactic_report += f'(F) {time_intersect}\n'
        syntactic_report += f'(G) {weather_intersect}\n'
        syntactic_report += f'(H) {weather_wish_intersect}\n'

        syntactic_report += f'\nКонтекст ответа:\n'
        syntactic_report += f'{answer_type}\n'

        syntactic_report += f'\nВероятность:\n'
        prob_normalized = format(prob, '.2f')
        syntactic_report += f'{prob_normalized}'

        self.send_analysis_report.emit(syntactic_report)

    def intersect_with_dict(self, words, dictionary):
        words_set = set(words)
        return list(words_set.intersection(dictionary))

    def attract_country(self):
        morphs = set(self.morphs)
        return list(morphs.intersection(user_attract_country_dict))

    def attract_sport(self):
        morphs = set(self.morphs)
        return list(morphs.intersection(user_attract_sport_dict))

    def attract_travel_way(self):
        morphs = set(self.morphs)
        return list(morphs.intersection(user_attract_travel_way_dict))

    def attract_place(self):
        morphs = set(self.morphs)
        return list(morphs.intersection(user_attract_place_dict))

    def attract_time(self):
        morphs = set(self.morphs)
        return list(morphs.intersection(user_attract_time_dict))

    def weather(self):
        morphs = set(self.morphs)
        return list(morphs.intersection(weather_dict))

    def attract_weather(self):
        morphs = set(self.morphs)
        return list(morphs.intersection(user_attract_weather_dict))
