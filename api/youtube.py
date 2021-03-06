# -*- coding: utf-8 -*-

import logging
import web_request

# YouTube API key.
YOUTUBE_API_KEY = 'AIzaSyCPQe4gGZuyVQ78zdqf9O5iEyfVLPaRwZg'

# TODO: Allow for logging to be enabled in module.
# TODO: Retrieve more information in one API call.

log = logging.getLogger(__name__)


def youtube_search(search):
    """
    Searches the youtube API for a youtube video matching the search term.

    A json response of ~50 possible items matching the search term will be presented.
    Each video_id will then be checked by youtube_time() until a candidate has been found
    and the resulting dict can be returned.

    :param search: The search term str to search for.
    :return: dict{'type=youtube', 'video_id', 'int(video_time)', 'video_title'} or None on error.
    """

    if search:
        if 'list' in search:
            search = search.split('?list')[0]
        youtube_search_url = 'https://www.googleapis.com/youtube/v3/search?' \
                             'type=video&key=%s' \
                             '&maxResults=50&q=%s&part=snippet' % (YOUTUBE_API_KEY, search, )

        api_response = web_request.get_request(youtube_search_url, json=True)

        if api_response['content'] is not None:
            try:
                for item in api_response['content']['items']:
                    video_id = item['id']['videoId']
                    video_title = item['snippet']['title'].encode('ascii', 'ignore')

                    video_time = youtube_time(video_id)
                    if video_time is not None:
                        return {'type': 'youTube', 'video_id': video_id,
                                'video_time': video_time['video_time'], 'video_title': video_title}
            except KeyError as ke:
                log.error(ke, exc_info=True)
                return None
    else:
        return None


def youtube_search_list(search, results=10):
    """
    Searches the API of youtube for videos matching the search term.

    Instead of returning only one video matching the search term, we return a list of candidates.

    :param search: The search term str to search for.
    :param results: int determines how many results we would like on our list
    :return: list[dict{'type=youtube', 'video_id', 'int(video_time)', 'video_title'}] or None on error.
    """
    if search:
        youtube_search_url = 'https://www.googleapis.com/youtube/v3/search?type=video' \
                             '&key=%s' \
                             '&maxResults=50&q=%s&part=snippet' % (YOUTUBE_API_KEY, search, )

        api_response = web_request.get_request(youtube_search_url, json=True)
        if api_response['content'] is not None:
            media_list = []
            try:
                i = 0
                for item in api_response['content']['items']:
                    if i == results:
                        return media_list
                    else:
                        video_id = item['id']['videoId']
                        video_title = item['snippet']['title'].encode('ascii', 'ignore')

                        video_time = youtube_time(video_id)
                        if video_time is not None:
                            media_info = {'type': 'youTube', 'video_id': video_id,
                                          'video_time': video_time['video_time'], 'video_title': video_title}
                            log.debug('YouTube item %s %s' % (i, media_info))
                            media_list.append(media_info)
                            i += 1
            except KeyError as ke:
                log.error(ke, exc_info=True)
                return None
    else:
        return None


def youtube_playlist_search(search, results=5):
    """
    Searches youtube for a playlist matching the search term.
    :param search: str the search term to search to search for.
    :param results: int the number of playlist matches we want returned.
    :return: list[dict{'playlist_title', 'playlist_id'}] or None on failure.
    """
    if search:
        youtube_search_url = 'https://www.googleapis.com/youtube/v3/search?' \
                             'type=playlist&key=%s' \
                             '&maxResults=50&q=%s&part=snippet' % (YOUTUBE_API_KEY, search, )

        api_response = web_request.get_request(youtube_search_url, json=True)
        if api_response is not None:
            play_lists = []
            try:
                for item in api_response['content']['items']:
                    playlist_id = item['id']['playlistId']
                    playlist_title = item['snippet']['title'].encode('ascii', 'ignore')
                    play_list_info = {'playlist_title': playlist_title, 'playlist_id': playlist_id}
                    play_lists.append(play_list_info)
                    if len(play_lists) == results:
                        return play_lists
            except KeyError as ke:
                log.error(ke, exc_info=True)
                return None
    else:
        return None


