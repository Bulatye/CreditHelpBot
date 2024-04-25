import requests
import telebot
from telebot import types
import datetime  

import config
from data_strings import *

bot = telebot.TeleBot(config.TOKEN)
user_data = {}
counter_owners = 0
URL_credit_report = "https://credistory.ru/credithistory?utm_source=bki-okb.ru&utm_medium=referral&utm_campaign=site&utm_content=b2c_block&utm_term="

@bot.message_handler(commands=['start'])
def start(message):
    '''реагирует на команду start'''

    start_position(message)
    print(user_data)


def start_position(message):
    '''Выполняет стартовые действия. Написана отдельной функцией для того, чтобы вызывать из функций не позволяющих
    из-за своего потока принять команду декоратором'''

    user_data.clear()
    img = open("greetings.jpg", 'rb')
    bot.send_photo(message.chat.id, img, greetings_text.format(message.from_user.first_name))
    bot.register_next_step_handler(message, process_phone_step) # process_phone_step
    img.close()


def check_content_type(message, type):
    '''проверят тип контента в message
    обрабатываем только сообщения с типом данных текст'''

    if message.content_type != type:
        return False
    return True


def check_command_start(message):
    '''Проверят команду /start'''
    # если пользователь вводит команду старт, переводим его на стартовую функцию
    if message.text == "/start":
        start_position(message)
        return False
    return True


def process_message_step(message, message_text, callback):
    '''Выводит сообщение и переводит на определенную функцию.'''
    # логирование
    log_bot(message, message.text)
    bot.send_message(message.chat.id, message_text)
    bot.register_next_step_handler(message, callback)


def process_message_markup(message, message_text, amount, *args):
    '''Выводит сообщение, callback кнопки.'''
    # логирование
    log_bot(message, message.text)

    markup = types.InlineKeyboardMarkup()

    for i in range(amount):
        markup.add(types.InlineKeyboardButton(args[i], callback_data=args[i]))

    bot.send_message(message.chat.id, text=message_text, reply_markup=markup)



def download_document(message):
    '''cкачивает документ локально'''
    file_info = bot.get_file(message.document.file_id)

    downloaded_file = bot.download_file(file_info.file_path)
    src = message.document.file_name

    with open('data/' + src, 'wb') as new_file:
        new_file.write(downloaded_file)

    return src


def download_photo(message):
    '''cкачивает фото локально'''
    photo = message.photo[-1]
    file_info = bot.get_file(photo.file_id)
    file_path = file_info.file_path

    # Формируем URL для загрузки фото
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

    # Получаем настоящее имя файла
    real_file_name = file_path.split('/')[-1]

    # Скачиваем и сохраняем фото с его настоящим именем файла
    with open('data/' + real_file_name, "wb") as file:
        file.write(requests.get(photo_url).content)

    return real_file_name


def log_bot(message, text):
    now = datetime.datetime.now()
    date_only = now.strftime("%Y-%m-%d-%H-%M")
    print(f"Имя:{message.from_user.first_name} время: {date_only} введенные данные: {text}")


def process_phone_step(message):
    '''проверяет корректность ввода телефона, выводит текст в чат
    с просьбой ввести фио'''
    if user_data == {}:
        start_position(message)

    if check_content_type(message, "text"):
        if not check_command_start(message):
            return None
        # производим проверку корректности введенного текста
        phone = list(message.text)
        if len(message.text) == 12 and phone[0] == "+":
            # выводим следующее сообщение, переводим на следующий шаг
            process_message_step(message, get_FIO_text, process_fio_step)
        
            user_data["phone"] = message.text
            return None
    # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
    process_message_step(message, error_input_phone_text, process_phone_step)


