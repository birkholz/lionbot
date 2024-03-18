import datetime
import logging
import os
import statistics
import sys
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

import requests
from sentry_sdk import capture_exception

#  from lionbot.errors import DiscordError
#  from lionbot.utils import send_discord_request, init_sentry


#  init_sentry()


test = """
<html id="html" lang="en" class="no-mobile js cssanimations backdropfilter csstransforms supports csstransforms3d csstransitions flexbox flexboxlegacy objectfit object-fit svg touchevents has-no-touch"><!--<![endif]--><head>
	<title>‎Northernlion’s activity • Letterboxd</title>
    <body class="activity activity-stream logged-out vsc-initialized" data-owner="Northernlion">
<header class="site-header js-hide-in-app -searchopen" id="header">
	<div class="site-header-bg"></div>
	<section>
		<h1 class="site-logo"><a href="/" class="logo replace">Letterboxd — Your life in film</a></h1>

		<div class="react-component" data-component-class="globals.comps.NavComponent"><div><nav class="main-nav"><ul class="navitems"><li class="navitem sign-in-menu"><a href="/sign-in/" class="navlink has-icon"><span class="icon"></span><span class="label">Sign in</span></a></li><li class="navitem create-account-menu"><a href="/create-account/" class="navlink has-icon cboxElement"><span class="icon"></span><span class="label">Create account</span></a></li><li class="navitem films-page main-nav-films"><a href="/films/" class="navlink has-icon"><span class="icon"></span><span class="label">Films</span></a></li><li class="navitem lists-page main-nav-lists"><a href="/lists/" class="navlink has-icon"><span class="icon"></span><span class="label">Lists</span></a></li><li class="navitem main-nav-people"><a href="/members/" class="navlink has-icon"><span class="icon"></span><span class="label">Members</span></a></li><li class="navitem main-nav-journal"><a href="/journal/" class="navlink has-icon"><span class="icon"></span><span class="label">Journal</span></a></li></ul></nav></div></div>
	</section>
</header>

<div id="content" class="site-body">
	<div class="content-wrap">
<section class="profile-header js-profile-header -is-mini-nav -outdent" data-person="Northernlion">
	<nav class="profile-navigation">
    </nav>
</section>

<div class="cols-3">
	<section class="col-17 col-main">
		<div id="content-nav" class="tabbed gapless">
			<ul class="sub-nav">

						<li class="selected">
							<a href="/northernlion/activity/">Northernlion</a>
						</li>
						<li>
							<a href="/northernlion/activity/following/">Following</a>
						</li>

			</ul>
		</div>

		<div data-owner="Northernlion" class="activity-table generic-person-activity">
			<div id="activity-table-body">
			<section data-activity-id="6240549242" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/quiz-show/" class="target"> <span class="context"> watched, liked and rated </span> Quiz Show </a> <span class="rating -tiny rated-8"> ★★★★ </span> on Friday <span class="nobr">Jan 19, 2024</span> </p> </div> <time datetime="2024-01-19T18:39:15.010Z" class="time timeago timeago-complete" title="1/19/2024, 1:39:15 PM">7h</time> </section>
		<section data-activity-id="6234916690" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/the-grand-budapest-hotel/" class="target"> <span class="context"> watched, liked and rated </span> The Grand Budapest Hotel </a> <span class="rating -tiny rated-9"> ★★★★½ </span> on Thursday <span class="nobr">Jan 18, 2024</span> </p> </div> <time datetime="2024-01-18T17:26:11.990Z" class="time timeago timeago-complete" title="1/18/2024, 12:26:11 PM">1d</time> </section>
		<section data-activity-id="6229348656" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/reign-of-fire/" class="target"> <span class="context"> watched, liked and rated </span> Reign of Fire </a> <span class="rating -tiny rated-6"> ★★★ </span> on Wednesday <span class="nobr">Jan 17, 2024</span> </p> </div> <time datetime="2024-01-17T17:17:02.065Z" class="time timeago timeago-complete" title="1/17/2024, 12:17:02 PM">2d</time> </section>
		<section data-activity-id="6223364862" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/high-fidelity/" class="target"> <span class="context"> rewatched, liked and rated </span> High Fidelity </a> <span class="rating -tiny rated-7"> ★★★½ </span> on Tuesday <span class="nobr">Jan 16, 2024</span> </p> </div> <time datetime="2024-01-16T17:40:13.455Z" class="time timeago timeago-complete" title="1/16/2024, 12:40:13 PM">3d</time> </section>
		<section data-activity-id="6216924656" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/underwater-2020/" class="target"> <span class="context"> watched and rated </span> Underwater </a> <span class="rating -tiny rated-4"> ★★ </span> on Monday <span class="nobr">Jan 15, 2024</span> </p> </div> <time datetime="2024-01-15T17:13:21.010Z" class="time timeago timeago-complete" title="1/15/2024, 12:13:21 PM">4d</time> </section>
		<section data-activity-id="6209742323" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/the-french-connection/" class="target"> <span class="context"> watched and rated </span> The French Connection </a> <span class="rating -tiny rated-6"> ★★★ </span> on Sunday <span class="nobr">Jan 14, 2024</span> </p> </div> <time datetime="2024-01-14T17:16:07.535Z" class="time timeago timeago-complete" title="1/14/2024, 12:16:07 PM">5d</time> </section>
		<section data-activity-id="6189987311" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/patton/" class="target"> <span class="context"> watched, liked and rated </span> Patton </a> <span class="rating -tiny rated-8"> ★★★★ </span> on Thursday <span class="nobr">Jan 11, 2024</span> </p> </div> <time datetime="2024-01-11T17:18:53.239Z" class="time timeago timeago-complete" title="1/11/2024, 12:18:53 PM">8d</time> </section>
		<section data-activity-id="6177399447" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/the-rock/" class="target"> <span class="context"> watched, liked and rated </span> The Rock </a> <span class="rating -tiny rated-7"> ★★★½ </span> on Tuesday <span class="nobr">Jan 9, 2024</span> </p> </div> <time datetime="2024-01-09T17:19:27.457Z" class="time timeago timeago-complete" title="1/9/2024, 12:19:27 PM">10d</time> </section>
		<section data-activity-id="6170727515" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/the-last-duel-2021/" class="target"> <span class="context"> watched, liked and rated </span> The Last Duel </a> <span class="rating -tiny rated-9"> ★★★★½ </span> on Monday <span class="nobr">Jan 8, 2024</span> </p> </div> <time datetime="2024-01-08T16:54:51.751Z" class="time timeago timeago-complete" title="1/8/2024, 11:54:51 AM">11d</time> </section>
		<section data-activity-id="6162690658" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/master-and-commander-the-far-side-of-the-world/" class="target"> <span class="context"> watched, liked and rated </span> Master and Commander: The Far Side of the World </a> <span class="rating -tiny rated-8"> ★★★★ </span> on Sunday <span class="nobr">Jan 7, 2024</span> </p> </div> <time datetime="2024-01-07T16:11:25.670Z" class="time timeago timeago-complete" title="1/7/2024, 11:11:25 AM">12d</time> </section>
		<section data-activity-id="6160035763" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/kingdom-of-heaven/" class="target"> <span class="context"> watched, liked and rated </span> Kingdom of Heaven </a> <span class="rating -tiny rated-6"> ★★★ </span> on Saturday <span class="nobr">Jan 6, 2024</span> </p> </div> <time datetime="2024-01-07T06:01:24.853Z" class="time timeago timeago-complete" title="1/7/2024, 1:01:24 AM">13d</time> </section>
		<section data-activity-id="6160032658" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/the-creator-2023/" class="target"> <span class="context"> watched and rated </span> The Creator </a> <span class="rating -tiny rated-4"> ★★ </span> on Thursday <span class="nobr">Jan 4, 2024</span> </p> </div> <time datetime="2024-01-07T06:00:53.857Z" class="time timeago timeago-complete" title="1/7/2024, 1:00:53 AM">13d</time> </section>
		<section data-activity-id="6160028661" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> <a href="/northernlion/film/the-martian/" class="target"> <span class="context"> watched, liked and rated </span> The Martian </a> <span class="rating -tiny rated-7"> ★★★½ </span> on Wednesday <span class="nobr">Jan 3, 2024</span> </p> </div> <time datetime="2024-01-07T06:00:13.255Z" class="time timeago timeago-complete" title="1/7/2024, 1:00:13 AM">13d</time> </section>
		<section data-activity-id="6160025733" class="activity-row -basic" style=""> <div class="table-activity-description"> <p class="activity-summary"> <a href="/northernlion/" class="name"><strong>Northernlion</strong></a> rated <a href="/film/sunshine-2007/" class="target">Sunshine</a> <span class="rating -tiny rated-8"> ★★★★ </span> </p> </div> <time datetime="2024-01-07T05:59:44.325Z" class="time timeago timeago-complete" title="1/7/2024, 12:59:44 AM">13d</time> </section>


			<section class="activity-row no-activity-message" style=""><p class="end-of-activity">End of recent activity</p></section></div>
		</div>
	</section>
</div>
		</div>
	</div>
"""


