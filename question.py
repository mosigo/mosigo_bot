from abc import abstractmethod

import random
import requests


class Question:

    def __init__(self, question, answers, correct_answer):
        """
        Вопрос для игры "Кто хочет стать миллионером". Если верный ответ не содержится в вариантах ответа,
        происходит исключительная ситуация (ValueError).

        :param question: формулировка вопроса (str)
        :param answers: возможные варианты ответа ([str])
        :param correct_answer: верный ответ (str)
        """
        if correct_answer not in answers:
            raise ValueError('Варианты ответа на вопрос не содержат верный ответ. Вопрос не может быть создан')
        self.question = question
        self.answers = answers
        self.correct_answer = correct_answer


# Объект, представляющий собой хранилище вопросов
class QuestionStorage:

    @abstractmethod
    def get_question(self, complexity):
        """
        Получает очередной вопрос при помощи внешнего API.

        :param complexity: предпочитаемая сложность (str)
        :return: Question (вопрос (str), варианты ответа ([str]), правильный ответ (str))
        """
        pass


# Реализация хранилища вопросов, которая ходит через внешнее API и получает очередной вопрос оттуда
class AkentevQuestionStorage(QuestionStorage):

    def get_question(self, complexity):
        r = requests.get(
            'https://stepik.akentev.com/api/millionaire',
            params={
                'complexity': complexity
            }
        )
        r.raise_for_status()

        data = r.json()

        question = data['question']
        answers = data['answers']
        solution = answers[0]

        random.shuffle(answers)

        return Question(question, answers, solution)


# Реализация хранилища вопросов, которая берёт данные из хранящегося в памяти массива вопросов
class InMemoryQuestionStorage(QuestionStorage):

    def __init__(self, questions_db):
        """
        Получает базу вопросов в виде массива.

        :param questions_db: список вопросов с вариантами ответов и верным ответом ([(str, [str], str)])
        """
        self.questions = questions_db

    def get_question(self, complexity):
        return random.choice(self.questions)


# Реализация хранилища вопросов, которая имеет ссылки на другие хранилища вопросов и пытается запросить очередной
# вопрос у каждого хранилища, пока это не закончится успехом
class CompositeQuestionStorage(QuestionStorage):

    def __init__(self, storages):
        self.storages = storages

    def get_question(self, complexity):
        for storage in self.storages:
            try:
                return storage.get_question(complexity)
            except Exception as e:
                print(e)
        raise RuntimeError('Не удалось получить вопрос ни от одного хранилища вопросов')


# база вопросов с правильными ответами (используется в случае неработоспособности API)
DEFAULT_QUESTIONS = [
    Question('Какую площадь имеет клетка стандартной школьной тетрадки:',
             ['0,25', '1,00', '0,5', '1,25'], '0,25'),
    Question('Чему равен экваториальный радиус Земли в километрах?',
             ['6378,1', '6356,8', '6371,0', '6384,1'], '6378,1'),
    Question('Какая планета Солнечной системы находится дальше всего от Солнца и Земли?',
             ['Юпитер', 'Нептун', 'Венера', 'Марс'], 'Нептун')
]
