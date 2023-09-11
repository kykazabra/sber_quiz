import telebot
import pandas as pd
import random
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import io
import datetime
from gridfs import GridFS

uri = "mongodb+srv://olok1:utofir33@cluster0.lfjwngi.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, server_api=ServerApi('1'))
TOKEN = "6511630353:AAFxjc7F59bVJwaKOYqhD6KYjqm0AcPYudY"
bot = telebot.TeleBot(TOKEN)

db = client.testdata

start_text =("Тест разделен на 2 части: в первой части 7 легких вопросов, а во второй 3 более сложных . За каждый правильный ответ ты получишь балл,твоя задача получить 5 балов в первом модуле и 1 во втором. Можешь не бояться, если не получится пройти тест по выбранному направлению, то ты сможешь попробовать свои силы в другом)\n\nПосле прохождения тестирования не забудь показать свой итоговый результат на стенде Сбера, что бы получить свой приз. Там тебе скажут,что делать дальше.\nПоехали !")

# функциы чтобы извлекать фото из бд
def p(id):
    fs = GridFS(client.testdata, collection="photos")
    file_cursor = fs.find_one({"filename": id})
    if file_cursor:
        image_data = file_cursor.read()
        image_io = io.BytesIO(image_data)
        image_io.seek(0)
    return image_io


# Функция чтобы вопросы не повторялись
def chek_next(chat_id, category, level):
    num = [i['_id'] for i in db.questions.find({"category": category, 'level': level})]
    num_2 = [i['question_id'] for i in db.answer.find({"user_id": chat_id, 'type': f'ask_{category}'})]
    choice = random.choice(list(set(num) - set(num_2)))

    return choice


# вывод статистики
def stats(chat_id, user_data, types, level):
    if (user_data.get(f"level_DS") == 2) and (user_data.get(f"level_DE") == 2):
        db.answer.delete_one({'type': 'ask'})
    else:
        pass
    correct_answers = db.answer.count_documents(
        {"user_id": chat_id, "res": True, "type": f'ask_{types}', 'level': level})
    total_questions = db.answer.count_documents({"user_id": chat_id, "type": f'ask_{types}', 'level': level})

    time = []
    for i in db.answer.find({"user_id": chat_id, "type": f'ask_{types}', 'level': level}):
        time.append(i['time'])

    time_start = (datetime.datetime.strptime((time[0]), '%H:%M:%S'))
    time_end = (datetime.datetime.strptime((time[-1]), '%H:%M:%S'))

    times = time_end - time_start

    result_message = f"Всего вопросов: {total_questions}\n"
    result_message += f"Отвечено правильно: {correct_answers}\n"
    result_message += f"Время : {times}\n"
    return result_message


def finish(chat_id, q_type):
    check_1 = db.answer.count_documents({"user_id": chat_id, "res": True, "type": f'ask_{q_type}', 'level': 1})
    check_2 = db.answer.count_documents({"user_id": chat_id, "res": True, "type": f'ask_{q_type}', 'level': 2})

    correct_answers = db.answer.count_documents({"user_id": chat_id, "res": True, "type": f'ask_{q_type}'})
    total_questions = db.answer.count_documents({"user_id": chat_id, "type": f'ask_{q_type}'})
    accuracy_percentage = round((correct_answers / total_questions) * 100, 1)

    if (check_1) > 4 and (check_2) > 0:

        text1 = f'Вы набрали больше необходимого количества баллов.\nТвой результат: {accuracy_percentage}% отличный результат!\n\
Если хочешь испытать свои силы на реальных задачах, подавай заявку на стажировку SberSeasons или приходи прокачивать свои IT навыки в Школу 21'

        text2 = 'Подходи на стенд Сбера и получи свой подарочек \n'

        markup = types.InlineKeyboardMarkup(row_width=2)
        button1 = types.InlineKeyboardButton('SberSeason',
                                             'https://sbergraduate.ru/sberseasons-moscow/?utm_source=sberu&utm_campaign=event130923')
        button2 = types.InlineKeyboardButton('Школа 21', 'https://21-school.ru')
        button3 = types.InlineKeyboardButton('Developer Sber', 'https://developers.sber.ru/kak-v-sbere/teams/sber-data')
        markup.add(button1, button2, button3)

        bot.send_message(chat_id, text1, reply_markup=markup)
        bot.send_message(chat_id, text2)
    else:

        text3 = f'Вы набрали меньше необходимого количества баллов.\nТвой результат: {accuracy_percentage}%\n\
Не расстраивайся, прокачивайся в {q_type}\n '

        bot.send_message(chat_id, text3)


