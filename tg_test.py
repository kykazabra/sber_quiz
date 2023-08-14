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

uri = "mongodb+srv://olok1:utofir33@cluster0.lfjwngi.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, server_api=ServerApi('1'))
TOKEN = "5393815864:AAHnIC9LULP5rltphCzMDG40h9T-vwyFUAY"
bot = telebot.TeleBot(TOKEN)

db = client.testdata
coll = db.test

def chek_next(category):
    num = [i['_id'] for i in db.questions.find({"category": category})]
    num_2 = [i['question_id'] for i in db.answer.find({'type':"ask"})]
    choice  = random.choice(list(set(num) - set(num_2)))

    return choice





def stats(chat_id):
    correct_answers = db.answer.count_documents({"user_id": chat_id, "res": True})
    total_questions = db.answer.count_documents({"user_id": chat_id, "type": 'ask'})

    time = []
    for i in db.answer.find({'user_id': chat_id}):
        time.append(i['time'])

    time_start = (datetime.datetime.strptime((time[0]), '%H:%M:%S'))
    time_end = (datetime.datetime.strptime((time[-1]), '%H:%M:%S'))

    times = time_end - time_start

    result_message = f"Всего вопросов: {total_questions}\n"
    result_message += f"Отвечено правильно: {correct_answers}\n"
    result_message += f"Время : {times}\n"
    return result_message






@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data = db.test.find_one({"user_id": chat_id})

    if not user_data:
        #db.test.insert_one({"user_id": chat_id, "current_question": 1, "level": 1, "answers": {}})
        db.test.insert_one({"user_id": chat_id, "current_question": 1, "level_DS": 1,"level_DE": 1})
        db.answer.insert_one({"user_id": chat_id, "type" : 'start_1','time':datetime.datetime.now().strftime('%H:%M:%S')})

        markup = types.ReplyKeyboardMarkup(row_width=2)
        DS = types.KeyboardButton("DS")
        DE = types.KeyboardButton("DE")
        markup.add(DS, DE)
        bot.send_message(chat_id, "Выберите блок:", reply_markup=markup)

    elif user_data.get('level_DS') == 2:

        markup = types.ReplyKeyboardMarkup(row_width=1)
        DE = types.KeyboardButton("DE")
        markup.add(DE)
        bot.send_message(chat_id, "Выберите блок:", reply_markup=markup)

    elif user_data.get('level_DE') == 2:

        markup = types.ReplyKeyboardMarkup(row_width=1)
        DS = types.KeyboardButton("DS")
        markup.add(DS)
        bot.send_message(chat_id, "Выберите блок:", reply_markup=markup)


    else:
        print()


