import sqlite3
import telebot
import datetime
import os
import requests

TG_TOKEN = os.environ['TG_TOKEN']

bot = telebot.TeleBot(TG_TOKEN, parse_mode=None)

conn = sqlite3.connect("/persistent/message_stat.db", check_same_thread=False,
                       detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)


def format_seconds_to_hhmmss(seconds):
    hours = seconds // (60*60)
    seconds %= (60*60)
    minutes = seconds // 60
    seconds %= 60
    return "%02i:%02i:%02i" % (hours, minutes, seconds)


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    cur = conn.cursor()

    first_day = datetime.datetime.today() - datetime.timedelta(days=datetime.datetime.today().weekday() % 7)
    first_day = first_day.replace(hour=0, minute=0, second=0, microsecond=0)

    chat_id = message.chat.id
    if chat_id < 0:
        table_name = f"chat_s{abs(chat_id)}"
    else:
        table_name = f"chat_{abs(chat_id)}"

    text: str = message.text
    if text.lower() == "кто больше всех пиздит" or text.lower() == "кто больше всех пиздит?":
        start_week = (first_day - datetime.timedelta(days=7)).strftime("%d.%m.%Y")
        end_week = (first_day - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        result = f"Люди без личной жизни за неделю {start_week} - {end_week}\n"
        data = cur.execute(f"SELECT username, count FROM dump_{table_name} WHERE 1=1 ORDER BY count DESC").fetchmany(10)
        if len(data) == 0:
            return
        for i, k in enumerate(data):
            result += f"{i + 1}. {k[0]} - {k[1]}\n"
        bot.send_message(chat_id, result)
        return
    
    if text.lower() == "кто больше всех жмет по клаве" or text.lower() == "кто больше всех жмет по клаве?":
        start_week = (first_day - datetime.timedelta(days=7)).strftime("%d.%m.%Y")
        end_week = (first_day - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        result = f"Лучшие мастера клавишного джаза за неделю {start_week} - {end_week}\n"
        data = requests.get(f"http://localhost:25424/weekly_stats/{chat_id}").json()
        d = []
        for k, v in data:
            d.append((v["username"], v["time"]))
        d = sorted(d, key=lambda x: x[1], reverse=True)
        if len(d) > 0:
            for i, k in enumerate(d[:10]):
                time = format_seconds_to_hhmmss(k.time)
                result += f"{i + 1}. {k.username} - {time}\n"
            bot.send_message(chat_id, result)
            return
        
    
    if text.lower() == "кто больше всех нажмякал по клаве" or text.lower() == "кто больше всех нажмякал по клаве?":
        start_week = (first_day - datetime.timedelta(days=7)).strftime("%d.%m.%Y")
        end_week = (first_day - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        result = f"Клавишные легенды вечности\n"
        data = requests.get(f"http://localhost:25424/global_stats/{chat_id}").json()
        d = []
        for k, v in data:
            d.append((v["username"], v["time"]))
        d = sorted(d, key=lambda x: x[1], reverse=True)
        if len(d) > 0:
            for i, k in enumerate(d[:10]):
                time = format_seconds_to_hhmmss(k.time)
                result += f"{i + 1}. {k.username} - {time}\n"
            bot.send_message(chat_id, result)
            return


    cur.execute(f"CREATE TABLE IF NOT EXISTS timings_{table_name} (creation_date timestamp);")
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS dump_{table_name} (user_id INTEGER PRIMARY KEY, username TEXT, count INT);")
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (user_id INTEGER PRIMARY KEY, username TEXT, count INT);")
    conn.commit()

    dump_timestamp = cur.execute(f"SELECT creation_date FROM timings_{table_name} WHERE 1=1;").fetchone()

    if dump_timestamp is None:
        cur.execute(f"INSERT INTO timings_{table_name} (creation_date) VALUES (?);", (first_day,))
        conn.commit()
    else:
        if dump_timestamp[0] != first_day:
            cur.execute(f"DROP TABLE dump_{table_name};")
            cur.execute(f"CREATE TABLE dump_{table_name} (user_id INTEGER PRIMARY KEY, username TEXT, count INT);")
            cur.execute(f"INSERT INTO dump_{table_name} SELECT * FROM {table_name} WHERE 1=1")
            cur.execute(f"DROP TABLE {table_name};")
            cur.execute(f"CREATE TABLE {table_name} (user_id INTEGER PRIMARY KEY, username TEXT, count INT);")
            cur.execute(f"UPDATE timings_{table_name} SET creation_date=? WHERE 1=1", (first_day,))
            conn.commit()

    x = cur.execute(f"SELECT count FROM {table_name} WHERE user_id=?;", (message.from_user.id,)).fetchone()
    if x is not None:
        count = x[0]
    else:
        count = 1
    if message.from_user.last_name:
        username = f"{message.from_user.first_name} {message.from_user.last_name}"
    else:
        username = message.from_user.first_name
    cur.execute(
        f"INSERT INTO {table_name} (user_id, username, count) VALUES(?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username=?, count=?;",
        (message.from_user.id, username, count, username, count + 1))
    conn.commit()


if __name__ == "__main__":
    bot.infinity_polling()
