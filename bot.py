from datetime import datetime
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler
import logging
import os
import cv2
import serial
import json
import pandas as pd
from PIL import Image

# read access token
with open(r'data/token.txt') as f:
    token = f.read()
bot = Bot(token=token)
ADMIN_ID = 116642584  # my own user id

# connect to printer
global printer
# pi: '/dev/ttyUSB0'
# local: 'COM7 / COM9'
printer = serial.Serial(port='/dev/ttyUSB0',
                        baudrate=19200)

updater = Updater(token=token, use_context=True)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


datapath = r'data/data.json'

global data
try:
    with open(datapath) as data_file:
        data = json.load(data_file)
except FileNotFoundError:
    logging.info("data.json file not found. Creating the file.")
    data = {}
    data['total_prints'] = 0
    data['text_prints'] = 0
    data['image_prints'] = 0
    data['contact_prints'] = 0
    data['poll_prints'] = 0
    data['location_prints'] = 0
    data['users'] = []

    with open(datapath, 'w') as data_file:
        json.dump(data, data_file)


def store_data():
    """Store data to json file"""
    with open(datapath, 'w') as data_file:
        json.dump(data, data_file)


def user_info(telegram_user):
    """Return username and permission to print"""
    for user in data['users']:
        if user['id'] == telegram_user.id:
            # If username is changed, update the settings
            first_name, last_name = get_full_name(telegram_user)
            if "{} {}".format(first_name, last_name) != user['name']:
                user['name'] = "{} {}".format(first_name, last_name)
                store_data()
            # Return username and permission to print
            if user['anonymous']:
                return "Anonymous", user['permission_to_print']
            else:
                return user['name'], user['permission_to_print']


def get_full_name(telegram_user):
    """Get a user's full name."""
    # Get user's name
    if telegram_user['first_name'] is not None:
        first_name = telegram_user['first_name']
    else:
        first_name = ''
    if telegram_user['last_name'] is not None:
        last_name = telegram_user['last_name']
    else:
        last_name = ''
    if first_name == '' and last_name == '':
        first_name = 'Anonymous'

    return first_name, last_name


def cmd_start(update: Update, context: CallbackContext):
    """Send welcome message."""
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Send any text (no images) to be printed :D")
    # context.bot.send_message(chat_id=update.effective_chat.id, text="Asking Micha to grant you permission...")

    # Add user to list of users
    if update.message.from_user['id'] in [user['id'] for user in data['users']]:
        update.message.reply_text("You are already registered.")
    else:
        data['users'].append({
            'username': update.message.from_user.username,
            'name': "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name),
            'id': update.message.from_user.id,
            'is_admin': False,
            'permission_to_print': True,  # WIP, add manual user permission
            'time_of_last_message': datetime.now().replace(year=1970).isoformat(),
            'anonymous': False})
        store_data()


# Set global variables
# max message length is automatically controlled with Telegram's max message length & anti spam function.
MIN_MSG_INTERVAL_SEC = 2  # minimum seconds between two messages


# Printing Code


def cut(prntr):
    '''
    Cut bonnetje.
    '''

    prntr.write(b'\033d0')


def write_markup(prntr, msg):
    '''
    Write intro text to bonnetje.
    '''

    # Get user's name
    first_name, last_name = get_full_name(msg.from_user)
    name = (first_name + ' ' + last_name).encode()

    # Current Time:
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S').encode()

    # Text
    # text = msg.text.encode()

    prntr.write('Message sent at:'.encode() +
                time_now +
                '\n'.encode() +
                'From User: '.encode() +
                name +
                '\n\n'.encode())


def write_text(prntr, msg):
    """
    Writes main text to bonnetje.
    """
    text = msg.text.encode()
    prntr.write(text)
    prntr.write('\n\n\n\n\n\n\n\n'.encode())


def write_img(prntr, msg):
    """
    (WIP) Write images to bonnetje.
    """
    return


def print_text(update: Update, context: CallbackContext):
    """Print anything a user sends"""

    # Check if user is not sending spam
    # for user in data['users']:
    #     if user['id'] == update.message.from_user.id:
    #         if int((datetime.now() - datetime.fromisoformat(user['time_of_last_message'])).seconds) < MIN_MSG_INTERVAL_SEC:
    #             update.message.reply_text(
    #                 "You are sending messages to fast. Please wait {} seconds.".format(MIN_MSG_INTERVAL_SEC))
    #             return

    # Check if user has pressed /start yet
    if update.message.from_user['id'] not in [user['id'] for user in data['users']]:
        update.message.reply_text(
            "Send the command '/start' to start before sending messages.")
        return

    # Check if user has permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        update.message.reply_text(
            "You are not allowed to print, request permission with /start")
        return

    else:
        try:
            for user in data['users']:
                if user['id'] == update.message.from_user.id:
                    user['time_of_last_message'] = datetime.now().isoformat()
            write_markup(printer, update.message)  # send text to bonnenprinter
            write_text(printer, update.message)
            cut(printer)  # cut bonnetje
            # close(printer)  # close printer
            update.message.reply_text('Bonnetje has been printed!')
        except:
            update.message.reply_text(
                'Something has gone wrong. Please try sending a bonnetje later, or poke Micha @Stoel.')


