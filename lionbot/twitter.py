import logging
import os
import signal
import sys
import time

from TwitterAPI import TwitterAPI, TwitterRequestError, TwitterConnectionError
from sentry_sdk import capture_exception
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lionbot.data import Guild
from lionbot.errors import DiscordError
from lionbot.utils import send_discord_request

logging.basicConfig(level=logging.INFO)
database_uri = os.getenv("DATABASE_URL")  # or other relevant config var
if database_uri and database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)
engine = create_engine(database_uri)
Session = sessionmaker(bind=engine)
session = Session()


def send_tweet_message(tweet):
    for guild in session.query(Guild).all():
        if guild.twitter_stream_id is None:
            continue

        if not guild.twitter_replies and 'in_reply_to_user_id' in tweet and tweet['in_reply_to_user_id'] != '213161945':
            continue

        stream = guild.twitter_stream
        url = f"https://twitter.com/Northernlion/status/{tweet['id']}"
        content = f"<@&{stream.role_id}>\n{url}"
        json_body = {
            "content": content,
            "allowed_mentions": {
                "parse": ["roles"]
            }
        }

        channel_id = stream.channel_id
        try:
            send_discord_request('post', f"channels/{channel_id}/messages", json_body)
        except DiscordError as e:
            capture_exception(e)


api = TwitterAPI(
    os.environ.get("TWITTER_API_KEY"),
    os.environ.get("TWITTER_API_SECRET"),
    auth_type='oAuth2',
    api_version='2'
)
stream = None

def run_stream():
    stream = api.request('tweets/search/stream', params={'tweet.fields': 'id,text,in_reply_to_user_id'})
    logging.info("Twitter stream started")

    for msg in stream:
        if 'data' in msg:
            logging.info(f"Received tweet: {msg}")
            send_tweet_message(msg['data'])


def start_stream(wait=30):
    logging.info("Twitter stream starting...")
    try:
        run_stream()
    except TwitterRequestError as e:
        if e.status_code == 429:
            stream = None
            logging.info(f'Waiting {wait} seconds to retry...')
            time.sleep(wait)
            start_stream(wait=wait+30)
    except TwitterConnectionError:
        stream = None
        # the error's __init__ logs itself
        logging.info(f'Waiting {wait} seconds to retry...')
        time.sleep(wait)
        start_stream(wait=wait+30)



def signal_handler(signal, frame):
    logging.info("Shutting down twitter stream...")
    if stream is not None:
        stream.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
start_stream()