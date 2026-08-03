from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from collections import Counter, defaultdict
import datetime
import re
import json
from textblob import TextBlob

TOKEN = 'INSERT YOUR TOKEN HERE'

stats = {
    'messages': 0,
    'users': defaultdict(int),
    'words': Counter(),
    'emotions': {'pos': 0, 'neg': 0, 'neu': 0},
    'hourly': [0]*24,
    'daily': [0]*7,
    'user_last_seen': {},
    'user_names': {},
    'media_count': 0,
    'links_count': 0
}

async def collect(update: Update, context: CallbackContext):
    msg = update.message
    if not msg or not msg.chat:
        return
    sender = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name or str(sender)
    text = msg.text or ''
    date = msg.date
    hour = date.hour
    weekday = date.weekday()
    stats['user_names'][sender] = username
    stats['messages'] += 1
    stats['users'][sender] += 1
    stats['hourly'][hour] += 1
    stats['daily'][weekday] += 1
    stats['user_last_seen'][sender] = date
    words = re.findall(r'\w+', text.lower())
    stats['words'].update(words)
    if 'http' in text or 't.me' in text:
        stats['links_count'] += 1
    if msg.photo or msg.video or msg.document:
        stats['media_count'] += 1
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        stats['emotions']['pos'] += 1
    elif polarity < -0.1:
        stats['emotions']['neg'] += 1
    else:
        stats['emotions']['neu'] += 1

async def stats_cmd(update: Update, context: CallbackContext):
    total = stats['messages']
    users = len(stats['users'])
    media = stats['media_count']
    links = stats['links_count']
    reply = (f"Statistics\n\n"
             f"Messages: {total}\n"
             f"Users: {users}\n"
             f"Media: {media}\n"
             f"Links: {links}\n"
             f"Positive: {stats['emotions']['pos']}\n"
             f"Negative: {stats['emotions']['neg']}\n"
             f"Neutral: {stats['emotions']['neu']}")
    await update.message.reply_text(reply)

async def top_cmd(update: Update, context: CallbackContext):
    top = Counter(stats['users']).most_common(5)
    reply = "Top 5 active:\n\n"
    for i, (uid, count) in enumerate(top, 1):
        name = stats['user_names'].get(uid, str(uid))
        reply += f"{i}. {name} - {count} messages\n"
    await update.message.reply_text(reply)

async def words_cmd(update: Update, context: CallbackContext):
    top_words = stats['words'].most_common(10)
    reply = "Most used words:\n\n"
    for word, count in top_words:
        if len(word) > 2:
            reply += f"{word} - {count}\n"
    await update.message.reply_text(reply)

async def mood_cmd(update: Update, context: CallbackContext):
    pos = stats['emotions']['pos']
    neg = stats['emotions']['neg']
    neu = stats['emotions']['neu']
    total = pos + neg + neu or 1
    reply = (f"Mood:\n\n"
             f"Positive: {pos} ({pos/total*100:.1f}%)\n"
             f"Negative: {neg} ({neg/total*100:.1f}%)\n"
             f"Neutral: {neu} ({neu/total*100:.1f}%)")
    await update.message.reply_text(reply)

async def user_cmd(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Use: /user @username")
        return
    username = context.args[0].replace('@', '')
    found = None
    for uid, name in stats['user_names'].items():
        if name.lower() == username.lower():
            found = uid
            break
    if not found:
        await update.message.reply_text("User not found")
        return
    count = stats['users'].get(found, 0)
    last = stats['user_last_seen'].get(found, 'unknown')
    await update.message.reply_text(f"{username}\nMessages: {count}\nLast seen: {last}")

async def start_cmd(update: Update, context: CallbackContext):
    await update.message.reply_text("Analytics bot started.\n"
                                    "/stats - general stats\n"
                                    "/top - top active\n"
                                    "/words - most used words\n"
                                    "/mood - sentiment\n"
                                    "/user @name - user stats")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, collect))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("words", words_cmd))
    app.add_handler(CommandHandler("mood", mood_cmd))
    app.add_handler(CommandHandler("user", user_cmd))
    app.add_handler(CommandHandler("start", start_cmd))
    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
