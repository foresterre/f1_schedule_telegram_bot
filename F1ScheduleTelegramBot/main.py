import datetime
import logging
import os
import requests
import telegram

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler
from ics import Calendar, Event

"""
Load .env variables
"""
load_dotenv()


"""
Setup logger
"""
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

CHECK_INTERVAL = datetime.timedelta(seconds=30)
NOTIFICATIONS = [
    {'delta': datetime.timedelta(minutes=15), 'message': "%s will start in 15 minutes."},
    # {'delta': datetime.timedelta(minutes=2), 'message': "%s will start in 2 minutes."},
    {'delta': datetime.timedelta(minutes=1), 'message': "%s is about to start!"}
]


async def main():
    bot = telegram.Bot(bot_token)
    async with bot:
        print(await bot.get_me())
        print((await bot.get_updates())[0])
        await bot.send_message(text='Hi John!', chat_id=1687550897)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! I am F1ScheduleTelegramBot! I am currently mostly hardcoded, but more features will be coming "
             "soon! Your chat id is: `%s`." % update.effective_chat.id,
    )


async def update_callback(context: ContextTypes.DEFAULT_TYPE):
    ical_url = os.getenv('ICAL_URL')

    # Get the F1 calendar
    cal = Calendar(requests.get(ical_url).text)
    print(cal.events)

    now = datetime.datetime.now(datetime.timezone.utc)
    chat_id = os.getenv('CHAT_ID')
    for notification in NOTIFICATIONS:
        for event in cal.events:
            event_begin_timedelta = event.begin - notification['delta'] - 0.5 * CHECK_INTERVAL
            event_end_timedelta = event.begin - notification['delta'] + 0.5 * CHECK_INTERVAL
            logging.debug("[%s]: %s -- %s - %s" % (event.name, notification['message'], event_begin_timedelta, event_end_timedelta))
            if event_begin_timedelta < now < event_end_timedelta:
                logging.info("Event in notification window!")
                message = notification['message'] % event.name
                logging.info("Sending message: \"%s\" to chat_id: %s." % (message, chat_id))
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                )


if __name__ == '__main__':
    bot_token = os.getenv('BOT_TOKEN')
    if bot_token is None or len(bot_token) <= 0:
        raise Exception("No BOT_TOKEN in environment!")

    ical_url = os.getenv('ICAL_URL')
    if ical_url is None or len(ical_url) <= 0:
        raise Exception("No ICAL_URL in environment!")

    chat_id = os.getenv('CHAT_ID')
    if chat_id is None or len(chat_id) <= 0:
        raise Exception("No CHAT_ID in environment!")

    application = ApplicationBuilder().token(bot_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    job_queue = application.job_queue
    job_every_second = job_queue.run_repeating(update_callback, interval=CHECK_INTERVAL, first=1)

    application.run_polling()
