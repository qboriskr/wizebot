# Бот-цитатник для Telegram

## Инструкция по запуску

1. Добавить бота в Telegram, общаясь с ботом BotFather; получить от него ключ HTTP API.
2. Задеплоить бота как web-приложение на heroku. Назовем его wzbot.
Обязательно указать для него переменные окружения:
* GOOGLE_CX_CODE = <настройка CX_CODE из API поиска картинок>
* GOOGLE_DEVELOPER_KEY = <настройка из API разработчика>
* SECRET_KEY = <соль для Django>
* TELEGRAM_BOT_TOKEN = <ключ HTTP API>

  Ограничить количество запускаемых одновременно инстансов приложения - для этого есть переменная окружения для Heroku:
* WEB_CONCURRENCY = 1
3. Чтобы бот получал сигналы от Telegram, установить webhook (может понадобится VPN, например Windscribe):
```python
import telepot
token = 'токен HTTP API, полученный от BotFather'
TelegramBot = telepot.Bot(token)
TelegramBot.setWebhook('https://wzbot.herokuapp.com/planet/bot/{bot_token}/'.format(bot_token=token))
```

4. После этого можно что-нибудь написать боту в ЛС и получить цитату с нечетким поиском по вхождению переданных слов.
Если добавить в конце /10 - выведет 10 цитат по убыванию score. Таким образом, можно использовать бота как поисковик, например:
* твен /30 - приколы из 19-го века
* цзы /10 - древние китайские мемы
* делез /10 - постмодернизьм

## Попробовать:
t.me/w_z_bot [ https://tglink.ru/w_z_bot ]

Раз уж чатбот это веб-приложение, можно получать случайную цитату и просто через REST - https://wzbot.herokuapp.com/planet/quote