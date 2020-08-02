import logging
import os

import requests
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
)

def subscribe_to_youtube():
    url = 'https://pubsubhubbub.appspot.com/subscribe'
    data = {
        "mode": "subscribe",
        "topic_id": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=Northernlion",
        "callback_url": "https://lion-disc-bot.herokuapp.com/youtube/webhook",
    }
    response = requests.post(url, data=data)
    if response.status_code > 299:
        logging.error(f"Error when subscribing to YouTube: {response.content}")


def get_twitch_access_token():
    url = f'https://id.twitch.tv/oauth2/token'
    body = {
        "client_id": os.environ.get("TWITCH_CLIENT_ID"),
        "client_secret": os.environ.get("TWITCH_CLIENT_SECRET"),
        "grant_type": "client_credentials",
    }
    response = requests.post(url, params=body)
    if response.status_code > 299:
        logging.error(f"Failed to get Twitch access code: {response.content}")
        return None
    access_token = response.json()['access_token']
    return access_token


def subscribe_to_twitch():
    token = get_twitch_access_token()
    if token is None:
        return

    url = 'https://api.twitch.tv/helix/webhooks/hub'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    json_body = {
        "hub.callback": "https://lion-disc-bot.herokuapp.com/twitch/webhook",
        "hub.mode": "subscribe",
        "hub.topic": "https://api.twitch.tv/helix/streams?user_id=14371185",
        "hub.lease_seconds": 864000,
        "hub.secret": os.environ.get("TWITCH_WEBHOOK_SECRET"),
    }
    response = requests.post(url, headers=headers, json=json_body)
    if response.status_code > 299:
        logging.error(f"Error when subscribing to Twitch: {response.json()}")

if __name__ == "__main__":
    subscribe_to_twitch()
    subscribe_to_youtube()
