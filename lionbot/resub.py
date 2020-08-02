import os

import requests
import sentry_sdk

from lionbot.errors import SubscriptionError
from lionbot.utils import status_successful

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
    )


def subscribe_to_youtube():
    url = 'https://pubsubhubbub.appspot.com/subscribe'
    data = {
        "hub.mode": "subscribe",
        "hub.topic": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=Northernlion",
        "hub.callback": "https://lion-disc-bot.herokuapp.com/youtube/webhook",
    }
    response = requests.post(url, data=data)
    if not status_successful(response.status_code):
        raise SubscriptionError("YouTube", response.content)


class AuthenticationError(Exception):
    """
    Exception raised when failing to authenticate.
    """
    def __init__(self, source, response):
        self.source = source
        self.response = response


def get_twitch_access_token():
    url = f'https://id.twitch.tv/oauth2/token'
    body = {
        "client_id": os.environ.get("TWITCH_CLIENT_ID"),
        "client_secret": os.environ.get("TWITCH_CLIENT_SECRET"),
        "grant_type": "client_credentials",
    }
    response = requests.post(url, params=body)
    if not status_successful(response.status_code):
        raise AuthenticationError("Twitch", response.content)
    access_token = response.json()['access_token']
    return access_token


def subscribe_to_twitch():
    token = get_twitch_access_token()
    if token is None:
        return

    url = 'https://api.twitch.tv/helix/webhooks/hub'
    headers = {
        'Client-Id': os.environ.get('TWITCH_CLIENT_ID'),
        'Authorization': f'Bearer {token}',
    }
    json_body = {
        "hub.callback": "https://lion-disc-bot.herokuapp.com/twitch/webhook",
        "hub.mode": "subscribe",
        "hub.topic": "https://api.twitch.tv/helix/streams?user_id=14371185",
        "hub.lease_seconds": 864000,
        "hub.secret": os.environ.get("TWITCH_WEBHOOK_SECRET"),
    }
    response = requests.post(url, headers=headers, json=json_body)
    if not status_successful(response.status_code):
        raise SubscriptionError("Twitch", response.content)


if __name__ == "__main__":
    subscribe_to_twitch()
    subscribe_to_youtube()
