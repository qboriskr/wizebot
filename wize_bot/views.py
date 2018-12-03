import json
import logging
from io import BytesIO
import urllib
import re
import os
import uuid
from threading import Thread
from time import sleep
from wize_bot.aphorism.aphorism import APHORISMS, MODEL_NAME
import telepot
from google_images_search import GoogleImagesSearch

from django.template.loader import render_to_string
from django.http import HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

from .utils import parse_planetpy_rss

TelegramBot = telepot.Bot(settings.TELEGRAM_BOT_TOKEN)

APHORISMS.load(os.path.join(settings.BASE_DIR, 'data'), MODEL_NAME)

BOT_ID = "Bot-" + str(uuid.uuid1())[:4]


class ChatRoom:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.bot_is_active = False
        self.welcome_pic_shown = False
        self.message_count = 0


ROOMS = {}

QUOTES_POST_PERIOD = 360  # Период отправки цитат (поштучно)
NUM_QUOTES_LIMIT = 30  # Максимум афоризмов в ответе при запросе нескольких штук

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

PICS_CACHE = {}
CACHED_WELCOME_PIC = None


def search_pic(aphorism):
    if not aphorism:
        return None
    if aphorism in PICS_CACHE:
        img_bytes = PICS_CACHE[aphorism]
        img_bytes.seek(0)
        return img_bytes
    try:
        words = aphorism
        for sep in '.,!?:;-/\\@#$%^&*()\'"':
            words = words.replace(sep, ' ')
        words = words.split(' ')
        # убираем лишние пробелы
        words = list(filter(lambda w: len(w) > 0, words))
        search_words = (' '.join(words))
        # ограничиваем длину строки для поиска
        while len(search_words) > 80:
            search_words = search_words.rsplit(' ', 1)[0]

        while len(search_words) > 10:
            print('searching pic by query:', search_words)
            gis = GoogleImagesSearch(settings.GOOGLE_DEVELOPER_KEY, settings.GOOGLE_CX_CODE)
            gis.search({'q': search_words, 'num': 1})
            gis_result = gis.results()
            print('results len:', len(gis_result))
            if gis_result:
                if isinstance(gis_result, list):
                    image = gis_result[0]
                else:
                    image = gis_result
                img_bytes = BytesIO()
                image.copy_to(img_bytes, image.get_raw_data())
                img_bytes.seek(0)
                PICS_CACHE[aphorism] = img_bytes
                return img_bytes
            search_words = search_words[:2 * len(search_words) / 3]
    except Exception as ex:
        logger.error("Exception on receiving image: %s" % (str(ex)))
    return None


def threaded_function():
    while True:
        sleep(QUOTES_POST_PERIOD)
        print("Cycling quotes...")
        print("Bot name: ", BOT_ID)
        aphorism = APHORISMS.get_random()
        if not aphorism:
            continue
        pic = search_pic(aphorism)
        for chat_id, room in ROOMS.items():
            if not room.bot_is_active:
                continue
            if pic is not None:
                TelegramBot.sendPhoto(chat_id, pic)
            TelegramBot.sendMessage(chat_id, aphorism.encode())
            room.message_count += 1


thread = Thread(target=threaded_function, args=())
thread.start()


def display_stats(room: ChatRoom):
    bot_status = 'enable' if room.bot_is_active else 'disabled'
    result = '{} status: {}\n'.format(BOT_ID, bot_status)
    result += APHORISMS.get_stats()
    result += '\n'
    result += 'Messages: ' + str(room.message_count)
    return result


def start_bot(room: ChatRoom):
    room.bot_is_active = True
    return "{} is enabled!".format(BOT_ID)


def stop_bot(room: ChatRoom):
    room.bot_is_active = False
    return "{} is disabled!".format(BOT_ID)


def display_help(_room):
    return render_to_string('help.md')


def display_planetpy_feed(_room):
    return render_to_string('feed.md', {'items': parse_planetpy_rss()})


MARKDOWN_FMT = 'Markdown'

COMMANDS = {
    '/status': (display_stats, None),
    '/start': (start_bot, MARKDOWN_FMT),
    '/stop': (stop_bot, MARKDOWN_FMT),
    '/help': (display_help, MARKDOWN_FMT),
    # '/feed': (display_planetpy_feed, MARKDOWN_FMT)
}


