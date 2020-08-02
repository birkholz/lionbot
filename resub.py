import os

import requests


def subscribe_to_youtube():
    url = 'https://pubsubhubbub.appspot.com/subscribe'
    data = {
        "mode": "subscribe",
        "topic_id": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=Northernlion",
        "callback_url": "localhost:5000/youtube/webhook",  # TODO: fill this when the server is up and running
    }
    requests.post(url, data=data)


def get_twitch_access_token():
    url = f'https://id.twitch.tv/oauth2/token'
    body = {
        "client_id": os.environ.get("TWITCH_CLIENT_ID"),
        "client_secret": os.environ.get("TWITCH_CLIENT_SECRET"),
        "grant_type": "client_credentials",
    }
    response = requests.post(url, params=body).json()
    access_token = response['access_token']
    return access_token


def subscribe_to_twitch():
    url = 'https://api.twitch.tv/helix/webhooks/hub'
    headers = {
        'Authorization': f'Bearer {get_twitch_access_token()}'
    }
    json_body = {
        "hub.callback": "localhost:5000/twitch/webhook",  # TODO: fill this when server is up and running
        "hub.mode": "subscribe",
        "hub.topic": "https://api.twitch.tv/helix/streams?user_id=14371185",
        "hub.lease_seconds": 864000,
        "hub.secret": os.environ.get("TWITCH_WEBHOOK_SECRET"),
    }
    requests.post(url, headers=headers, json=json_body)

if __name__ == "__main__":
    subscribe_to_twitch()
    subscribe_to_youtube()
