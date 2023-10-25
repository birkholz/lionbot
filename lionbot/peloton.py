import datetime
import logging
import os
import sys

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

        if response.status_code == 403:
            # Private user, must accept follow to view workouts
            return []

        if response.status_code == 503:
            logging.error('Peloton API returned 503.')
            sys.exit(1)

        return response.json()['data']

    def get_users_in_tag(self, tag, after=None):
        request_url = 'https://gql-graphql-gateway.prod.k8s.onepeloton.com/graphql'
        body = {
            'operationName': 'TagDetail',
            'query': 'query TagDetail($tagName: String!, $after: Cursor) {tag(tagName: $tagName) {name followingCount assets { backgroundImage { location __typename } detailBackgroundImage { location __typename } __typename } users(after: $after) { totalCount edges { node { id username assets { image { location __typename } __typename } followStatus protectedFields { ... on UserProtectedFields { totalWorkoutCounts __typename } ... on UserPrivacyError { code message __typename } __typename } __typename } __typename } pageInfo { hasNextPage endCursor __typename } __typename } __typename } }',
            'variables': {
                'tagName': tag
            }
        }
        if after:
            body['variables']['after'] = after

        response = self.API.post(request_url, json=body)

        if response.status_code == 401:
            self.login()
            return self.get_users_in_tag(tag, after)

        if response.status_code == 503:
            logging.error('Peloton API returned 503.')
            sys.exit(1)

        return response.json()['data']


