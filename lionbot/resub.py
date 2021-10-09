import os

import requests
from sentry_sdk import configure_scope

from lionbot.errors import SubscriptionError, AuthenticationError
from lionbot.utils import status_successful, init_sentry

init_sentry()


def subscribe_to_youtube():
    url = 'https://pubsubhubbub.appspot.com/subscribe'
    data = {
        "hub.mode": "subscribe",
        "hub.topic": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC3tNpTOHsTnkmbwztCs30sA",
        "hub.callback": f"{os.environ.get('DOMAIN')}/youtube/webhook",
        "hub.secret": os.environ.get("WEBHOOK_SECRET"),
    }
    response = requests.post(url, data=data)
    if not status_successful(response.status_code):
        with configure_scope() as scope:
            scope.set_extra("source", "YouTube")
            scope.set_extra("request.body", data)
            scope.set_extra("response.body", response.content)
            raise SubscriptionError()


def get_twitch_access_token():
    url = f'https://id.twitch.tv/oauth2/token'
    body = {
        "client_id": os.environ.get("TWITCH_CLIENT_ID"),
        "client_secret": os.environ.get("TWITCH_CLIENT_SECRET"),
        "grant_type": "client_credentials",
    }
    response = requests.post(url, params=body)
    if not status_successful(response.status_code):
        with configure_scope() as scope:
            scope.set_extra("source", "Twitch")
            scope.set_extra("request.body", body)
            scope.set_extra("response.body", response.content)
            raise AuthenticationError()
    access_token = response.json()['access_token']
    return access_token


def subscribe_to_twitch():
    token = get_twitch_access_token()
    if token is None:
        return

    url = 'https://api.twitch.tv/helix/eventhub/subscriptions'
    headers = {
        'Client-Id': os.environ.get('TWITCH_CLIENT_ID'),
        'Authorization': f'Bearer {token}',
    }
    json_body = {
        "type": "stream.online",
        "version": "1",
        "condition": {
            "broadcaster_user_id": "14371185"
        },
        "transport": {
            "method": "webhook",
            "callback": f"{os.environ.get('DOMAIN')}/twitch/webhook",
            "secret": os.environ.get("WEBHOOK_SECRET")
        }
    }
    response = requests.post(url, headers=headers, json=json_body)
    if not status_successful(response.status_code):
        with configure_scope() as scope:
            scope.set_extra("source", "Twitch")
            scope.set_extra("request.body", json_body)
            scope.set_extra("response.body", response.content)
            raise SubscriptionError()


if __name__ == "__main__":
    # subscribe_to_twitch()
    subscribe_to_youtube()