def process_fio_step(message):
    '''обработка фио, запрос лица'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "text"):
        if not check_command_start(message):
            return None

        # Проверка на наличие цифр в введенных данных.
        for i in message.text:
            if not i.isdigit():
                process_message_step(message, "В ФИО не должно быть цифр!", process_inn_step)
                return None

        # удаляем возможные пробелы в начале и конце строки и формируем список
        list_message_FIO = message.text.strip(' ').split(' ')

        # производим проверку корректности введенного текста
        if len(list_message_FIO) == 3:
            # запрашиваем лицо
            process_message_markup(message, choose_face, 3, *face_arr)
            user_data["FIO"] = message.text
            return None
    # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
    process_message_step(message, error_FIO, process_fio_step)


@bot.callback_query_handler(func=lambda c: c.data in face_arr)
def process_face_step(callback):
    '''обработка лица, запрашиваем инн'''
    if user_data == {}:
        start_position(callback.message)
        return None

    user_data["face"] = callback.data
    process_message_step(callback.message, inn_text, process_inn_step)



def process_inn_step(message):
    '''обработка инн, запрос снилс'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "text"):
        if not check_command_start(message):
            return None

        for i in message.text:
            if not i.isdigit() or len(message.text) != 12:
                process_message_step(message, inn_error_text, process_inn_step)
                return None

        user_data["inn"] = message.text
        process_message_step(message, snils_text, process_snils_step)
    else:
        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_inn_step)



def process_snils_step(message):
    '''Обрабатываем текст снилса, запрашиваем ввод региона'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "text"):
        if not check_command_start(message):
            return None

        for i in message.text:
            if not i.isdigit() or len(message.text) != 11:
                process_message_step(message, snils_error_text, process_snils_step)
                return None

        user_data["snils"] = message.text
        process_message_step(message, region_text, peocess_region_step)
    else:
        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_snils_step)



def peocess_region_step(message):
    '''обработка региона, запрашиваем сумму кредита'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "text"):
        if not check_command_start(message):
            return None

        if len(message.text) > 1 and not any(char.isdigit() for char in message.text):
            user_data['region'] = message.text
            process_message_markup(message, choose_face, 4, *credit_sums)
            return None

    # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
    process_message_step(message, error_text, peocess_region_step)



@bot.callback_query_handler(func=lambda c: c.data in credit_sums)
def process_sum_step(callback):
    '''обработка суммы, запрашиваем фото паспорта'''
    if user_data == {}:
        start_position(callback.message)
        return None

    user_data["credit_sum"] = callback.data
    process_message_step(callback.message, pasport_text, process_passport_step)


def process_passport_step(message):
    '''обработка фото пасспорта, запрашиваем кредитный отчет'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "photo"):

        try:
            user_data["photo_passport"] = download_photo(message)
            
            # запрашивае данные кредитного отчета
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Сервис для получения кредитного отчета", url=URL_credit_report))

            bot.send_message(message.chat.id, text=credit_report_text, reply_markup=markup)
            bot.register_next_step_handler(message, process_credit_report_step)


        except Exception as e:
            process_message_step(message, error_text, process_passport_step)

    else:
        if not check_command_start(message):
            return None

        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_passport_step)



def process_credit_report_step(message):
    '''обработка кредитного отчета, запрашиваем продукт'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "document"):
        try:
            user_data["credit_report"] = download_document(message)
            process_message_markup(message, choose_product_text, 1, "Кредит")

        except Exception as e:
            process_message_step(message, error_text, process_credit_report_step)

    else:
        if not check_command_start(message):
            return None
        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_credit_report_step)


@bot.callback_query_handler(func=lambda c: c.data == 'Кредит')
def process_product_step(callback):
    '''обработка продукта'''
    if user_data == {}:
        start_position(callback.message)
        return None

    user_data["service"] = 'Кредит'

    # если пользователь физ. лицо, проводим его по первой ветке
    if user_data["face"] == face_arr[0]:
        process_message_markup(callback.message, family_status, 2, *families_status_arr)
    # если пользователь юр. лицо или ооо, проводим его по второй ветке
    elif user_data["face"] == face_arr[1] or user_data["face"] == face_arr[2]:
        process_message_step(callback.message, bank_statement_text, process_bank_statement)


@bot.callback_query_handler(func=lambda c: c.data in families_status_arr)
def process_family_status(callback):
    '''обработка семейного статуса, запрашиваем справку с места работы'''
    if user_data == {}:
        start_position(callback.message)
        return None

    user_data["family_status"] = callback.data

    process_message_step(callback.message, certificate_work, proccess_certificate_work)