def post_workouts(api, nl_user_id):
    workouts = api.get_workouts(nl_user_id)
    interval = datetime.timedelta(hours=24)
    workouts = [workout for workout in workouts if is_within_interval(workout['created_at'], interval)]

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
        if duration.seconds == 0:
            continue

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

    if not embeds:
        return

    json_body = {
        "content": "Northernlion finished a workout",
        "embeds": embeds[::-1],
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


def is_previous_day(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp)
    now = datetime.datetime.now()
    max_dt = now - datetime.timedelta(hours=24)
    min_dt = now - datetime.timedelta(hours=48)
    return min_dt < dt < max_dt


def get_users_in_tag(api, after=None):
    data_response = api.get_users_in_tag('TheEggCarton', after=after)
    users = [
        {
            'id': user['node']['id'],
            'username': user['node']['username']
        }
        for user in data_response['tag']['users']['edges']
    ]
    if data_response['tag']['users']['pageInfo']['hasNextPage']:
        after = data_response['tag']['users']['pageInfo']['endCursor']
        users += get_users_in_tag(api, after=after)

    return users


def has_no_duration(workout):
    start_time = datetime.datetime.fromtimestamp(workout['start_time'])
    if not workout['end_time']:
        return True

    end_time = datetime.datetime.fromtimestamp(workout['end_time'])
    duration = end_time - start_time
    if duration.seconds == 0:
        return True

    return False


def humanize(i):
    if i == 0:
        return '1st'
    if i == 1:
        return '2nd'
    if i == 2:
        return '3rd'
    if i >= 3:
        return f'{i+1}th'


def plural(i):
    if i != 1:
        return 's'
    return ''


def post_leaderboard(api, nl_user_id):
    workouts = api.get_workouts(nl_user_id)
    workouts = [
        workout
        for workout in workouts
        if is_previous_day(workout['created_at'])
    ]

    def valid_workout(workout):
        if workout['status'] != 'COMPLETE' or has_no_duration(workout):
            return False

        return True

    workouts = filter(valid_workout, workouts)
    # Put in chrono order
    workouts = list(workouts)[::-1]
    rides = {
        workout['ride']['id']: {
            'id': workout['ride']['id'],
            'title': workout['ride']['title'],
            'instructor_name': workout['ride']['instructor']['name'],
            'start_time': workout['start_time'],
            'air_time': workout['ride']['original_air_time'],
            'url': f'https://members.onepeloton.com/classes/cycling?modal='
                   f'classDetailsModal&classId={workout["ride"]["id"]}',
            'workouts': []
        }
        for workout in workouts
    }
    totals = {}
    players_who_pbd = []

    users = get_users_in_tag(api)

    for user in users:
        user_workouts = api.get_workouts(user['id'])
        user_workouts = filter(valid_workout, user_workouts)

        for workout in user_workouts:
            workout_ride_id = workout['ride']['id']
            for ride_id, ride in rides.items():
                if workout_ride_id != ride_id:
                    continue

                start_time = datetime.datetime.fromtimestamp(workout['start_time'])
                min_dt = datetime.datetime.fromtimestamp(ride['start_time']) - datetime.timedelta(hours=1)
                if start_time < min_dt:
                    continue

                workout_obj = {
                    'user_username': user['username'],
                    'total_work': workout['total_work'],
                    'is_new_pb': workout['is_total_work_personal_record'],
                }
                rides[ride_id]['workouts'].append(workout_obj)

                if workout['is_total_work_personal_record']:
                    players_who_pbd.append(user['username'])

                if user['username'] not in totals.keys():
                    totals[user['username']] = {
                        'username': user['username'],
                        'output': workout['total_work'],
                        'rides': 1
                    }
                else:
                    totals[user['username']]['output'] += workout['total_work']
                    totals[user['username']]['rides'] += 1

    embeds = []

    for _ride_id, ride in rides.items():
        # sort by output desc
        ride['workouts'] = sorted(ride['workouts'], key=lambda w: w['total_work'], reverse=True)
        # cut off top 5
        ride['workouts'] = ride['workouts'][:5]

        desc = f"""Instructor: {ride["instructor_name"]}\r
        Aired: <t:{ride["air_time"]}:F>\r
        NL rode: <t:{ride["start_time"]}:F>"""
        embed = {
            'type': 'rich',
            'title': f'{ride["title"]} - Leaderboard',
            'description': desc,
            'url': ride['url'],
            'fields': [
                {
                    'name': f'{humanize(i)} Place',
                    'value': f'{workout["user_username"]} - **{round(workout["total_work"] / 1000)}** kj'
                             f'{" (⭐ **NEW PB** ⭐)" if workout["is_new_pb"] else ""}'
                             f' ({totals[workout["user_username"]]["rides"]}'
                             f' ride{plural(totals[workout["user_username"]]["rides"])})'
                }
                for i, workout in enumerate(ride['workouts'])
            ]
        }

        embeds.append(embed)

    if totals:
        totals = sorted(totals.values(), key=lambda u: u['output'], reverse=True)
        totals = totals[:10]

        embed = {
            'type': 'rich',
            'title': 'Total Leaderboard',
            'description': 'Total output across all matching rides for the day. Only rides matching NL\'s are counted.',
            'fields': [
                {
                    'name': f'{humanize(i)} Place',
                    'value': f'{user["username"]} - **{round(user["output"] / 1000)}** kj ({user["rides"]} '
                             f'ride{plural(user["rides"])})'
                }
                for i, user in enumerate(totals)
            ]
        }

        embeds.append(embed)

    if players_who_pbd:
        embed = {
            'type': 'rich',
            'title': '⭐ Congratulations for the new PBs! ⭐',
            'description': ', '.join(sorted(set(players_who_pbd)))
        }
        embeds.append(embed)

    if not embeds:
        return

    json_body = {
        "content": f"Here are the leaderboards for yesterday's rides. Private account? Read the pinned message!",
        "embeds": embeds,
        "allowed_mentions": {
            "parse": ["roles"]
        }
    }

    channel_id = os.environ.get('PELOTON_CHANNEL_ID')
    try:
        send_discord_request('post', f"channels/{channel_id}/messages", json_body)
        logging.info(f"Successfully posted leaderboard with ride ids: {rides.keys()}")
    except DiscordError as e:
        capture_exception(e)


def get_and_post_workouts():
    # Scheduler calls this every interval
    api = PelotonAPI()
    api.login()

    nl_user_id = 'efc2317a6aad48218488a27bf8b0e460'

    post_workouts(api, nl_user_id)
    post_leaderboard(api, nl_user_id)


if __name__ == "__main__":
    get_and_post_workouts()
