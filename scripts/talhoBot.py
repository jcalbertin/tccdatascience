#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import json

import telebot
from environs import Env
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import types

from scripts.classes.Choice import Choice
from scripts.classes.text_to_speak import TextToSpeak
from scripts.classes.options_menu import options_bovino, options_aves, options_suinos

# import environment variables
env = Env()
env.read_env()

telegram_token = env("TELEGRAM_TOKEN_API")
download_path = env("DOWNLOAD_PATH")
bot_name = "Talho"
message_step_one = "O que vai querer? (Escolha a opção ou digite pelo código)"
cart = []
current_interaction = None

# logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
log = logging.getLogger(__name__)

bot = telebot.TeleBot(telegram_token)


def main_option_keyboard_markup(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("Aves", callback_data=json.dumps({"step": "main", "option": "AVES", "id": chat_id})),
        InlineKeyboardButton("Bovinos", callback_data=json.dumps({"step": "main", "option": "BOVINOS", "id": chat_id})),
        InlineKeyboardButton("Suínos", callback_data=json.dumps({"step": "main", "option": "SUINOS", "id": chat_id})),
        InlineKeyboardButton("Sugestões", callback_data=json.dumps({"step": "main", "option": "SUGESTOES", "id": chat_id})),
        InlineKeyboardButton("Info", callback_data=json.dumps({"step": "main", "option": "INFO", "id": chat_id})),
        InlineKeyboardButton("Encerrar", callback_data=json.dumps({"step": "main", "option": "ENCERRAR", "id": chat_id}))
    )
    return markup


@bot.message_handler(commands=['start', 'help'])
def message_start(message):
    welcome(message)


@bot.message_handler(func=lambda message: True)
def message_handler(message):
    if current_interaction is None:
        welcome(message)
    else:
        log.warning("repass to handle for current interation {0} ...". format(current_interaction))
        interaction_handle(message, current_interaction)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    choice = json.loads(call.data)
    global current_interaction
    current_interaction = choice
    interaction_handle(call, choice)


def interaction_handle(call, choice):
    global current_interaction
    if choice["step"] == "main":
        if choice["option"] == "AVES":
            # bot.answer_callback_query(call.id, call.data)
            create_submenu(message_step_one, choice, options_aves, "aves")
        elif choice["option"] == "BOVINOS":
            create_submenu(message_step_one, choice, options_bovino, "bovinos")
        elif choice["option"] == "SUINOS":
            create_submenu(message_step_one, choice, options_suinos, "suinos")
        elif choice["option"] == "SUGESTOES":
            sugestoes_menu(choice)
        elif choice["option"] == "INFO":
            info_menu(choice)
        else:  # encerrar
            encerrar_menu(choice)
    elif choice["step"] in ("aves", "bovinos", "suinos"):
        if choice["option"] == "INITIAL":
            message = call.json
            log.warning(message["text"])
        elif choice["option"] == "QTDE":
            log.info("Qtde digitada: {0}".format(call.json["text"]))
            pass
        else: # handle for submenu
            current_interaction = {"step": choice["step"], "option": "QTDE", "id": choice["id"]}
            markup = types.ForceReply(selective=False)
            bot.send_message(choice["id"], "Digite a quantidade em kg:", reply_markup=markup)

    else:
        print("no step configured ....")




@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    # this is the standard reply to a normal message
    bot.send_message(m.chat.id, "I don't understand \"" + m.text + "\"\nMaybe try the help page at /help")

@bot.message_handler(content_types=['document', 'audio', 'voice'])
def handle_docs_audio(message):
    try:
        log.warning(message)

        if (message.content_type == 'voice') or (message.content_type == 'audio'):
            log.warning(message.voice)
            file_id = message.voice.file_id
            file_info = bot.get_file(file_id)
            bot.send_message(message.chat.id, file_info)
            downloaded_file = bot.download_file(file_info.file_path)

            if not os.path.exists(download_path):
                os.mkdir(download_path)

            filename = "./" + download_path + "/audio_" + str(message.chat.id) + str(message.from_user.id) + ".ogg"
            with open(filename, 'wb') as new_file:
                new_file.write(downloaded_file)

            bot.send_message(message.chat.id, "Você enviou um áudio ou voz")
    except Exception as inst:
        log.error("Error in handle_docs_audio {0}".format(inst.args))


def create_submenu(message, choice, options, step_name):
    log.info("creating submenu: " + str(choice))
    bot.send_message(choice["id"],
                     message,
                     reply_markup=create_option_menu_markup(choice["id"], options, step_name))


def info_menu(choice):
    bot.send_message(choice["id"], "Horário de funcionamente: ")


def sugestoes_menu(choice):
    bot.send_message(choice["id"], "Escreva aqui suas sugestões!")


def fechar_menu(choice):
    bot.send_message(choice["id"], "Pedido enviado!")
    cart = []


def encerrar_menu(choice):
    bot.send_message(choice["id"], "Volte sempre!")
    cart = []


def quantidade(choice):
    bot.send_message(choice["id"], "Digite a quantidade que deseja:")


def create_option_menu_markup(chat_id, options, step_name):
    log.info("creating {0} menu markup ...".format(step_name))
    global current_interaction

    markup = InlineKeyboardMarkup(row_width=1)
    for option in options:
        if option["type"] == "instructions":
            bot.send_message(chat_id, option["text"])
        elif option["type"] in ("item", "action"):
            step = {"step": step_name, "option": option['option'], "id": chat_id}
            if option["code"] == "-1":
                markup.add(
                    InlineKeyboardButton(
                        option["description"],
                        callback_data=json.dumps(step))
                )
            else:
                markup.add(
                    InlineKeyboardButton("{0} - {1} - R$ {2}".format(option["code"], option["description"], option["price"]), callback_data=json.dumps(step))
                )
    current_interaction = {"step": step_name, "option": "INITIAL", "id": chat_id}
    return markup


def welcome(message):
    log.debug(message)
    chat_id = message.chat.id
    log.info(message.from_user)
    bot.send_chat_action(chat_id, "typing")
    user_message = "Olá {user_name}".format(user_name=message.from_user.first_name)
    bot.send_message(chat_id, user_message)
    welcome_message = "Meu nome é {bot}, serei seu assistente virtual." \
                      "O quê deseja pedir?".format(bot=bot_name)

    speak = TextToSpeak()
    speak.set_voice(speak.get_available_voice())
    converted_audio = speak.save_voice_to_file(welcome_message, "./audio.out", "./audio.ogg", "ogg")

    bot.send_chat_action(chat_id, "record_audio")
    bot.send_voice(chat_id, open(converted_audio, "rb"))
    bot.send_message(chat_id, welcome_message, reply_markup=main_option_keyboard_markup(chat_id))


bot.polling(none_stop=True, interval=0, timeout=60)
