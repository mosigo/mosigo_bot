from abc import abstractmethod

import json
import os

from question import Question


class UserDataStorage:

    @abstractmethod
    def get_user_current_question(self, user_id):
        """
        Возвращает вопрос, который был задан пользователю последним и на который ещё не получен ответ. None, если
        сейчас пользователь в той стадии, когда неотвеченных вопросов нет.

        :param user_id: telegram-ID пользователя (int)
        """
        pass

    @abstractmethod
    def put_user_current_question(self, user_id, question):
        """
        Сохраняет вопрос, который был задан пользователю.

        :param user_id: telegram-ID пользователя (int), которому задавался вопрос
        :param question: вопрос, который был задан (Question)
        """
        pass

    @abstractmethod
    def clear_user_current_question(self, user_id):
        """
        Очищает информацию о последнем заданном вопросе пользователю.

        :param user_id: telegram-ID пользователя (int)
        """
        pass

    @abstractmethod
    def get_user_complexity(self, user_id):
        """
        Возвращает сложность, которая была выбрана пользователем (или значение по умолчанию, если пользователь
        ничего не выбирал.

        :param user_id: telegramID пользователя (int)
        """
        pass

    @abstractmethod
    def set_user_complexity(self, user_id, complexity):
        """
        Устанавливает сложность игры для пользователя: 1, 2 или 3. Если передано что-то другое, то происходит
        исключительная ситуация (ValueError).

        :param user_id: telegram-ID пользователя (int)
        :param complexity: сложность игры (int): 1, 2 или 3
        """
        pass

    @abstractmethod
    def get_user_victories_count(self, user_id):
        """
        Возвращает кол-во побед пользователя (int).

        :param user_id: telegram-ID пользователя (int)
        """
        pass

    @abstractmethod
    def get_user_defeats_count(self, user_id):
        """
        Возвращает кол-во поражений пользователя (int).

        :param user_id: telegram-ID пользователя (int)
        """
        pass

    @abstractmethod
    def add_user_victory(self, user_id):
        """
        Записывает на счёт пользователя одну новую победу.

        :param user_id: telegram-ID пользователя (int)
        """
        pass

    @abstractmethod
    def add_user_defeat(self, user_id):
        """
        Записывает на счёт пользователя одно новое поражение.

        :param user_id: telegram-ID пользователя (int)
        """
        pass


class InMemoryUserDataStorage(UserDataStorage):

    def __init__(self):
        # для каждого пользователя храним текущий активный вопрос
        self.user_current_questions = {}

        # для каждого пользователя храним предпочитаемую сложность
        self.user_complexity = {}
        self.acceptable_complexities = ['1', '2', '3']
        self.default_complexity = '1'

        # для каждого пользователя храним счётчик его побед и поражений
        self.user_victories = {}
        self.user_defeats = {}

    def get_user_current_question(self, user_id):
        return self.user_current_questions.get(user_id)

    def put_user_current_question(self, user_id, question):
        self.user_current_questions[user_id] = question

    def clear_user_current_question(self, user_id):
        del self.user_current_questions[user_id]

    def get_user_complexity(self, user_id):
        return self.user_complexity.get(user_id, self.default_complexity)

    def set_user_complexity(self, user_id, complexity):
        if complexity not in self.acceptable_complexities:
            raise ValueError(f'Недопустимое значение для сложности игры: {complexity}, '
                             f'допустимые значения: {",".join(self.acceptable_complexities)}')
        self.user_complexity[user_id] = complexity

    def get_user_victories_count(self, user_id):
        return self.user_victories.get(user_id, 0)

    def get_user_defeats_count(self, user_id):
        return self.user_defeats.get(user_id, 0)

    def add_user_victory(self, user_id):
        self.user_victories[user_id] = self.get_user_victories_count(user_id) + 1

    def add_user_defeat(self, user_id):
        self.user_defeats[user_id] = self.get_user_defeats_count(user_id) + 1


class InMemoryWithFileSavingDataStorage(UserDataStorage):

    @staticmethod
    def __question_to_json(question):
        return {
            'question': question.question,
            'answers': question.answers,
            'correct_answer': question.correct_answer
        }

    @staticmethod
    def __question_from_json(question_json):
        return Question(
            question_json['question'],
            question_json['answers'],
            question_json['correct_answer']
        )

    @staticmethod
    def __convert_map(data, key_function=lambda k: k, value_function=lambda v: v):
        result = {}
        for k, v in data.items():
            result[key_function(k)] = value_function(v)
        return result

    def __init__(self, file_name):
        self.in_memory_storage = InMemoryUserDataStorage()

        current_dir = os.path.abspath(os.path.dirname(__file__))
        file = os.path.join(current_dir, file_name)

        self.file_path = file
        if os.path.isfile(file):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.__from_json(data)

    def __save_to_file(self):
        json_data = self.__to_json()
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

    def __to_json(self):
        return {
            'user_current_questions': self.__convert_map(
                self.in_memory_storage.user_current_questions,
                value_function=self.__question_to_json
            ),
            'user_complexity': self.in_memory_storage.user_complexity,
            'user_victories': self.in_memory_storage.user_victories,
            'user_defeats': self.in_memory_storage.user_defeats
        }

    def __from_json(self, json_data):

        self.in_memory_storage.user_current_questions = \
            self.__convert_map(
                json_data.get('user_current_questions', {}),
                key_function=int,
                value_function=self.__question_from_json
            )

        self.in_memory_storage.user_complexity = \
            self.__convert_map(json_data.get('user_complexity', {}), key_function=int)

        self.in_memory_storage.user_victories = \
            self.__convert_map(json_data.get('user_victories', {}), key_function=int)

        self.in_memory_storage.user_defeats = \
            self.__convert_map(json_data.get('user_defeats', {}), key_function=int)

    def get_user_current_question(self, user_id):
        return self.in_memory_storage.get_user_current_question(user_id)

    def put_user_current_question(self, user_id, question):
        self.in_memory_storage.put_user_current_question(user_id, question)
        self.__save_to_file()

    def clear_user_current_question(self, user_id):
        self.in_memory_storage.clear_user_current_question(user_id)
        self.__save_to_file()

    def get_user_complexity(self, user_id):
        return self.in_memory_storage.get_user_complexity(user_id)

    def set_user_complexity(self, user_id, complexity):
        self.in_memory_storage.set_user_complexity(user_id, complexity)
        self.__save_to_file()

    def get_user_victories_count(self, user_id):
        return self.in_memory_storage.get_user_victories_count(user_id)

    def get_user_defeats_count(self, user_id):
        return self.in_memory_storage.get_user_defeats_count(user_id)

    def add_user_victory(self, user_id):
        self.in_memory_storage.add_user_victory(user_id)
        self.__save_to_file()

    def add_user_defeat(self, user_id):
        self.in_memory_storage.add_user_defeat(user_id)
        self.__save_to_file()


if __name__ == '__main__':
    ds = InMemoryWithFileSavingDataStorage('storage.json')
    ds.add_user_victory(11122333)
    ds.add_user_defeat(11122333)
    ds.set_user_complexity(11122333, '2')
    ds.put_user_current_question(11122333, Question('Какую площадь имеет клетка стандартной школьной тетрадки:',
                                                    ['0,25', '1,00', '0,5', '1,25'], '0,25'))