#
@bot.message_handler(func=lambda message: message.text in ["DS", "DE"])
def handle_direction(message):
    chat_id = message.chat.id
    user_data = db.test.find_one({"user_id": chat_id})
    q_type = message.text
    db.answer.insert_one({"user_id": chat_id, 'type': f"{q_type}_level_1",'time': datetime.datetime.now().strftime('%H:%M:%S') })


    if user_data.get("current_question") < 5:

        question_num = user_data.get("current_question", 0)
        question_data = db.questions.find_one({"_id": chek_next(q_type)})
        #question_data = chek_next(q_type)


        if question_data:
            options = question_data['options']
            markup = types.InlineKeyboardMarkup(row_width=2)
            for i in range(len(options)):
                #button = types.InlineKeyboardButton(options[i], callback_data=f'answer_{question_num}_{i + 1}')
                button = types.InlineKeyboardButton(options[i], callback_data=f'answer_{question_num}_{i + 1}_{q_type}')
                markup.add(button)

            question = question_data['question']
            bot.send_message(chat_id,f"Вопрос {user_data['current_question']} \n{question}" , reply_markup= markup)
            #bot.send_message(chat_id, f"Вопрос {user_data['current_question']}")
            #bot.send_photo(chat_id, photo=photo(question_data['png']), reply_markup= markup)

        else:
            bot.send_message(chat_id, "Произошла ошибка при выборе вопросов.")

        db.test.update_one({"user_id": chat_id},
                           {"$set": {"current_question": question_num + 1}})

    else:
        bot.send_message(chat_id, "Вы уже ответили на все вопросы.")


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.message:
        chat_id = call.message.chat.id
        user_data = db.test.find_one({"user_id": chat_id})
        #print(user_data)

        parts = call.data.split("_")
        print(parts)
        question_num = int(parts[1])
        selected_answer = int(parts[2])
        q_type = parts[3]
        print(q_type)
        true_answer = db.questions.find_one({"_id": question_num}).get('correct_answer')
        res = selected_answer == true_answer


        db.answer.insert_one({"user_id": chat_id, 'question_id': question_num,
                              "selected_answer": selected_answer, "true_answer": true_answer, 'res': res,
                              'type':'ask','time':datetime.datetime.now().strftime('%H:%M:%S')})

        if user_data.get("current_question") < 5 + 1 :
            #next_question_num = user_data.get("current_question") + 1
            next_question_num = chek_next(q_type)

            next_question_data = db.questions.find_one({"_id": next_question_num})



            if next_question_data:
                options = next_question_data['options']
                markup = types.InlineKeyboardMarkup(row_width=2)
                for i in range(len(options)):
                    button = types.InlineKeyboardButton(options[i],
                                                        callback_data=f'answer_{next_question_num}_{i + 1}_{q_type}')
                    markup.add(button)

                question = next_question_data['question']

                bot.send_message(chat_id, f"Вопрос {user_data['current_question']} \n{question}", reply_markup=markup)


            else:
                bot.send_message(chat_id, "ошибка при выборе вопросов.")


            db.test.update_one({"user_id": chat_id},
                               {"$set": {"current_question": user_data.get("current_question") + 1}})

        elif (user_data.get("current_question") == 6) and (user_data.get(f"level_{q_type}") == 1 ):


            bot.send_message(chat_id, stats(chat_id))

            db.test.update_one({"user_id": chat_id}, {"$set": {f"level_{q_type}": 2}})
            db.test.update_one({"user_id": chat_id}, {"$set": {"current_question": 1}})
            db.answer.delete_many({'type': 'ask'})

            #  начало второго уровня
            next_question_num = chek_next(q_type)
            next_question_data = db.questions.find_one({"_id": next_question_num})

            if next_question_data:
                markup = types.InlineKeyboardMarkup(row_width=2)
                button = types.InlineKeyboardButton('Да',
                                                     callback_data=f'answer_{next_question_num}_{1}_{q_type}')
                markup.add(button)


            bot.send_message(chat_id, f"Переходим на второй уровень ?", reply_markup=markup)

        elif (user_data.get("current_question") == 6) and (user_data.get(f"level_{q_type}") == 2):

            bot.send_message(chat_id, stats(chat_id))
            bot.send_message(chat_id,f'Поздравляю, ты прошел блок {q_type}')

            db.test.update_one({"user_id": chat_id},
                               {"$set": {"current_question": user_data.get("current_question") + 1}})



        elif user_data.get("current_question") > 6:
            print()


@bot.message_handler(commands=['del'])
def del_db(message):
    find = db.test.find_one({"current_question": {'$gt': 0}})['current_question']

    db.test.delete_many({"current_question": find})
    db.answer.delete_many({})

    bot.send_message(message.chat.id, 'Успех!')

@bot.message_handler(commands=['png'])
def png(message):
    source_collection = db['questions']


    text = source_collection.find()#['question']
    for i in text:

        width, height = 500, 100
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        font = ImageFont.truetype("arial.ttf", 14)
        text_color = (0, 0, 0)
        text_position = (50, 50)
        draw.text(text_position, i['question'], fill=text_color, font=font)

        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_data = image_buffer.getvalue()


        source_collection.update_many({"_id": i['_id']},
                           {"$set": {"png": image_data}})
    bot.send_message(message.chat.id, 'Успех!')


if __name__ == "__main__":
    bot.polling(none_stop=True)