# Вовод вопроса и ответа после выбора
def evaluate_question(chat_id, question_num, correct_answer_index, user_answer_index):
    info = db.questions.find_one({"_id": question_num})
    question = info['question']
    answer_choices = info['options']
    feedback = []
    correct_answer_index -= 1
    user_answer_index -= 1
    options = ["a", "b", "c", "d"]
    for i, answer in enumerate(answer_choices):
        if i == correct_answer_index == user_answer_index:

            feedback.append(f"{options[i]}. {answer} ✅")
        elif i == user_answer_index != correct_answer_index:
            feedback.append(f"{options[i]}. {answer} ❌")
        else:
            feedback.append(f"{options[i]}. {answer}")

    res = f"{question}\n\n" + '\n'.join(feedback)

    bot.send_message(chat_id, res)


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data = db.test.find_one({"user_id": chat_id})

    if not user_data:
        db.test.insert_one({"user_id": chat_id, "current_question": 1, "level_DS": 1, "level_DE": 1, 'status': 0})
        db.answer.insert_one(
            {"user_id": chat_id, "type": 'start', 'time': datetime.datetime.now().strftime('%H:%M:%S')})
        db.temp_answer.insert_one(
            {"user_id": chat_id, "type": 'start', 'time': datetime.datetime.now().strftime('%H:%M:%S')})

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)  ### Добавил чтобы клавиатура пропадала
        DS = types.KeyboardButton("DS\n"
                                  "(Data Science)")
        DE = types.KeyboardButton("DE\n"
                                  "(Data Engineer)")
        markup.add(DS, DE)
        bot.send_message(chat_id, start_text)
        bot.send_message(chat_id, "Выберите блок:", reply_markup=markup)
    else:
        pass


