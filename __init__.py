import re
import time
import random
import traceback
from fuzzywuzzy.process import extractOne as extract_one

from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from .mopidypost import Mopidy

NOTHING_FOUND = (None, 0.0)
PLAYLIST_MAX_LENGTH = 50

def type_to_playlist_type(title_type):
    if title_type.lower() == "the album":
        return 'album'
    elif title_type.lower() == "the track":
        return 'song'
    elif title_type.lower() == "the artist":
        return 'artist'
    elif title_type.lower() == "the band":
        return 'artist'
    elif title_type.lower() == "the playlist":
        return 'playlist'
    else:
        return 'generic'


def shorten_playlist(tracks):
    if len(tracks) > PLAYLIST_MAX_LENGTH:
        return random.sample(tracks, PLAYLIST_MAX_LENGTH)
    else:
        return tracks


class MopidySkill(CommonPlaySkill):
    def __init__(self):
        super(MopidySkill, self).__init__('Mopidy Skill')
        self.mopidy = None
        self.volume_is_low = False
        self.regexes = [
            "(the artist|the group|the band|(something|anything|stuff|music|songs) (by|from)|some) (?P<artist>.+)",
            "(the |)(song|track) (?P<track>.+) (by (?P<artist>.+)|)",
            "the (album|record) (?P<album>.+) (by (?P<artist>.+)|)"
        ]

        path = self.find_resource('phrases.regex')
        if path:
            self.regexes = [line.rstrip('\n') for line in open(path)]
        else:
            self.log.warning("Could not find phrases.regex")

    def _connect(self):
        url = 'http://localhost:6680'
        if self.settings:
            url = self.settings.get('mopidy_url', url)

        try:
            mopidy = Mopidy(url)
        except Exception as err:
            self.log.error("Error: {}".format(err))
            self.log.error(traceback.format_exc())
            self.log.warning('Could not connect to Mopidy server {}'.format(url) )
            return None

        self.log.info('Connected to mopidy server')
        self.cancel_scheduled_event('MopidyConnect')

        return mopidy

    def initialize(self):
        self.log.info('initializing Mopidy skill')
        super(MopidySkill, self).initialize()

        # Setup handlers for playback control messages
        self.add_event('mycroft.audio.service.next', self.handle_next)
        self.add_event('mycroft.audio.service.prev', self.handle_prev)
        self.add_event('mycroft.audio.service.pause', self.handle_pause)
        self.add_event('mycroft.audio.service.resume', self.handle_resume)

        self.mopidy = self._connect()

        self.register_intent_file('currently.playing.intent', self.handle_currently_playing)
        self.register_intent_file('add.to.playlist.intent', self.handle_add_to_playlist)

    def play(self, tracks):
        self.log.info("Adding {} tracks".format(len(tracks)))
        self.mopidy.add_list(tracks)
        self.log.info("playing")
        self.mopidy.play()

    def CPS_match_query_phrase(self, phrase):
        for rx in self.regexes:
            self.log.info(rx)
            match = re.match(rx, phrase)
            self.log.info(match)

            if match:
                artist = None
                album = None
                track = None

                if 'artist' in match.groupdict():
                    artist = match.groupdict()['artist']

                if 'album' in match.groupdict():
                    album = match.groupdict()['album']

                if 'track' in match.groupdict():
                    track = match.groupdict()['track']

                return (phrase, CPSMatchLevel.GENERIC, 
                    {
                        "artist": artist,
                        "album": album,
                        "track": track
                    })                   

        return None

    def CPS_start(self, phrase, data):
        # Need to do the search here, as it's too slow for the timeout in CPS_match_query_phrase
        uri = self.mopidy.gmusic_search(data["artist"], data["album"], data["track"])

        self.log.info("Found URI: {}".format(uri))

        match_string = ""
        if "track" in data:
            match_string = data["track"]
        elif "album" in data:
            match_string = data["album"]
        elif "artist" in data:
            match_string = data["artist"]

        if uri:
            self.speak('Playing {}'.format(match_string))

            self.log.info("Clear List")
            self.mopidy.clear_list()
            self.log.info("Play!")
            self.play([data.uri])
        else:
            self.speak("Could not find {} in Mopidy".format(match_string))

    def handle_next(self, message):
        self.mopidy.next()

    def handle_prev(self, message):
        self.mopidy.previous()

    def handle_pause(self, message):
        self.mopidy.pause()

    def handle_resume(self, message):
        """Resume playback if paused"""
        self.mopidy.resume()

    def lower_volume(self, message):
        self.log.info('lowering volume')
        self.mopidy.lower_volume()
        self.volume_is_low = True

    def restore_volume(self, message):
        self.log.info('maybe restoring volume')
        self.volume_is_low = False
        time.sleep(2)
        if not self.volume_is_low:
            self.log.info('restoring volume')
            self.mopidy.restore_volume()

    def handle_currently_playing(self, message):
        current_track = self.mopidy.currently_playing()
        if current_track is not None:
            self.mopidy.lower_volume()
            time.sleep(1)
            if 'album' in current_track:
                data = {'current_track': current_track['name'],
                        'artist': current_track['album']['artists'][0]['name']}
                self.speak_dialog('currently_playing', data)
            time.sleep(6)
            self.mopidy.restore_volume()

    def handle_add_to_playlist(self, message):
        title = message.data.get('title')
        title_type = message.data.get('type')
        self.log.info(message.data)
        if title is None:
            self.speak_dialog('not_recognised')
        else:
            data = {'playlist': title, 'playlist_type': type_to_playlist_type(title_type)}

            tracks = self.get_matching_tracks(data)
            self.play(tracks)

            self.speak_dialog('added_to_queue', {'title', title})


def create_skill():
    return MopidySkill()