def youtube_playlist_videos(playlist_id):
    """
    Finds the video info for a given playlist ID.

    The list returned will contain all the videos in the playlist;
    retrieves all video information using pageToken.
    :param playlist_id: str the playlist ID
    :return: list[dict{'type=youTube', 'video_id', 'video_title', 'video_time'}] or None on failure.
    """
    playlist_details_url = 'https://www.googleapis.com/youtube/v3/playlistItems?' \
                           'key=%s&playlistId=%s' \
                           '&maxResults=50&part=contentDetails' % (YOUTUBE_API_KEY, playlist_id, )

    video_list = []
    start_token = True
    non_public = 0

    while start_token:
        api_response = web_request.get_request(playlist_details_url, json=True)
        if api_response is not None:
            try:
                pageToken = str(api_response['content']['nextPageToken'])
                playlist_details_url = 'https://www.googleapis.com/youtube/v3/playlistItems?' \
                                       'key=%s&playlistId=%s' \
                                       '&maxResults=50&part=status,contentDetails&pageToken=%s' % (YOUTUBE_API_KEY, playlist_id, pageToken, )
            except KeyError as ke:
                log.error(ke, exc_info=True)
                start_token = False

            try:
                for item in api_response['content']['items']:
                    if item['status']['privacyStatus'] != "public":
                        non_public += 1

                    else:
                        video_id = item['contentDetails']['videoId']
                        # video_title = item['snippet']['title'].encode('ascii', 'ignore')

                        video_time = youtube_time(video_id)
                        if video_time is not None:
                            info = {'type': 'youTube', 'video_id': video_id,
                                    'video_title': video_time['video_title'], 'video_time': video_time['video_time']}
                            video_list.append(info)
                            # print info['video_title']  # debug only
            except Exception as e:
                log.error(e)
                pass
    return video_list, non_public


def youtube_time(video_id, check=False):
    """
    Youtube helper function to get the video time for a given video id.

    Checks a youtube video id to see if the video is blocked or allowed in the following countries:
    USA, DENMARK, POLAND. If a video is blocked in one of the countries, None is returned.
    If a video is NOT allowed in ONE of the countries, None is returned else the video time will be returned.

    :param check: bool True = checks region restriction. False = no check will be done
    :param video_id: The youtube video id str to check.
    :return: dict{'type=youTube', 'video_id', 'video_time', 'video_title'} or None
    """

    youtube_details_url = 'https://www.googleapis.com/youtube/v3/videos?' \
                          'id=%s&key=%s&part=contentDetails,snippet' % (video_id, YOUTUBE_API_KEY, )

    api_response = web_request.get_request(youtube_details_url, json=True)

    if api_response is not None:
        try:
            if len(api_response['content']['items']) is not 0:
                contentdetails = api_response['content']['items'][0]['contentDetails']
                if check:
                    if 'regionRestriction' in contentdetails:
                        if 'blocked' in contentdetails['regionRestriction']:
                            if ('US' or 'DK' or 'PL') in contentdetails['regionRestriction']['blocked']:
                                log.info('%s is blocked in: %s' % (video_id, contentdetails['regionRestriction']['blocked']))
                                return None
                        if 'allowed' in contentdetails['regionRestriction']:
                            if ('US' or 'DK' or 'PL') not in contentdetails['regionRestriction']['allowed']:
                                log.info('%s is allowed in: %s' % (video_id, contentdetails['regionRestriction']['allowed']))
                                return None

                video_time = convert_to_millisecond(contentdetails['duration'])
                video_title = api_response['content']['items'][0]['snippet']['title'].encode('ascii', 'ignore')

                return {'type': 'youTube', 'video_id': video_id, 'video_time': video_time, 'video_title': video_title}
            return None
        except KeyError as ke:
            log.error(ke, exc_info=True)
            return None


def convert_to_millisecond(duration):
    """
    Converts a ISO 8601 duration str to milliseconds.

    :param duration: The ISO 8601 duration str
    :return:  int milliseconds
    """

    duration_string = duration.replace('PT', '').upper()
    seconds = 0
    number_string = ''

    for char in duration_string:
        if char.isnumeric():
            number_string += char
        if char == 'H':
            seconds += (int(number_string) * 60) * 60
            number_string = ''
        if char == 'M':
            seconds += int(number_string) * 60
            number_string = ''
        if char == 'S':
            seconds += int(number_string)
    return seconds * 1000