def proccess_certificate_work(message):
    '''Обработка справки с места работы, выводим сообщение об окончании ввода данных'''
    if user_data == {}:
        start_position(message)
        return None

    try:
        if check_content_type(message, "document"):
            user_data["certificate_work"] = download_document(message)
            
            # конечный шаг пользовательского ввода
            # выводим сообщение с просьбой ожидания обработки введенных данных
            bot.send_message(message.chat.id, end_text)

            # результирующий набор данных
            for key, value in user_data.items():
                print("{0}: {1}".format(key,value))
        
            
            # логирование
            log_bot(message, message.text)

        elif check_content_type(message, "photo"):
            user_data["certificate_work"] = download_photo(message)

            # конечный шаг пользовательского ввода
            # выводим сообщение с просьбой ожидания обработки введенных данных
            bot.send_message(message.chat.id, end_text)

            # результирующий набор данных
            for key, value in user_data.items():
                print("{0}: {1}".format(key,value))
            
        elif not check_command_start(message):
            return None

        else:
            print("not doc and photo")
            # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
            process_message_step(message, file_certificate_work_error, proccess_certificate_work)

    except Exception as es:
        process_message_step(message, file_certificate_work_error, proccess_certificate_work)


def process_bank_statement(message):
    '''Обработка выписки с счета, спрашиваем о наличии задолжности'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "document"):
        try:
            user_data["bank_statement"] = download_document(message)
            process_message_markup(message, debt_text, 2, *debt_arr)

        except Exception as e:
            process_message_step(message, error_text, process_bank_statement)
    else:
        if not check_command_start(message):
            return None
        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_bank_statement)


@bot.callback_query_handler(func=lambda c: c.data in debt_arr)
def proccess_debt_step(callback):
    '''обработка наличия заложности, запрашиваем выписку 1с'''
    if user_data == {}:
        start_position(callback.message)
        return None

    user_data["debt"] = callback.data

    process_message_markup(callback.message, extract_1s_text, 2, *extract_1s_arr)


@bot.callback_query_handler(func=lambda c: c.data in extract_1s_arr)
def process_extract_1s(callback):
    '''обработка выписки 1с и текст завершения'''
    if user_data == {}:
        start_position(callback.message)
        return None

    if callback.data == extract_1s_arr[0]:
        process_message_step(callback.message, extract_1s_file_text, process_extract_1s_file)
    elif callback.data == extract_1s_arr[1]:
        user_data["extract_1s"] = extract_1s_arr[1]

        # спрашиваем является ли человек единственным учредителем
        process_message_markup(callback.message, ooo_answer_text, 2, *ooo_answer_arr)

        if user_data["face"] == "OOO":
            # спрашиваем является ли человек единственным учредителем
            process_message_markup(callback.message, ooo_answer_text, 2, *ooo_answer_arr)


def process_extract_1s_file(message):
    '''Скачивание 1с файла'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "document"):
        try:
            user_data["extract_1s"] = download_document(message)

            if user_data["face"] == "ИП":
                # конечный шаг пользовательского ввода
                # выводим сообщение с просьбой ожидания обработки введенных данных
                bot.send_message(message.chat.id, end_text)

                # результирующий набор данных
                for key, value in user_data.items():
                    print("{0}: {1}".format(key,value))

            elif user_data["face"] == "ООО":
                # спрашиваем является ли человек единственным учредителем
                process_message_markup(message, ooo_answer_text, 2, *ooo_answer_arr)

        except Exception as e:
            print(e)
            process_message_step(message, error_text, process_extract_1s_file)
    else:
        if not check_command_start(message):
            return None
        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_extract_1s_file)