BASE_URL = "https://letterboxd.com"

class Movie:
    def __init__(self, name):
        self.name = name

    def set_timestamp(self, ts):
        self.ts = ts
        return self

    def set_link(self, link):
        self.link = link
        return self

    def set_rating(self, rating):
        self.rating = rating
        return self


class Letterbox:
    def __init__(self, username: str) -> None:
        if not re.match("^[A-Za-z0-9_]*$", username):
            raise Exception("Invalid username")
        self.username = username.lower()

    def __str__(self):
        return self.jsonify()

    def jsonify(self) -> str:
        return json.dumps(self, indent=4,cls=Encoder)

    def fetch_page(self, url: str):
        # This fixes a blocked by cloudflare error i've encountered
        headers = {
            "referer": BASE_URL,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        return requests.get(url, headers=headers).text

    '''
    Example
    <section class="activity-row -basic" data-activity-id="6240549242" style="">
        <div class="table-activity-description">
            <p class="activity-summary">
                <a class="name" href="/northernlion/"><strong>Northernlion</strong></a>
                <a class="target" href="/northernlion/film/quiz-show/">
                    <span class="context"> watched, liked and rated </span> Quiz Show
                </a>
                <span class="rating -tiny rated-8"> ★★★★ </span> on Friday
                <span class="nobr">Jan 19, 2024</span>
            </p>
        </div>
        <time class="time timeago timeago-complete" datetime="2024-01-19T18:39:15.010Z" title="1/19/2024, 1:39:15 PM">
            7h
        </time>
    </section>
    '''
    def parse_movie_info(self, row):
        movie_tag = row.find('a', class_='target')
        if movie_tag is None:
            return None
        movie_link = movie_tag['href']
        movie_name = movie_tag.contents[-1].strip()
        return [movie_name, movie_link]

    def parse_review_time(self, row):
        time_tag = row.find('time', class_='time timeago timeago-complete')
        if time_tag is None:
            return None
        time = time_tag['datetime']
        # TODO can this throw?
        return datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")

    def parse_rating_info(self, row):
        rating_tag = row.find('span', class_='rating -tiny rated-8')
        if rating_tag is None:
            return None
        rating = rating_tag.text.strip()
        return rating

    def parse_activity_row(self, row):
        movie_info = self.parse_movie_info(row)
        time_obj = self.parse_review_time(row)
        rating_info = self.parse_rating_info(row)
        if movie_info is None or time_obj is None or rating_info is None:
            print("{movie_info} {time_obj} {rating_info}")
            return None
        [movie_name, movie_link] = movie_info
        full_movie_link = BASE_URL + movie_link
        return (
                Movie(movie_name)
                .set_timestamp(time_obj)
                .set_link(full_movie_link)
                .set_rating(rating_info)
            )

    def get_and_parse_html(self):
        response = self.fetch_page(BASE_URL + "/" + self.username + "/")
        print(response)
        return BeautifulSoup(response, "html.parser")

    def get_movies(self, bs_result):
        activity_rows = bs_result.find_all('section', class_='activity-row')

        movies = []
        for row in activity_rows:
            pieces = self.parse_activity_row(row)
            # TODO the last row has this issue?
            if pieces is None:
                continue
            movies.append(pieces)
        return movies


    '''
<html>
<body>
			<div class="col-4 gutter-right-1">
				<section class="poster-list -p150 el col viewing-poster-container" data-owner="Northernlion" data-object-id="viewing:516191276" data-object-name="diary entry" >
					<div class="really-lazy-load poster film-poster film-poster-45292 linked-film-poster" data-image-width="150" data-image-height="225" data-film-id="45292" data-film-slug="quiz-show" data-poster-url="/film/quiz-show/image-150/" data-linked="linked" data-target-link="/film/quiz-show/" data-target-link-target="" data-cache-busting-key="71c00321" data-context="hero" data-show-menu="true" data-hide-tooltip="true" > <img src="https://s.ltrbxd.com/static/img/empty-poster-150.d356771f.png" class="image" width="150" height="225" alt="Quiz Show"/> <span class="frame"><span class="frame-title"></span></span> </div>
				</section>
                </div>
</body>
</html>

    '''
    def get_and_parse_poster_html(self, movie_link):
        # TODO this is always empty because letterboxd lazy loads the images
        # probably need to fine the poster elsewhere
        response = self.fetch_page(movie_link)
        return BeautifulSoup(response, "html.parser")

    def fetch_movie_poster(self, movie):
        soup = self.get_and_parse_poster_html(movie.link)
        img_tag = soup.find('img', alt=movie.name)
        poster_url = img_tag['src']
        return poster_url

    def generate_embed_for_movie(self, movie):
        movie_poster = self.fetch_movie_poster(movie)

        embed = {
            'type': 'rich',
            'title': f'{movie.name}',
            'description': '',
            'url': movie.link,
            'thumbnail': {
                'url': movie_poster
            },
            'fields': [
                {
                    'name': 'Date',
                    'value': f'<t:{int(movie.ts.timestamp())}:F>',
                    'inline': True
                },
                                {
                    'name': 'Rating',
                    'value': f'{movie.rating}',
                    'inline': True
                }
            ]
        }
        return embed

    def generate_discord_message(self, movies):
        embeds = []

        for movie in movies:
            emb = self.generate_embed_for_movie(movie)
            if emb is None:
                continue
            embeds.append(emb)

        json_body = {
            "content": "Northernlion rated a movie",
            "embeds": embeds[::-1],
            "allowed_mentions": {
                "parse": ["roles"]
            }
        }

        print(json_body)

        '''
        TODO
        channel_id = os.environ.get('LETTERBOXD_CHANNEL_ID')
        try:
            send_discord_request('post', f"channels/{channel_id}/messages", json_body)
            logging.info(f"Successfully posted Letterboxd review: {[movie.name for movie in movies]}")
        except DiscordError as e:
            capture_exception(e)
       '''

def today_only(movies):
    now = datetime.now()
    return list(filter(lambda x : (now - x.ts) < timedelta(hours=24) , movies))

def fetch_new_ratings():
    letterbox = Letterbox("northernlion")
    pa = letterbox.get_and_parse_html()
    movies = letterbox.get_movies(pa)
    print("movies")
    print(movies)
    movies = today_only(movies)

    # no new movies
    if len(movies) == 0:
        return

    letterbox.generate_discord_message(movies)

if __name__ == "__main__":
    fetch_new_ratings()
