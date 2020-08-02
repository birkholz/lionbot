import logging
import os

import feedparser
import requests
import sentry_sdk
from flask import Flask, request
from sentry_sdk.integrations.flask import FlaskIntegration
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data import Stream, Guild


sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[FlaskIntegration()]
)

app = Flask(__name__)

engine = create_engine(os.environ.get('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()


def send_youtube_message(title, link):
    for stream in session.query(Stream).all():
        if stream.title_contains is not None and stream.title_contains in title:
            channel_id = stream.channel_id
            message_url = f"https://discordapp.com/api/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {os.environ.get('DISCORD_TOKEN')}",
                "Content-Type": "application/json",
            }

            content = f"<@&{stream.role_id}>\n{link}"

            json_body = {
                "content": content,
                "allowed_mentions": {
                    "parse": ["roles"]
                }
            }
            response = requests.post(message_url, headers=headers, json=json_body)
            if response.status_code > 299:
                logging.error(f"Error when posting YouTube video: {response.content}")


@app.route('/youtube/webhook', methods=['POST'])
def youtube_webhook():
    # TODO: Ensure request came from YouTube
    video = feedparser.parse(request.data).entries[0]
    send_youtube_message(video.title, video.link)
    return '', 204


def send_twitch_message(title, thumbnail_url):
    for guild in session.query(Guild).all():
        channel_id = guild.twitch_stream.channel_id
        message_url = f"https://discordapp.com/api/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {os.environ.get('DISCORD_TOKEN')}",
            "Content-Type": "application/json",
        }

        link = 'https://www.twitch.tv/northernlion'
        content = f"<@&{guild.twitch_stream.role_id}>\nNorthernlion just went live on Twitch!"

        json_body = {
            "content": content,
            "embed": {
                "title": title,
                "url": link,
                "image": {
                    "url": thumbnail_url,
                }
            },
            "allowed_mentions": {
                "parse": ["roles"]
            }
        }
        response = requests.post(message_url, headers=headers, json=json_body)
        if response.status_code > 299:
            logging.error(f"Error when posting Twitch live embed: {response.content}")
            return


@app.route('/twitch/webhook', methods=['POST'])
def twitch_webhook():
    # TODO: request.headers['X-Hub-Signature'] == sha256(secret, notification_bytes)
    json_body = request.get_json()
    event = json_body['data'][0]
    if event['type'] == 'live':
        send_twitch_message(event['title'], event['thumbnail_url'])
    return '', 204

@app.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0
