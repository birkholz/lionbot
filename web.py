import os

import feedparser
import requests
from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data import Stream

app = Flask(__name__)

engine = create_engine(os.environ.get('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()

def send_message(title, link):
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
            requests.post(message_url, headers=headers, json=json_body)

@app.route('/youtube/webhook', methods=['POST'])
def youtube_webhook():
    # TODO: Ensure request came from YouTube
    video = feedparser.parse(request.data).entries[0]
    send_message(video.title, video.link)
    return '', 204


@app.route('/twitch/webhook', methods=['POST'])
def twitch_webhook():
    return '', 204
