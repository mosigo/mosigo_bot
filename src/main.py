import telebot
import re

from keyboa.keyboards import keyboa_maker
from telebot import types

from message_processor import get_unified_user_message, get_chat_id_to_reply, unify_message, is_user_try_answer
from question import CompositeQuestionStorage, AkentevQuestionStorage, InMemoryQuestionStorage, DEFAULT_QUESTIONS
from user_data import InMemoryWithFileSavingDataStorage

token = '1621053959:AAH0OF1Yh6mLDNZW1DahCbTl1KYN77DP9Iw'
bot = telebot.TeleBot(token)

# регулярное выражение для команды от пользователя на изменение сложности
complexity_reg_exp = r'^сложность ([123])$'

# стартовое сообщение, которое выводит бот, если его спрашивают про правила или если он не понял, что от него хотят
start_message = 'Это бот-игра в "Кто хочет стать миллионером". Скажи мне "Спроси меня вопрос", чтобы сыграть, ' \
                'или "Покажи счёт", чтобы узнать число твоих побед и поражений. ' \
                'Меняй сложность игры, сказав "Сложность 1", "Сложность 2" или "Сложность 3"!'

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


def send_message_with_question(bot, user_id, question, prefix=''):
    message = f'{prefix}{question.question}'
    keyboard_answers = keyboa_maker(items=question.answers, copy_text_to_callback=True, items_in_row=2)
    bot.send_message(user_id, message, reply_markup=keyboard_answers)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup()

    markup.row(types.KeyboardButton('Спроси меня вопрос'), types.KeyboardButton('Покажи счёт'))
    markup.row(types.KeyboardButton('Сложность 1'), types.KeyboardButton('Сложность 2'), types.KeyboardButton('Сложность 3'))
    markup.row(types.KeyboardButton('Как играть?'))

    bot.send_message(message.chat.id, start_message, reply_markup=markup)


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) in ['/start', 'что ты умеешь?', 'как играть?'])
def start_handler(message):
    bot.send_message(get_chat_id_to_reply(message), start_message)


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) in ['привет'])
def hello_handler(message):
    bot.send_message(get_chat_id_to_reply(message), 'Ну привет!')


@bot.message_handler(
    func=lambda message: re.match(complexity_reg_exp, get_unified_user_message(message)))
def start_handler(message):
    user_id = get_chat_id_to_reply(message)
    m = re.match(complexity_reg_exp, get_unified_user_message(message))
    if m:
        complexity = m.group(1)
        user_data_storage.set_user_complexity(user_id, complexity)

        bot.send_message(user_id, f'Изменил сложность игры на {complexity} из 3!')


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) == 'спроси меня вопрос')
def ask_question_handler(message):
    user_id = get_chat_id_to_reply(message)
    question = user_data_storage.get_user_current_question(user_id)
    if question is None:
        complexity = user_data_storage.get_user_complexity(user_id)
        question = question_storage.get_question(complexity)
        user_data_storage.put_user_current_question(user_id, question)
        send_message_with_question(bot, user_id, question)
    else:
        send_message_with_question(bot, user_id, question,
                                   prefix='Ты пока не ответил на предыдущий вопрос. Повторю его для тебя!\n\n')


@bot.message_handler(
    func=lambda message: get_unified_user_message(message) in ['покажи счёт'])
def hello_handler(message):
    user_id = get_chat_id_to_reply(message)
    victories = user_data_storage.get_user_victories_count(user_id)
    defeats = user_data_storage.get_user_defeats_count(user_id)
    bot.send_message(user_id, f'Побед: {victories}, поражений: {defeats}')


@bot.callback_query_handler(func=lambda call: True)
def answer_callback(callback):
    user_message = unify_message(callback.data)
    user_id = get_chat_id_to_reply(callback)

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
                                       prefix='Ты отвечаешь не на последний вопрос! Могу засчитать за неверный ответ, '
                                              'но, может, всё же ответишь как нужно?\n\n')
    else:
        bot.send_message(user_id, 'На этот вопрос ты уже отвечал! Попроси меня задать новый: "спроси меня вопрос"')


@bot.message_handler(func=lambda message: True)
def default_handler(message):
    user_id = get_chat_id_to_reply(message)
    question = user_data_storage.get_user_current_question(user_id)
    if question is not None:
        bot.send_message(user_id, 'Нажми на кнопку ответа, который считаешь верным')
    else:
        bot.send_message(user_id, start_message)


bot.polling()