#
@bot.message_handler(func=lambda message: message.text in ["DS\n(Data Science)", "DE\n(Data Engineer)"])
def handle_direction(message):
    chat_id = message.chat.id
    user_data = db.test.find_one({"user_id": chat_id})
    q_type = (message.text).split('\n')[0]
    level = user_data.get(f"level_{q_type}", 0)

    if user_data.get('status') == 0:

        db.answer.insert_one({"user_id": chat_id, 'type': f"press_{q_type}", 'level': level,
                              'time': datetime.datetime.now().strftime('%H:%M:%S')})
        db.temp_answer.insert_one({"user_id": chat_id, 'type': f"press_{q_type}", 'level': level,
                              'time': datetime.datetime.now().strftime('%H:%M:%S')})

        next_ = db.test.find_one({"user_id": chat_id}).get('current_question')

        if user_data.get("current_question") < 10:

            question_data = db.questions.find_one({"_id": chek_next(chat_id, q_type, level)})
            question_num = question_data.get('_id')

            if question_data:
                options = ['A', "B", 'C', 'D']
                markup = types.InlineKeyboardMarkup(row_width=2)
                for i in range(len(options)):
                    button = types.InlineKeyboardButton(options[i],
                                                        callback_data=f'answer_{question_num}_{i + 1}_{q_type}_{level}',
                                                        resize_keyboard=True)
                    markup.add(button)

                bot.send_message(chat_id, f"Вопрос {user_data['current_question']}")
                bot.send_photo(chat_id, photo=p(question_data['_id']), reply_markup=markup)

            db.test.update_one({"user_id": chat_id},
                               {"$set": {"current_question": next_ + 1}})
            db.test.update_one({"user_id": chat_id},
                               {"$set": {"status": 1}})
    else:
        pass


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.message:
        chat_id = call.message.chat.id
        user_data = db.test.find_one({"user_id": chat_id})
        # print(user_data)

        parts = call.data.split("_")
        # print(parts)
        question_num = int(parts[1])
        selected_answer = int(parts[2])
        q_type = parts[3]
        # print(q_type)
        # level = int(parts[4])
        level = int(user_data.get(f"level_{q_type}"))

        if question_num == 0:
            bot.delete_message(chat_id, call.message.message_id)
            db.answer.insert_one({"user_id": chat_id,
                                  'type': 'press_yes', 'time': datetime.datetime.now().strftime('%H:%M:%S')})
            db.temp_answer.insert_one({"user_id": chat_id,
                                  'type': 'press_yes', 'time': datetime.datetime.now().strftime('%H:%M:%S')})

        else:
            true_answer = db.questions.find_one({"_id": question_num}).get('correct_answer')
            res = selected_answer == true_answer
            bot.delete_message(chat_id, call.message.message_id)

            evaluate_question(chat_id, question_num, true_answer, selected_answer)

            db.answer.insert_one({"user_id": chat_id, 'question_id': question_num,
                                  "selected_answer": selected_answer, "true_answer": true_answer, 'res': res,
                                  'type': f'ask_{q_type}', 'level': level,
                                  'time': datetime.datetime.now().strftime('%H:%M:%S')})

            db.temp_answer.insert_one({"user_id": chat_id, 'question_id': question_num,
                                  "selected_answer": selected_answer, "true_answer": true_answer, 'res': res,
                                  'type': f'ask_{q_type}', 'level': level,
                                  'time': datetime.datetime.now().strftime('%H:%M:%S')})

        if (user_data.get(f"level_{q_type}") == 1):
            stop = 8
        else:
            stop = 11

        if user_data.get("current_question") < stop:
            # print('проверка',level,q_type)
            next_question_num = chek_next(chat_id, q_type, level)

            next_question_data = db.questions.find_one({"_id": next_question_num})

            if next_question_data:
                options = ['A', "B", 'C', 'D']
                markup = types.InlineKeyboardMarkup(row_width=2)
                for i in range(len(options)):
                    button = types.InlineKeyboardButton(options[i],
                                                        callback_data=f'answer_{next_question_num}_{i + 1}_{q_type}_{level}',
                                                        resize_keyboard=True)
                    markup.add(button)

                bot.send_message(chat_id, f"Вопрос {user_data['current_question']}")
                bot.send_photo(chat_id, photo=p(next_question_data['_id']), reply_markup=markup)
            else:
                bot.send_message(chat_id, "ошибка при выборе вопросов.")
            db.test.update_one({"user_id": chat_id},
                               {"$set": {"current_question": user_data.get("current_question") + 1}})



        elif (user_data.get(f"level_DS") == 2) and (user_data.get(f"level_DE") == 2) and (
                user_data.get("current_question") == 11):

            bot.send_message(chat_id, stats(chat_id, user_data, q_type, level))
            finish(chat_id, q_type)
            bot.send_message(chat_id, "Спасибо за участие!")
            db.test.update_one({"user_id": chat_id},
                               {"$set": {"current_question": user_data.get("current_question") + 1}})

        elif (user_data.get("current_question") == 8) and (user_data.get(f"level_{q_type}") == 1):

            bot.send_message(chat_id, stats(chat_id, user_data, q_type, level))

            db.test.update_one({"user_id": chat_id}, {"$set": {f"level_{q_type}": 2}})
            # db.test.update_one({"user_id": chat_id}, {"$set": {"current_question": 3}})

            #  начало второго уровня
            level = int(db.test.find_one({"user_id": chat_id}).get(f"level_{q_type}"))
            print(q_type, level)
            next_question_num = chek_next(chat_id, q_type, level)
            next_question_data = db.questions.find_one({"_id": next_question_num})

            if next_question_data:
                markup = types.InlineKeyboardMarkup(row_width=2)
                button = types.InlineKeyboardButton('Да',
                                                    callback_data=f'answer_{0}_{1}_{q_type}_{level}')
                markup.add(button)

            bot.send_message(chat_id, f"Переходим на второй уровень ?", reply_markup=markup)


        elif (user_data.get("current_question") == 11) and (user_data.get(f"level_{q_type}") == 2):

            db.answer.delete_one({
                'type': 'ask',
                'user_id': chat_id
            })
            bot.send_message(chat_id, stats(chat_id, user_data, q_type, level))

            res_level_1 = db.answer.count_documents(
                {"user_id": chat_id, "res": True, "type": f'ask_{q_type}', 'level': 1})
            res_level_2 = db.answer.count_documents(
                {"user_id": chat_id, "res": True, "type": f'ask_{q_type}', 'level': 2})
            if (res_level_1 > 4) and (res_level_2 > 0):
                finish(chat_id, q_type)
                bot.send_message(chat_id, "Спасибо за участие!")

            else:

                db.test.update_one({"user_id": chat_id},
                                   {"$set": {"current_question": user_data.get("current_question") + 1}})

                markup = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)

                if user_data.get('level_DE') == 2:


                    type_key = ("DS\n"
                                "(Data Science)")
                else:
                    type_key = ("DE\n"
                                "(Data Engineer)")

                block = types.KeyboardButton(f"{type_key}")
                markup.add(block)
                finish(chat_id, q_type)
                bot.send_message(chat_id, f'Попробуй свои силы в другом блоке:', reply_markup=markup)

                db.test.update_one({"user_id": chat_id},
                                   {"$set": {"status": 0}})
                db.test.update_one({"user_id": chat_id},
                                   {"$set": {"current_question": 1}})


        elif user_data.get("current_question") > 10:
            pass


@bot.message_handler(commands=['del'])
def del_db(message):
    chat_id = message.chat.id
    db.test.delete_many({"user_id": chat_id})
    db.answer.delete_many({"user_id": chat_id})
    db.temp_answer.insert_one(
        {"user_id": chat_id, "type": 'del', 'time': datetime.datetime.now().strftime('%H:%M:%S')})

    bot.send_message(message.chat.id, 'Успех!')




#
@bot.message_handler(commands=['png'])
def str_to_photos(message):
    fs = GridFS(client.testdata, collection="photos")
    res = db.questions.find({})
    for i in res:
        width, height = 600, 200
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        font = ImageFont.truetype("arial.ttf", 14)
        text_color = (0, 0, 0)
        text_position = (50, 50)

        formatted_question = f"{i['question']} :"
        formatted_answers = "\n".join([f"{chr(97 + i)}) {answer}" for i, answer in enumerate(i['options'])])
        formatted_text = f"{formatted_question}\n{formatted_answers}"
        draw.text(text_position, formatted_text, fill=text_color, font=font)

        img_io = io.BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

        fs.put(img_io, filename=i['_id'])
    bot.send_message(message.chat.id, 'Успех!')


#
if __name__ == "__main__":
    bot.polling(none_stop=True)