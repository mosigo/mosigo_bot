import os

import telebot
import re
import logging

from telebot.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from message_processor import get_unified_user_message, get_chat_id_to_reply, unify_message, is_user_try_answer
from question import CompositeQuestionStorage, AkentevQuestionStorage, InMemoryQuestionStorage, DEFAULT_QUESTIONS
from user_data import InMemoryUserDataStorage, RedisDataStorage, InMemoryWithFileSavingDataStorage

token = '1621053959:AAH0OF1Yh6mLDNZW1DahCbTl1KYN77DP9Iw'
bot = telebot.TeleBot(token)

telebot.logger.setLevel(logging.DEBUG)

# регулярное выражение для команды от пользователя на изменение сложности
complexity_reg_exp = r'^сложность ([123])$'

# стартовое сообщение, которое выводит бот, если его спрашивают про правила или если он не понял, что от него хотят
start_message = 'Это бот-игра в "Кто хочет стать миллионером". Скажи мне "Спроси меня вопрос", чтобы сыграть, ' \
                'или "Покажи счёт", чтобы узнать число твоих побед и поражений. ' \
                'Меняй сложность игры, сказав "Сложность 1", "Сложность 2" или "Сложность 3"!'

# сообщение пользователю в случае внутренней ошибки бота
internal_error_message = 'Со мной что-то не так... Попробуй сказать мне что-то другое'

# хранилище вопросов для игры, которое использует наш бот: сначала пытаемся получить вопрос через API,
# если это не получилось (произошла ошибка или API вернуло статус, отличный от 200), то берём вопрос из памяти
question_storage = CompositeQuestionStorage(
    [
        AkentevQuestionStorage(),
        InMemoryQuestionStorage(DEFAULT_QUESTIONS)
    ]
)

# хранилище состояния для каждого пользователя
user_data_storage = InMemoryWithFileSavingDataStorage('storage.json')
redis_url = os.environ.get('REDIS_URL')
if redis_url is not None:
    user_data_storage = RedisDataStorage(redis_url)


def send_message_about_internal_exception(bot, user_id, e):
    """
    Отправляет сообщение о том, что случилась внутренняя ошибка в логике работы бота.

    :param bot: объект бота (TeleBot)
    :param user_id: telegramID пользователя (int)
    :param e: объект случившейся ошибки (Exception)
    """
    telebot.logger.error(e)
    bot.send_message(user_id, internal_error_message)


def send_start_message(bot, user_id):
    """
    Отправляет сообщение, в котором описываются возможности бота. Также отправляется клавиатура
    с готовыми командами.

    :param bot: объект бота (TeleBot)
    :param user_id: telegramID пользователя (int)
    """
    markup = ReplyKeyboardMarkup()

    markup.row(KeyboardButton('Спроси меня вопрос'), KeyboardButton('Покажи счёт'))
    markup.row(KeyboardButton('Сложность 1'), KeyboardButton('Сложность 2'), KeyboardButton('Сложность 3'))
    markup.row(KeyboardButton('Как играть?'))

    bot.send_message(user_id, start_message, reply_markup=markup)


def send_message_with_question(bot, user_id, question, prefix=''):
    """
    Отправляет сообщение с вопросом для пользователя.

    :param bot: объект бота (TeleBot)
    :param user_id: telegramID пользователя (int)
    :param question: вопрос, который задаётся (Question)
    :param prefix: текст, который добавляется перед текстом вопроса (str)
    """
    markup = InlineKeyboardMarkup(row_width=2)
    [val1, val2, val3, val4] = question.answers
    markup.add(InlineKeyboardButton(val1, callback_data=val1), InlineKeyboardButton(val2, callback_data=val2))
    markup.add(InlineKeyboardButton(val3, callback_data=val3), InlineKeyboardButton(val4, callback_data=val4))

    message = f'{prefix}{question.question}'
    bot.send_message(user_id, message, reply_markup=markup)


@bot.message_handler(commands=['start'])
@bot.message_handler(
    func=lambda message: get_unified_user_message(message) in ['что ты умеешь?', 'как играть?'])
def start(message):
    send_start_message(bot, get_chat_id_to_reply(message))


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) in ['что ты умеешь?', 'как играть?'])
def start_handler(message):
    send_start_message(bot, get_chat_id_to_reply(message))


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) in ['привет', 'привет!', 'привет'])
def hello_handler(message):
    bot.send_message(get_chat_id_to_reply(message), 'Ну привет!')


@bot.message_handler(
    func=lambda message: re.match(complexity_reg_exp, get_unified_user_message(message)))
def complexity_handler(message):
    user_id = get_chat_id_to_reply(message)
    try:
        m = re.match(complexity_reg_exp, get_unified_user_message(message))
        if m:
            complexity = m.group(1)
            user_data_storage.set_user_complexity(user_id, complexity)

            bot.send_message(user_id, f'Изменил сложность игры на {complexity} из 3!')
    except Exception as e:
        send_message_about_internal_exception(bot, user_id, e)


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) == 'спроси меня вопрос')
def ask_question_handler(message):
    user_id = get_chat_id_to_reply(message)
    try:
        question = user_data_storage.get_user_current_question(user_id)
        if question is None:
            complexity = user_data_storage.get_user_complexity(user_id)
            question = question_storage.get_question(complexity)
            user_data_storage.put_user_current_question(user_id, question)
            send_message_with_question(bot, user_id, question)
        else:
            send_message_with_question(bot, user_id, question,
                                       prefix='Ты пока не ответил на предыдущий вопрос. Повторю его для тебя!\n\n')
    except Exception as e:
        send_message_about_internal_exception(bot, user_id, e)


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) in ['покажи счёт'])
def scores_handler(message):
    user_id = get_chat_id_to_reply(message)
    try:
        victories = user_data_storage.get_user_victories_count(user_id)
        defeats = user_data_storage.get_user_defeats_count(user_id)
        bot.send_message(user_id, f'Побед: {victories}, поражений: {defeats}')
    except Exception as e:
        send_message_about_internal_exception(bot, user_id, e)


@bot.callback_query_handler(func=lambda call: True)
def answer_callback(callback):
    user_id = get_chat_id_to_reply(callback)
    try:
        user_message = unify_message(callback.data)

        question = user_data_storage.get_user_current_question(user_id)
        if question is not None:
            if is_user_try_answer(user_message, question.answers):
                if user_message == unify_message(question.correct_answer):
                    bot.send_message(user_id, '👍 Правильно!')
                    user_data_storage.add_user_victory(user_id)
                else:
                    bot.send_message(user_id, f'😔 Неправильно. Верный ответ был "{question.correct_answer}"')
                    user_data_storage.add_user_defeat(user_id)

                user_data_storage.clear_user_current_question(user_id)
            else:
                send_message_with_question(bot, user_id, question,
                                           prefix='Ты отвечаешь не на последний вопрос! Могу засчитать за неверный '
                                                  'ответ, но, может, всё же ответишь как нужно?\n\n')
        else:
            bot.send_message(user_id, 'На этот вопрос ты уже отвечал! Попроси меня задать новый')
    except Exception as e:
        send_message_about_internal_exception(bot, user_id, e)


@bot.message_handler(func=lambda message: True)
def default_handler(message):
    user_id = get_chat_id_to_reply(message)
    try:
        question = user_data_storage.get_user_current_question(user_id)
        if question is not None:
            bot.send_message(user_id, 'Нажми на кнопку ответа, который считаешь верным')
        else:
            send_start_message(bot, user_id)
    except Exception as e:
        send_message_about_internal_exception(bot, user_id, e)


bot.polling()
