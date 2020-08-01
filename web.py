import os

import feedparser
import redis
import requests
from flask import Flask, request

from data import get_streams

app = Flask(__name__)

redis_client = redis.Redis.from_url(os.environ.get("REDIS_URL"))


def send_message(title, link):
    streams = get_streams()
    channel = None
    for stream in streams:
        if stream['name_contains'] in title:
            channel = stream['channel']

    if not channel:
        return



    message_url = f"https://discordapp.com/api/channels/{int(redis_client.get('role_channel_id'))}/messages"
    headers = {
        "Authorization": f"Bot {os.environ.get('DISCORD_TOKEN')}",
        "Content-Type": "application/json",
    }

    requests.post(message_url, headers=headers, json={"content": link})


@app.route('/youtube/webhook', methods=['POST'])
def youtube_webhook():
    # TODO: Ensure request came from YouTube
    video = feedparser.parse(request.data).entries[0]
    send_message(video.title, video.link)
    return '', 204


@app.route('/twitch/webhook', methods=['POST'])
def twitch_webhook():
    return '', 204
