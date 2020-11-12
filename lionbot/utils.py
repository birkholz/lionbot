import os

import requests
from sentry_sdk import configure_scope

from lionbot.errors import DiscordError


def status_successful(status_code):
    return status_code >= 200 and status_code < 300

def init_sentry(integrations=None):
    if not integrations:
        integrations = []

    if os.environ.get("SENTRY_DSN"):
        import sentry_sdk
        sentry_sdk.init(
            dsn=os.environ.get("SENTRY_DSN"),
            integrations=integrations
        )

def int_ids(obj):
    if isinstance(obj, dict):
        obj['id'] = int(obj['id'])
    if isinstance(obj, list):
        for o in obj:
            int_ids(o)


def send_discord_request(method, endpoint, body=None):
    message_url = f"https://discordapp.com/api/{endpoint}"
    headers = {
        "Authorization": f"Bot {os.environ.get('DISCORD_TOKEN')}",
        "Content-Type": "application/json",
    }

    response = requests.request(method, message_url, headers=headers, json=body)
    if not status_successful(response.status_code):
        with configure_scope() as scope:
            scope.set_extra("source", "Discord")
            scope.set_extra("request.body", body)
            scope.set_extra("response.body", response.content)
            raise DiscordError()

    if response.status_code != 204:
        return response.json()