class QuoteView(View):
    def get(self, _request):
        print('Handling GET request')
        return JsonResponse({'quote': APHORISMS.get_random()}, status=200, safe=False,
                            json_dumps_params={'ensure_ascii': False})

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(QuoteView, self).dispatch(request, *args, **kwargs)


class CommandReceiveView(View):

    def post(self, request, bot_token):
        print('Handling POST request')

        if bot_token != settings.TELEGRAM_BOT_TOKEN:
            logger.warning('Invalid bot token!')
            return HttpResponseForbidden('Invalid token')
        raw = request.body.decode('utf-8')
        print(raw)

        try:
            payload = json.loads(raw)
        except ValueError:
            return HttpResponseBadRequest('Invalid request body')
        else:
            if 'message' in payload:
                message_node_name = 'message'
            elif 'edited_message' in payload:
                message_node_name = 'edited_message'
            else:
                logger.error('cannot find message block in JSON:\n %s' % str(payload))
                return JsonResponse({}, status=500)
            chat_id = payload[message_node_name]['chat']['id']
            if not chat_id:
                logger.error('empty chat_id!')
                return JsonResponse({}, status=200)

            try:
                room = ROOMS[chat_id]
            except KeyError:
                room = ChatRoom(chat_id)
                ROOMS[chat_id] = room
            input_text = payload[message_node_name].get('text')  # command
            if input_text is None:
                logger.error('cmd is None!')
                return JsonResponse({}, status=200)

            if not input_text:
                logger.error('cmd is empty string!', input_text)
                return JsonResponse({}, status=200)
            print('cmd: %s' % input_text)
            room.message_count += 1
            cmd = input_text.split()[0].lower()
            cmd_handler = COMMANDS.get(cmd)
            if cmd_handler:
                func, response_fmt = cmd_handler
                TelegramBot.sendMessage(chat_id, func(room), response_fmt)
            else:
                if not room.bot_is_active:
                    self.show_welcome_pic(room)
                else:
                    reply_to_message_id = payload[message_node_name].get('message_id')
                    self.send_quote_by_input(room, reply_to_message_id, input_text)

        return JsonResponse({}, status=200)

    @staticmethod
    def send_quote_by_input(room, reply_to_message_id, input_text):
        n = 1
        m = re.search(r'\[\d+\]$', input_text)
        if m is not None:
            sz = len(m.group())
            input_text = input_text[:-sz]
            n = min(int(m.group()[1:-1]), NUM_QUOTES_LIMIT)
        else:
            m = re.search(r'/\d+$', input_text)
            if m is not None:
                sz = len(m.group())
                input_text = input_text[:-sz]
                n = min(int(m.group()[1:]), NUM_QUOTES_LIMIT)

        aphorisms = APHORISMS.get_fuzzy(input_text, n)
        result = '{} replies [{}]:\n'.format(BOT_ID, room.message_count)
        for aphorism in aphorisms:
            result += "%s (score %.2f)\n" % (aphorism[0], aphorism[1])
        pic = search_pic(aphorisms[0][0])
        TelegramBot.sendMessage(room.chat_id, result.encode(), reply_to_message_id=reply_to_message_id)
        if pic is not None:
            TelegramBot.sendPhoto(room.chat_id, pic)

    @staticmethod
    def show_welcome_pic(room: ChatRoom):
        TelegramBot.sendChatAction(room.chat_id, 'upload_photo')
        global CACHED_WELCOME_PIC
        if not CACHED_WELCOME_PIC:
            pic_url = 'http://img-fotki.yandex.ru/get/26036/310023662.31c5/0_773570_44fab6ea_orig'
            CACHED_WELCOME_PIC = BytesIO(urllib.request.urlopen(pic_url).read())
        else:
            CACHED_WELCOME_PIC.seek(0)

        if not room.welcome_pic_shown:
            room.welcome_pic_shown = True
            TelegramBot.sendPhoto(room.chat_id, CACHED_WELCOME_PIC)
        welcome_message = '{} is currently disabled! Type /start or /help'.format(BOT_ID)
        TelegramBot.sendMessage(room.chat_id, welcome_message)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CommandReceiveView, self).dispatch(request, *args, **kwargs)
