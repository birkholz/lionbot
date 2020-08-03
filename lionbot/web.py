import hashlib
import os
import random
import urllib.parse

import feedparser
import requests
from discord import Permissions
from flask import Flask, redirect, request, session, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from requests import HTTPError
from sentry_sdk import configure_scope
from sentry_sdk.integrations.flask import FlaskIntegration

from lionbot.data import Stream, Guild
from lionbot.errors import DiscordError, ValidationException
from lionbot.utils import status_successful, init_sentry

init_sentry([FlaskIntegration()])

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

discord_api_root = 'https://discord.com/api/v6'


def send_youtube_message(title, link):
    for stream in db.session.query(Stream).all():
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
            if not status_successful(response.status_code):
                with configure_scope() as scope:
                    scope.set_extra("source", "Discord")
                    scope.set_extra("request.body", json_body)
                    scope.set_extra("response.body", response.content)
                    raise DiscordError()


@app.route('/youtube/webhook', methods=['GET', 'POST'])
def youtube_webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge:
            return challenge, 200
        return '', 405

    # TODO: Ensure request came from YouTube
    video = feedparser.parse(request.data).entries[0]
    send_youtube_message(video.title, video.link)
    return '', 204


def send_twitch_message(title, thumbnail_url):
    for guild in db.session.query(Guild).all():
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
        if not status_successful(response.status_code):
            with configure_scope() as scope:
                scope.set_extra("source", "Discord")
                scope.set_extra("request.body", json_body)
                scope.set_extra("response.body", response.content)
                raise DiscordError()


@app.route('/twitch/webhook', methods=['GET', 'POST'])
def twitch_webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge:
            return challenge, 200
        return '', 405

    hash = hashlib.sha256(os.environb.get(b"TWITCH_WEBHOOK_SECRET") + request.get_data())
    if request.headers['X-Hub-Signature'] != f'sha256={hash.hexdigest()}':
        with configure_scope() as scope:
            scope.set_extra("source", "Twitch")
            scope.set_extra("sha", request.headers['X-Hub-Signature'])
            scope.set_extra("body", request.get_data())
            raise ValidationException()
    json_body = request.get_json()
    event = json_body['data'][0]
    if event['type'] == 'live':
        send_twitch_message(event['title'], event['thumbnail_url'])
    return '', 204


@app.route('/login', methods=['GET'])
def login():
    client_id = os.environ.get('DISCORD_CLIENT_ID')
    redirect_uri = urllib.parse.quote(f"{os.environ.get('DOMAIN')}/discord/callback")
    scopes = '%20'.join(['identify', 'guilds'])
    state = random.randint(10000000,99999999)
    session['discord_state'] = state
    redirect_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&state={state}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}&prompt=none"
    return render_template('login.html', redirect_url=redirect_url)


def exchange_discord_code(code=None):
    data = {
        'client_id': os.environ.get('DISCORD_CLIENT_ID'),
        'client_secret': os.environ.get('DISCORD_CLIENT_SECRET'),
        'redirect_uri': f"{os.environ.get('DOMAIN')}/discord/callback",
        'scope': 'identify guilds'
    }
    if code:
        data['code'] = code
        data['grant_type'] = 'authorization_code'
    else:
        data['refresh_token'] = session.get('discord_refresh_token')
        data['grant_type'] = 'refresh_token'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = call_discord_api('/oauth2/token', headers=headers, data=data, auth=False)
    session['discord_access_token'] = response['access_token']
    session['discord_refresh_token'] = response['refresh_token']


@app.route('/discord/callback', methods=['GET'])
def discord_callback():
    stored_state = session.pop('discord_state', None)
    if int(request.args.get('state')) != stored_state:
        with configure_scope() as scope:
            scope.set_extra("source", "Discord")
            scope.set_extra("state.incoming", request.args.get('state'))
            scope.set_extra("state.stored", stored_state)
            raise DiscordError("Mismatched state")

    exchange_discord_code(request.args.get('code'))
    return redirect(url_for('management'))


def call_discord_api(endpoint, headers=None, data=None, auth=True, bot=False):
    url = f'{discord_api_root}{endpoint}'
    if not headers:
        headers = {}
    if auth:
        if bot:
            headers['Authorization'] = f"Bot {os.environ.get('DISCORD_TOKEN')}"
        else:
            headers['Authorization'] = f"Bearer {session['discord_access_token']}"

    response = requests.get(url, headers=headers, data=data)
    with configure_scope() as scope:
        scope.set_extra("source", "Discord")
        response.raise_for_status()
    return response.json()


def get_guilds():
    call_discord_api('/guilds')


@app.route('/manage', methods=['GET'])
def management():
    if 'discord_access_token' not in session:
        return redirect(url_for('login'))

    try:
        current_user = call_discord_api('/users/@me')
        guilds = call_discord_api('/users/@me/guilds')
    except HTTPError:
        return redirect(url_for('login'))

    bot_guilds = call_discord_api('/users/@me/guilds', bot=True)

    guilds_managed = []
    for managed_guild in guilds:
        # Only show guilds they can add the bot to
        permissions = Permissions(permissions=int(managed_guild['permissions_new']))
        if not permissions.administrator and not permissions.manage_guild:
            continue

        # Mark guilds that the bot is already active in
        managed_guild['added'] = False
        for bot_guild in bot_guilds:
            if bot_guild['id'] == managed_guild['id']:
                managed_guild['added'] = True
                break

        if not managed_guild['added']:
            client_id = os.environ.get('DISCORD_CLIENT_ID')
            permissions = 268659776
            redirect_url = urllib.parse.quote(os.environ.get('DOMAIN') + url_for('manage_guild', guild_id=managed_guild['id']))
            managed_guild['add_link'] = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=bot&redirect_url={redirect_url}&guild_id={managed_guild['id']}"

        guilds_managed.append(managed_guild)

    return render_template("management.html", current_user=current_user, guilds=guilds_managed)


@app.route('/manage/<guild_id>', methods=['GET'])
def manage_guild(guild_id):
    guild = call_discord_api(f'/guilds/{guild_id}', bot=True)
    return render_template('manage_guild.html', guild=guild)
