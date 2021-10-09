import hmac
import logging
import os
import urllib.parse

import feedparser
import requests
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from psycopg2._psycopg import IntegrityError
from sentry_sdk import configure_scope, capture_exception
from sentry_sdk.integrations.flask import FlaskIntegration

from lionbot.data import Stream, Guild, Video, TwitchStream
from lionbot.errors import DiscordError, ValidationException
from lionbot.utils import init_sentry, send_discord_request

logging.basicConfig(level=logging.INFO)

init_sentry([FlaskIntegration()])

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

discord_api_root = 'https://discord.com/api/v6'


def send_youtube_message(video):
    for stream in db.session.query(Stream).all():
        posted = db.session.query(Video).filter_by(video_id=video.id, guild_id=stream.guild_id).count()
        if posted > 0:
            # Already posted, don't repost
            continue

        if (stream.playlist_id is not None and video_is_in_playlist(video.yt_videoid, stream.playlist_id)) or \
                (stream.title_contains is not None and stream.title_contains in video.title):

            obj = Video(video_id=video.id, guild_id=stream.guild_id)
            db.session.add(obj)

            try:
                db.session.commit()
            except IntegrityError as e:
                # Duplicate race condition
                capture_exception(e)
                continue

            content = f"<@&{stream.role_id}>\n{video.link}"
            if stream.guild.playlist_links and stream.playlist_id is not None:
                content += f'&list={stream.playlist_id}'
            json_body = {
                "content": content,
                "allowed_mentions": {
                    "parse": ["roles"]
                }
            }

            channel_id = stream.channel_id
            try:
                response = send_discord_request('post', f"channels/{channel_id}/messages", json_body)
                logging.info(f"Successfully posted video id:{video.yt_videoid} to channel: {channel_id}")
            except DiscordError as e:
                capture_exception(e)
                continue

            message_id = response['id']

            try:
                if stream.guild.pinning_enabled:
                    # Unpin previous, pin new
                    if stream.latest_message_id:
                        send_discord_request('delete', f"channels/{channel_id}/pins/{stream.latest_message_id}")
                    send_discord_request('put', f"channels/{channel_id}/pins/{message_id}")

                    stream.latest_message_id = message_id
                    db.session.add(stream)
                    db.session.commit()
            except DiscordError as e:
                capture_exception(e)
                continue


def video_is_in_playlist(video_id, playlist_id):
    """
    Queries YouTube's Data API to ask if a video is in a playlist.
    """
    params = {
        'key': os.environ.get('YOUTUBE_API_KEY'),
        'playlistId': playlist_id,
        'videoId': video_id,
        'part': 'id',
    }
    param_string = urllib.parse.urlencode(params)
    url = f'https://www.googleapis.com/youtube/v3/playlistItems?{param_string}'
    response = requests.get(url)
    body = response.json()
    if 'error' in body:
        return False

    return body['pageInfo']['totalResults'] > 0


@app.route('/youtube/webhook', methods=['GET', 'POST'])
def youtube_webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge:
            return challenge, 200
        return '', 405

    if not check_signature(request):
        with configure_scope() as scope:
            scope.set_extra("source", "YouTube")
            scope.set_extra("sha", request.headers['X-Hub-Signature'])
            scope.set_extra("body", request.get_data())
            raise ValidationException()

    try:
        logging.info(f"Received YouTube webhook: {request.data}")
        video = feedparser.parse(request.data).entries[0]
        send_youtube_message(video)
    except IndexError as e:
        with configure_scope() as scope:
            scope.set_extra("source", "YouTube")
            scope.set_extra("body", request.data)
            capture_exception(e)

    return '', 204


def send_twitch_message(event):
    for guild in db.session.query(Guild).all():
        posted = db.session.query(TwitchStream).filter_by(twitch_id=event['id'], guild_id=guild.id).count()
        if posted > 0:
            # Already posted, don't repost
            continue

        stream = guild.twitch_stream
        link = 'https://www.twitch.tv/northernlion'
        content = f"<@&{stream.role_id}>\nNorthernlion just went live on Twitch!\n{link}"
        json_body = {
            "content": content,
            "allowed_mentions": {
                "parse": ["roles"]
            }
        }
        channel_id = stream.channel_id
        try:
            response = send_discord_request('post', f"channels/{channel_id}/messages", json_body)
        except DiscordError as e:
            capture_exception(e)
            continue

        message_id = response['id']

        try:
            if guild.pinning_enabled:
                if stream.latest_message_id:
                    send_discord_request('delete', f"channels/{channel_id}/pins/{stream.latest_message_id}")
                send_discord_request('put', f"channels/{channel_id}/pins/{message_id}")

                stream.latest_message_id = message_id
                db.session.add(stream)
        except DiscordError as e:
            capture_exception(e)
            continue

        obj = TwitchStream(twitch_id=event['id'], guild_id=guild.id)
        db.session.add(obj)
        db.session.commit()


def check_signature(request):
    signed = request.headers.get('Twitch-Eventsub-Message-Signature')
    if signed:
        alg, signature = signed.split('=')
        hash = hmac.new(os.environb.get(b"WEBHOOK_SECRET"), msg=request.get_data(), digestmod=alg).hexdigest()
        return hash == signature

    return True


@app.route('/twitch/webhook', methods=['GET', 'POST'])
def twitch_webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        if challenge:
            return challenge, 200
        return '', 405

    if not check_signature(request):
        with configure_scope() as scope:
            scope.set_extra("source", "Twitch")
            scope.set_extra("sha", request.headers['X-Hub-Signature'])
            scope.set_extra("body", request.get_data())
            raise ValidationException()

    logging.info(f"Received Twitch webhook: {request.data}")
    json_body = request.get_json()
    if json_body['challenge']:
        return json_body['challenge'], 200

    if json_body['event']:
        event = json_body['event']
        if event['type'] == 'live':
            send_twitch_message(event)
    return '', 204
