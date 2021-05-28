# Вспомогательная функция, возвращающая унифицированное сообщение, пришедшее от пользователя боту
def get_unified_user_message(message):
    return unify_message(message.text)


# Вспомогательная функция, которая преобразует текстовое сообщение в "унифицированный" вид
def unify_message(message_text):
    if message_text is not None:
        return message_text.lower().strip()
    return ''


# Функция, извлекающая ID чата для ответа из сообщения
def get_chat_id_to_reply(message):
    return message.from_user.id


# Вспомогательная функция, которая проверяет, что ответ пользователя находится в списке возможных вариантов,
# которые бот предлагал в качестве ответа
def is_user_try_answer(user_message, answers):
    for answer in answers:
        if user_message == unify_message(answer):
            return True
    return False