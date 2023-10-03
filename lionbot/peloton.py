import datetime
import logging
import os

import requests
from sentry_sdk import capture_exception

from lionbot.errors import DiscordError
from lionbot.utils import send_discord_request


class PelotonAPI:
    def __init__(self):
        self.API = requests.Session()

    def login(self):
        payload = {
            'username_or_email': os.environ.get('PELOTON_USERNAME'),
            'password': os.environ.get('PELOTON_PASSWORD')
        }

        return self.API.post('https://api.onepeloton.com/auth/login', json=payload)
        # stores cookies to the Session
        # I hate using cookies, but I don't see a way to get a bearer token yet

    def get_workouts(self, user_id):
        request_url = f'https://api.onepeloton.com/api/user/{user_id}/workouts?joins=ride,ride.instructor'
        response = self.API.get(request_url)

        if response.status_code == 401:
            self.login()
            return self.get_workouts(user_id)

        return response.json()['data']


def post_workouts(workouts):
    embeds = []

    for workout in workouts:
        if workout['status'] != 'COMPLETE':
            continue

        class_id = workout['ride']['id']
        class_url = f'https://members.onepeloton.com/classes/cycling?modal=classDetailsModal&classId={class_id}'

        created_at = datetime.datetime.fromtimestamp(workout['created_at'])
        start_time = datetime.datetime.fromtimestamp(workout['start_time'])
        end_time = datetime.datetime.fromtimestamp(workout['end_time'])
        total_output = workout['total_work']
        duration = end_time - start_time
        avg_output = total_output / duration.seconds

        instructor_name = workout['ride']['instructor']['name']
        instructor_image = workout['ride']['instructor']['image_url']

        ride_title = workout['ride']['title']

        new_pb = workout['is_total_work_personal_record']
        pb_line = '\n\n ⭐ ️**New Total Work Personal Record!** ⭐️' if new_pb else ''

        embed = {
            'type': 'rich',
            'title': ride_title,
            'description': f'{instructor_name}{pb_line}',
            'url': class_url,
            'thumbnail': {
                'url': instructor_image
            },
            'fields': [
                {
                    'name': 'Date',
                    'value': f'<t:{int(created_at.timestamp())}:F>',
                    'inline': True
                },
                {
                    'name': 'Total Output',
                    'value': f'{round(total_output / 1000)} kj',
                    'inline': True
                },
                {
                    'name': 'Avg Output',
                    'value': f'{round(avg_output)} watts',
                    'inline': True
                }
            ]
        }

        embeds.append(embed)

    json_body = {
        "content": "Northernlion finished a workout",
        "embeds": embeds,
        "allowed_mentions": {
            "parse": ["roles"]
        }
    }

    channel_id = os.environ.get('PELOTON_CHANNEL_ID')
    try:
        send_discord_request('post', f"channels/{channel_id}/messages", json_body)
        logging.info(f"Successfully posted Peloton ride ids: {[workout['ride']['id'] for workout in workouts]}")
    except DiscordError as e:
        capture_exception(e)


def is_within_interval(timestamp, interval):
    dt = datetime.datetime.fromtimestamp(timestamp)
    now = datetime.datetime.now()
    min_dt = now - interval
    return dt > min_dt


def get_and_post_workouts():
    # Scheduler calls this every interval
    api = PelotonAPI()
    api.login()
    workouts = api.get_workouts('efc2317a6aad48218488a27bf8b0e460')
    interval = datetime.timedelta(hours=24)
    workouts = [workout for workout in workouts if is_within_interval(workout['created_at'], interval)]
    post_workouts(workouts)


if __name__ == "__main__":
    get_and_post_workouts()