def print_image(update: Update, context: CallbackContext):
    '''
    Command: Print image to bonnetje.
    '''

    # Check if user is not sending spam
    for user in data['users']:
        if user['id'] == update.message.from_user.id:
            if int((datetime.now() - datetime.fromisoformat(user['time_of_last_message'])).seconds) < MIN_MSG_INTERVAL_SEC:
                update.message.reply_text(
                    "You are sending messages to fast. Please wait {} seconds.".format(MIN_MSG_INTERVAL_SEC))
                return

    # Check if user has pressed /start yet
    if update.message.from_user['id'] not in [user['id'] for user in data['users']]:
        update.message.reply_text(
            "Send the command '/start' to start before sending messages.")
        return

    # Check if user has permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        update.message.reply_text(
            "You are not allowed to print, request permission with /start")
        return

    else:
        try:
            for user in data['users']:
                if user['id'] == update.message.from_user.id:
                    user['time_of_last_message'] = datetime.now().isoformat()

            # Process image
            image = context.bot.get_file(
                update.message.photo[-1].file_id).download()
            img = Image.open(image).convert('L')
            # scale image to width of bonnetje.
            wpercent = (512/float(img.size[0]))
            hsize = int((float(img.size[1])*float(wpercent)))
            img = img.resize((512, hsize))

            write_markup(printer, update.message)

            # Write image
            for i in range(img.size[0]):
                for j in range(img.size[1]):
                    printer.write(img.getpixel((i, j)).to_bytes(1, 'little'))
                printer.write('\r\n'.encode())

            # Check for caption
            if update.message.caption != None:
                write_text(update.message.caption)

            cut(printer)  # cut bonnetje

            # close(printer)  # close printer
            update.message.reply_text('Bonnetje has been printed!')
        except:
            update.message.reply_text(
                'Something has gone wrong. Please try sending a bonnetje later, or poke Micha @Stoel.')


def close(prntr):
    prntr.close()


dispatcher.add_handler(CommandHandler('start', cmd_start))
# dispatcher.add_handler(CallbackQueryHandler(callback_query_handler))
# CommandHandlers: boodschappenlijstje
# dispatcher.add_handler(CommandHandler('add', boodschap))
# dispatcher.add_handler(CommandHandler('print', print_list))
# dispatcher.add_handler(CommandHandler('remove_all', empty_list))
# dispatcher.add_handler(CommandHandler('remove', remove_one))

# MessageHandlers: to print bonnetjes
dispatcher.add_handler(MessageHandler(
    Filters.text & ~Filters.command, print_text))
dispatcher.add_handler(MessageHandler(
    Filters.photo & ~Filters.command, print_image))

updater.start_polling()
updater.idle()

# Check if user is admin
# def user_is_admin(user_id):
#     """Check if user is the admin"""
#     if int(user_id) == ADMIN_ID:
#         return True
#     else:
#         return False

# Buttons for User Permission
# USER_GRANTED = 'user_granted'
# yes_button = InlineKeyboardButton(
#     text='Yes',  # text that show to user
#     callback_data=USER_GRANTED  # text that send to bot when user tap button
# )

# USER_DISMISSED = 'user_dismissed'
# no_button = InlineKeyboardButton(
#     text='No',  # text that show to user
#     callback_data=USER_DISMISSED  # text that send to bot when user tap button
# )

# Handle Query for User Permissions
# def callback_query_handler(update: Update, context: CallbackContext):
#     cq = update.callback_query
#     cq.answer()

#     cqd = cq.data
#     if cqd == USER_GRANTED:
#         for user in data['users']:
#             if user['id'] == int(context.user_data['id']):
#                 user['permission_to_print'] = True
#                 if user_is_admin(context.user_data['id']):
#                     user['is_admin'] = True
#                 else:
#                     user['is_admin'] = False
#                 context.bot.send_message(
#                     user['id'], "You now have permission to print :D")
#                 store_data()
#                 break
#     elif cqd == USER_DISMISSED:
#         for user in data['users']:
#             if user['id'] == int(context.user_data['id']):
#                 user['permission_to_print'] = False
#                 if user_is_admin(context.user_data['id']):
#                     user['is_admin'] = True
#                 else:
#                     user['is_admin'] = False
#                 context.bot.send_message(
#                     user['id'], "You don't have permission to print...")
#                 store_data()
#                 break