@bot.callback_query_handler(func=lambda c: c.data in ooo_answer_arr)
def proccess_debt_step(callback):
    '''обработка вопроса о кол-ве учредителей'''
    print(user_data)
    if user_data == {}:
        start_position(callback.message)
        return None

    if callback.data == ooo_answer_arr[0]:

        # конечный шаг пользовательского ввода
        # выводим сообщение с просьбой ожидания обработки введенных данных
        bot.send_message(callback.message.chat.id, end_text)

        # результирующий набор данных
        for key, value in user_data.items():
            print("{0}: {1}".format(key,value))

        user_data["count_owners"] = 1
    elif callback.data == ooo_answer_arr[1]:
        process_message_step(callback.message, ooo_count_owners, process_count_owners)


def process_count_owners(message):
    '''Обработка количества учредителей, запрашиваем фамилии каждого из них'''
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "text"):
        if not check_command_start(message):
            return None

        for i in message.text:
            if not i.isdigit() or len(message.text) > 2 :
                process_message_step(message, inn_error_text, process_inn_step)
                return None

        user_data["count_owners"] = int(message.text)
        # Просим ввести фио каждого учредитея
        
        bot.send_message(message.chat.id, f"{ooo_fio_owner} 1")
        bot.register_next_step_handler(message, process_fio_owner)

    else:
        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_count_owners)


def process_fio_owner(message):
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "text"):
        if not check_command_start(message):
            return None

        # Проверка на наличие цифр в введенных данных.
        for i in message.text:
            if not i.isdigit():
                process_message_step(message, "В ФИО не должно быть цифр!", process_inn_step)
                return None

        global counter_owners 

        if (counter_owners < user_data["count_owners"]):
            print(counter_owners)
            fio_list = message.text.split()

            if len(fio_list) != 3:
                # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
                process_message_step(message, f"{error_FIO_owner} {ooo_fio_owner} {counter_owners + 1}", process_fio_owner)
                return None

            if "fio_owners" not in user_data.keys():
                user_data["fio_owners"] = list()

            user_data["fio_owners"].append(message.text)
          

            counter_owners += 1

            if counter_owners < user_data["count_owners"]:
                bot.send_message(message.chat.id, f"{ooo_fio_owner} {counter_owners + 1}")
            else:
                process_message_step(message, ooo_data_partner, process_data_partner)
                print(user_data["fio_owners"])
                user_data["count_owners"] = len(user_data["fio_owners"])
                counter_owners = 0
                return None

            bot.register_next_step_handler(message, process_fio_owner)


def process_data_partner(message):
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "document"):
        try:
            user_data["data_partner"] = download_document(message)
            bot.send_message(message.chat.id, f"{credit_report_parnter} 1 в формате pdf")
            bot.register_next_step_handler(message, process_credit_report_parnters)

        except Exception as e:
            print(str(e))
            process_message_step(message, error_text, process_data_partner)
    else:
        if not check_command_start(message):
            return None
        print("fuck")
        # Выводим сообщение об ошибке если условия оказалось ложными, запускаем функцию повторно
        process_message_step(message, error_text, process_data_partner)


def process_credit_report_parnters(message):
    if user_data == {}:
        start_position(message)
        return None

    if check_content_type(message, "document"):
        if not check_command_start(message):
            return None

        global counter_owners

        if (counter_owners < user_data["count_owners"]):

            try:
                if "credit_report_parnters" not in user_data.keys():
                    user_data["credit_report_parnters"] = list()

                user_data["credit_report_parnters"].append(download_document(message))

                counter_owners += 1
                if (counter_owners < user_data["count_owners"]):
                    bot.send_message(message.chat.id, f"{credit_report_parnter} {counter_owners + 1} в формате pdf")
                    bot.register_next_step_handler(message, process_credit_report_parnters)
                else:
                    # конечный шаг пользовательского ввода
                    # выводим сообщение с просьбой ожидания обработки введенных данных
                    bot.send_message(message.chat.id, end_text)
                    # результирующий набор данных
                    for key, value in user_data.items():
                        print("{0}: {1}".format(key,value))
                    counter_owners = 0

            

            except Exception as e:
                process_message_step(message, error_text, process_credit_report_parnters)
            
    else:
        process_message_step(message, error_text, process_credit_report_parnters)


bot.polling(none_stop=True)
