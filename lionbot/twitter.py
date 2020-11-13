import logging
import os
import signal
import sys
import time

from TwitterAPI import TwitterAPI, TwitterRequestError
from sentry_sdk import capture_exception
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lionbot.data import Guild
from lionbot.errors import DiscordError
from lionbot.utils import send_discord_request

logging.basicConfig(level=logging.INFO)
engine = create_engine(os.environ.get('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()


def send_tweet_message(tweet):
    for guild in session.query(Guild).all():
        if guild.twitter_stream_id is None:
            continue

        stream = guild.twitter_stream
        url = f"https://twitter.com/NorthernlionLP/status/{tweet['id']}"
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
    stream = api.request('tweets/search/stream')
    logging.info("Twitter stream started")

    for msg in stream:
        if 'data' in msg:
            logging.info(f"Received tweet: {msg}")
            send_tweet_message(msg['data'])


def start_stream(wait=2):
    logging.info("Twitter stream starting...")
    try:
        run_stream()
    except TwitterRequestError as e:
        if e.status_code == 429:
            logging.info(f'Waiting {wait} seconds to retry...')
            time.sleep(wait)
            start_stream(wait=wait*2)


def signal_handler(signal, frame):
    logging.info("Shutting down twitter stream...")
    if stream is not None:
        stream.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
start_stream()