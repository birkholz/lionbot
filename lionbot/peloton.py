import datetime
import logging
import os
import statistics
import sys
from zoneinfo import ZoneInfo

import requests
from sentry_sdk import capture_exception

from lionbot.errors import DiscordError
from lionbot.utils import send_discord_request, init_sentry


init_sentry()


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

        if response.status_code >= 500:
            logging.error(f'Peloton API returned {response.status_code}.')
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
        if workout['status'] != 'COMPLETE' or workout['metrics_type'] != 'cycling':
            continue

        class_id = workout['ride']['id']
        class_url = f'https://members.onepeloton.com/classes/cycling?modal=classDetailsModal&classId={class_id}'

        created_at = datetime.datetime.fromtimestamp(workout['created_at'])
        total_output = workout['total_work']
        if has_no_duration(workout):
            continue

        avg_output = round(total_output / ride_duration_or_actual(workout))

        if workout['ride']['instructor'] is None:
            instructor_name = workout['ride']['description']
            instructor_image = workout['ride']['image_url']
        else:
            instructor_name = workout['ride']['instructor']['name']
            instructor_image = workout['ride']['instructor']['image_url']

        ride_title = workout['ride']['title']

        new_pb = workout['is_total_work_personal_record']
        pb_line = '\n\n ⭐ ️**New Total Work Personal Record!** ⭐ ' if new_pb else ''

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
                    'value': f'{round(total_output / 1000)} kJ',
                    'inline': True
                },
                {
                    'name': 'Avg Output',
                    'value': f'{round(avg_output)} W',
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


def is_previous_day(workout):
    # Determine previous day based on user's own timezone
    if not workout['timezone']:
        return False

    zi = ZoneInfo(workout['timezone'])
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    # midnight yesterday
    min_dt = datetime.datetime.combine(yesterday, datetime.time.min).replace(tzinfo=zi)
    # 23:59:59 yesterday
    max_dt = datetime.datetime.combine(yesterday, datetime.time.max).replace(tzinfo=zi)

    dt = datetime.datetime.fromtimestamp(workout['created_at']).replace(tzinfo=zi)
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


def valid_workout(workout):
    if workout['status'] != 'COMPLETE' or has_no_duration(workout) or workout['metrics_type'] != 'cycling':
        return False

    return True


def ride_count_str(totals, workout):
    if workout['user_username'] not in totals:
        return ''

    ride_count = totals[workout['user_username']]['rides']
    return f'({ride_count} ride{plural(ride_count)})'


def pb_list_str(pb_dict):
    pb_list = [
        f'**{round(pb["total_work"] / 1000)}** kJ/{pb["duration"]} mins'
        for pb in pb_dict
    ]
    return ', '.join(pb_list)


def ride_duration_or_actual(workout):
    if workout['ride']['duration']:
        return workout['ride']['duration']

    return workout['end_time'] - workout['start_time']



def post_leaderboard(api, nl_user_id):
    workouts = api.get_workouts(nl_user_id)
    workouts = [
        workout
        for workout in workouts
        if is_previous_day(workout)
    ]

    workouts = filter(valid_workout, workouts)
    # Put in chrono order
    workouts = list(workouts)[::-1]

    rides = {
        workout['ride']['id']: {
            'id': workout['ride']['id'],
            'title': workout['ride']['title'],
            'instructor_name': workout['ride']['instructor']['name'],
            'start_time': workout['start_time'],
            'url': f'https://members.onepeloton.com/classes/cycling?modal='
                   f'classDetailsModal&classId={workout["ride"]["id"]}',
            'workouts': []
        }
        for workout in workouts
    }
    totals = {}
    players_who_pbd = {}

    users = get_users_in_tag(api)

    for user in users:
        user_workouts = api.get_workouts(user['id'])
        user_workouts = filter(valid_workout, user_workouts)

        for workout in user_workouts:
            workout_ride_id = workout['ride']['id']

            if is_previous_day(workout):
                # Did user PB?
                if workout['is_total_work_personal_record']:
                    pb_dict = {
                        'total_work': workout['total_work'],
                        'duration': round(ride_duration_or_actual(workout) / 60)
                    }
                    if user['username'] not in players_who_pbd:
                        players_who_pbd[user['username']] = [pb_dict]
                    else:
                        players_who_pbd[user['username']].append(pb_dict)

                # Calculate user's totals
                if user['username'] not in totals.keys():
                    totals[user['username']] = {
                        'username': user['username'],
                        'output': workout['total_work'],
                        'rides': 1,
                        'duration': round(ride_duration_or_actual(workout) / 60)
                    }
                else:
                    totals[user['username']]['output'] += workout['total_work']
                    totals[user['username']]['rides'] += 1
                    totals[user['username']]['duration'] += round(ride_duration_or_actual(workout) / 60)

            # Add workout to ride leaderboard
            for ride_id, ride in rides.items():
                if workout_ride_id != ride_id:
                    continue

                # was ride recent?
                # These rides can be up to 12 hours before NL
                start_time = datetime.datetime.fromtimestamp(workout['start_time'])
                min_dt = datetime.datetime.fromtimestamp(ride['start_time']) - datetime.timedelta(hours=12)
                if start_time < min_dt:
                    continue

                workout_obj = {
                    'user_username': user['username'],
                    'total_work': workout['total_work'],
                    'is_new_pb': workout['is_total_work_personal_record'],
                }
                rides[ride_id]['workouts'].append(workout_obj)

    embeds = []
    leaderboard_size = os.environ.get('LEADERBOARD_SIZE', 10)

    # Generate leaderboards
    for ride in rides.values():
        # sort by output desc
        ride['workouts'] = sorted(ride['workouts'], key=lambda w: w['total_work'], reverse=True)
        outputs = [w['total_work'] for w in ride['workouts']]
        median_output = statistics.median(outputs)
        mean_output = statistics.mean(outputs)
        rider_count = len(ride['workouts'])
        # cut top
        ride['workouts'] = ride['workouts'][:leaderboard_size]

        desc = f"""Instructor: {ride["instructor_name"]}\r
        NL rode: <t:{ride["start_time"]}:F>\r
        Total riders: **{rider_count}**"""

        embed = {
            'type': 'rich',
            'title': f'{ride["title"]} - Leaderboard',
            'description': desc,
            'url': ride['url'],
            'fields': [
                {
                    'name': f'{humanize(i)} Place',
                    'value': f'{workout["user_username"]} - **{round(workout["total_work"] / 1000)}** kJ'
                             f'{" (⭐ **NEW PB** ⭐)" if workout["is_new_pb"] else ""}'
                             f' {ride_count_str(totals, workout)}'
                }
                for i, workout in enumerate(ride['workouts'])
            ]
        }
        embed['fields'].append({
            'name': 'Median / Average',
            'value': f'**{round(median_output / 1000)}** kJ / **{round(mean_output / 1000)}** kJ'
        })

        embeds.append(embed)

    # Generate endurance leaderboard
    if totals:
        totals = sorted(totals.values(), key=lambda u: u['output'], reverse=True)
        total_riders = len(totals)
        ride_counts = [w["rides"] for w in totals]
        median_ride_count = statistics.median(ride_counts)
        average_ride_count = round(statistics.mean(ride_counts), 2)
        total_output = sum(w['output'] for w in totals)
        totals = totals[:leaderboard_size]
        yesterday = datetime.date.today() - datetime.timedelta(days=1)

        if total_output / 1000000 > 10:
            total_output_str = f'**{round(total_output / 1000000, 2)}** MJ'
        else:
            total_output_str = f'**{round(total_output / 1000)}** kJ'

        embed = {
            'type': 'rich',
            'title': f'Endurance Leaderboard {yesterday.isoformat()}',
            'description': 'Combined output across all of yesterday\'s rides.\r'
                           f'Total riders: **{total_riders}**\r'
                           f'Median/Average ride count: **{median_ride_count}** / **{average_ride_count}**\r'
                           f'Combined Output: {total_output_str}',
            'fields': [
                {
                    'name': f'{humanize(i)} Place',
                    'value': f'{user["username"]} - **{round(user["output"] / 1000)}** kJ ({user["rides"]} '
                             f'ride{plural(user["rides"])} / {user["duration"]} mins)'
                }
                for i, user in enumerate(totals)
            ]
        }

        embeds.append(embed)

    # Generate PB callout
    if players_who_pbd:
        player_callouts = [
            f'{un} ({pb_list_str(u_dict)})'
            for un, u_dict in players_who_pbd.items()
        ]
        player_callouts = sorted(player_callouts, key=lambda x: x.lower())
        desc = ', '.join(player_callouts)
        # Escape double underscore
        desc = desc.replace('__', '\\_\\_')
        embed = {
            'type': 'rich',
            'title': '⭐ Congratulations for the new PBs! ⭐',
            'description': desc
        }
        embeds.append(embed)

    if not embeds:
        return

    json_body = {
        "content": "# \\#TheEggCarton Leaderboards\n"
                   "Ride leaderboards are based on dillwillhill's rides yesterday "
                   "and include all matching rides from 12 hours before the ride until now.\n"
                   "Endurance leaderboards and the PB callout are only yesterday's rides (in your timezone).\n"
                   "See https://discord.com/channels/726598830992261273/1157338211480256573/1172736947526045716 "
                   "for more info.",
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

    leaderboard_user_id = os.environ.get('LEADERBOARD_USER_ID', '9d18f22c927743dfb18ee5a4f91af63f')
    post_leaderboard(api, leaderboard_user_id)


if __name__ == "__main__":
    get_and_post_workouts()
