"""
This module contains code to scrape coordinates for games off of espn for any given game
"""

import pandas as pd
from bs4 import BeautifulSoup
import xml.etree.ElementTree as etree
import re
import hockey_scraper.shared as shared


def event_type(play_description):
    """
    Returns the event type (ex: a SHOT or a GOAL...etc) given the event description 
    
    :param play_description: description of play
    
    :return: event
    """
    events = {'GOAL SCORED': 'GOAL', 'SHOT ON GOAL': 'SHOT', 'SHOT MISSED': 'MISS', 'SHOT BLOCKED': 'BLOCK',
              'PENALTY': 'PENL', 'FACEOFF': 'FAC', 'HIT': 'HIT', 'TAKEAWAY': 'TAKE', 'GIVEAWAY': 'GIVE'}

    event = [events[e] for e in events.keys() if e in play_description]
    return event[0] if event else None


def get_game_ids(response):
    """
    Get game_ids for date from doc
    
    :param response: doc
    
    :return: list of game_ids
    """
    soup = BeautifulSoup(response, 'lxml')

    divs = soup.findAll('div', {'class': "game-header"})
    regex = re.compile(r'id="(\d+)')
    game_ids = [regex.findall(str(div))[0] for div in divs]

    return game_ids


def get_teams(response):
    """
    Extract Teams for date from doc
    
    :param response: doc
    
    :return: list of teams    
    """
    soup = BeautifulSoup(response, 'lxml')

    td = soup.findAll('td', {'class': "team"})
    teams = [shared.get_team(t.get_text().upper()) for t in td if t.get_text() != '']

    # Make a list of both teams for each game
    games = [teams[i:i + 2] for i in range(0, len(teams), 2)]

    return games


def get_espn_date(date):
    """
    Get the page that contains all the games for that day
    
    :param date: YYYY-MM-DD
    
    :return: response 
    """
    page_info = {
        "url": 'http://www.espn.com/nhl/scoreboard?date={}'.format(date.replace('-', '')),
        "name": date,
        "type": "espn_scoreboard",
        "season": shared.get_season(date),
    }
    response = shared.get_file(page_info)

    # If can't get or not there throw an exception
    if not response:
        raise Exception
    else:
        return response


def get_espn_game_id(date, home_team, away_team):
    """
    Scrapes the day's schedule and gets the id for the given game
    Ex: http://www.espn.com/nhl/scoreboard?date=20161024
    
    :param date: format-> YearMonthDay-> 20161024
    :param home_team: home team
    :param away_team: away team
    
    :return: 9 digit game id as a string
    """
    response = get_espn_date(date)
    game_ids = get_game_ids(response)
    games = get_teams(response)

    # Get the game id with the right team for it
    for i in range(len(games)):
        if home_team in games[i] or away_team in games[i]:
            return game_ids[i]


def get_espn_game(date, home_team, away_team, game_id=None):
    """
    Gets the ESPN pbp feed 
    Ex: http://www.espn.com/nhl/gamecast/data/masterFeed?lang=en&isAll=true&gameId=400885300
    
    :param date: date of the game
    :param home_team: home team
    :param away_team: away team
    :param game_id: Game id of we already have it - for live scraping. None if not there
    
    :return: raw xml
    """
    # Get if not provided
    if not game_id:
        game_id = get_espn_game_id(date, home_team.upper(), away_team.upper())

    file_info = {
        "url": 'http://www.espn.com/nhl/gamecast/data/masterFeed?lang=en&isAll=true&gameId={}'.format(game_id),
        "name": game_id,
        "type": "espn_pbp",
        "season": shared.get_season(date),
    }
    response = shared.get_file(file_info)

    if response is None:
        raise Exception

    return response


def parse_event(event):
    """
    Parse each event. In the string each field is separated by a '~'. 
    Relevant for here: The first two are the x and y coordinates. And the 4th and 5th are the time elapsed and period.
    
    :param event: string with info
    
    :return: return dict with relevant info
    """
    info = dict()
    fields = event.split('~')

    # Shootouts screw everything up so don't bother...coordinates don't matter there either way
    if fields[4] == '5':
        return None

    info['xC'] = float(fields[0])
    info['yC'] = float(fields[1])
    info['time_elapsed'] = shared.convert_to_seconds(fields[3])
    info['period'] = fields[4]
    info['event'] = event_type(fields[8].upper())

    return info


def parse_espn(espn_xml):
    """
    Parse feed 
    
    :param espn_xml: raw xml of feed
    
    :return: DataFrame with info
    """
    columns = ['period', 'time_elapsed', 'event', 'xC', 'yC']

    # Occasionally we get malformed XML because of the presence of \x13 characters
    # Let's just replace them with dashes
    espn_xml = espn_xml.replace(u'\x13', '-')

    try:
        tree = etree.fromstring(espn_xml)
    except etree.ParseError:
        shared.print_warning("Espn pbp isn't valid xml, therefore coordinates can't be obtained for this game")
        return pd.DataFrame([], columns=columns)

    events = tree[1]
    plays = [parse_event(event.text) for event in events]
    plays = [play for play in plays if play is not None]    # Get rid of plays that are None

    return pd.DataFrame(plays, columns=columns)


def scrape_game(date, home_team, away_team, game_id=None):
    """
    Scrape the game
    
    :param date: ex: 2016-20-24
    :param home_team: tricode
    :param away_team: tricode
    :param game_id: Only provided for live games.
    
    :return: DataFrame with info 
    """
    try:
        shared.print_warning('Using espn for pbp')
        espn_xml = get_espn_game(date, home_team, away_team, game_id)
    except Exception as e:
        shared.print_warning("Espn pbp for game {a} {b} {c} is either not there or can't be obtained {d}".format(a=date,
                                                                                                    b=home_team,
                                                                                                    c=away_team, d=e))
        return None

    try:
        espn_df = parse_espn(espn_xml)
    except Exception as e:
        shared.print_warning("Error parsing Espn pbp for game {a} {b} {c} {d}".format(a=date, b=home_team, c=away_team, d=e))
        return None

    return espn_df
