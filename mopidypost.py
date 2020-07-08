import requests
from copy import copy
import json
#from mycroft.util.log import LOG
from fuzzywuzzy.process import fuzz

MOPIDY_API = '/mopidy/rpc'

MATCH_PERCENTAGE = 90

_base_dict = {'jsonrpc': '2.0', 'id': 1, 'params': {}}


class Mopidy(object):
    def __init__(self, url):
        self.timeout = 10
        self.url = url + MOPIDY_API
        self.volume = None
        self.volume_low = 5
        self.volume_high = 15
        # self.clear_list()
        
    def search(self, artist = None, album = None, track = None):

        if (artist == None and album == None and track == None):
            return []

        d = copy(_base_dict)
        d['method'] = 'core.library.search'

        d['params']['uris'] = ["gmusic:"]
        d['params']['query'] = {}

        if (artist != None):
            d['params']['query']['artist'] = [artist]

        if (album != None):
            d['params']['query']['album'] = [album]

        if (track != None):
            d['params']['query']['track'] = [track]

        print(d)

        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=45)
        r = r.json()

        if (track != None):
            filterList = r['result'][0]['tracks']
            for result in filterList:
                if (fuzz.ratio(track, result['name']) < MATCH_PERCENTAGE):
                    continue

                if (artist != None and fuzz.ratio(artist, result['artists'][0]['name']) < MATCH_PERCENTAGE):
                    continue

                if (album != None and fuzz.ratio(album, result['album']['name']) < MATCH_PERCENTAGE):
                    continue
                
                return result['uri']

        elif (album != None):
            filterList = r['result'][0]['albums']
            for result in filterList:
                if (fuzz.ratio(album, result['name']) < MATCH_PERCENTAGE):
                    continue
                
                if (artist != None and fuzz.ratio(artist, result['artists'][0]['name']) < MATCH_PERCENTAGE):
                    continue

                return result['uri']

        elif (artist != None):
            filterList = r['result'][0]['artists']
            for result in filterList:
                if (fuzz.ratio(artist, result['name']) < MATCH_PERCENTAGE):
                    continue

                return result['uri']

        return None

    def find_artist(self, artist):
        d = copy(_base_dict)
        d['method'] = 'core.library.search'
        d['params'] = {'artist': [artist]}
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        return r.json()['result'][1]['artists']

    def get_playlists(self, filter=None):
        d = copy(_base_dict)
        d['method'] = 'core.playlists.as_list'
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        if filter is None:
            return r.json()['result']
        else:
            return [l for l in r.json()['result'] if filter + ':' in l['uri']]

    def find_album(self, album, filter=None):
        d = copy(_base_dict)
        d['method'] = 'core.library.search'
        d['params'] = {'album': [album]}
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        l = [res['albums'] for res in r.json()['result'] if 'albums' in res]
        if filter is None:
            return l
        else:
            return [i for sl in l for i in sl if filter + ':' in i['uri']]

    def find_track(self, track, filter=None):
        d = copy(_base_dict)
        d['method'] = 'core.library.search'
        d['params'] = {'track_name': [track]}
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        l = [res['tracks'] for res in r.json()['result'] if 'tracks' in res]
        if filter is None:
            return l
        else:
            return [i for sl in l for i in sl if filter + ':' in i['uri']]

    def find_exact(self, uris='null'):
        d = copy(_base_dict)
        d['method'] = 'core.library.find_exact'
        d['params'] = {'uris': uris}
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        return r.json()

    def browse(self, uri):
        d = copy(_base_dict)
        d['method'] = 'core.library.browse'
        d['params'] = {'uri': uri}
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        if 'result' in r.json():
            return r.json()['result']
        else:
            return None

    def clear_list(self):
        d = copy(_base_dict)
        d['method'] = 'core.tracklist.clear'
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        return r

    def add_list(self, uri):
        d = copy(_base_dict)
        d['method'] = 'core.tracklist.add'
        if isinstance(uri, str):
            d['params'] = {'uri': uri}
        elif isinstance(uri, list):
            d['params'] = {'uris': uri}
        else:
            return None
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        return r

    def play(self):
        self.restore_volume()
        d = copy(_base_dict)
        d['method'] = 'core.playback.play'
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)

    def next(self):
        d = copy(_base_dict)
        d['method'] = 'core.playback.next'
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)

    def previous(self):
            d = copy(_base_dict)
            d['method'] = 'core.playback.previous'
            r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)

    def stop(self):
        self.pause()

    def currently_playing(self):
        d = copy(_base_dict)
        d['method'] = 'core.playback.get_current_track'
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        return r.json()['result']

    def set_volume(self, percent):
        d = copy(_base_dict)
        d['method'] = 'core.mixer.set_volume'
        d['params'] = {'volume': percent}
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)

    def lower_volume(self):
        self.set_volume(self.volume_low)

    def restore_volume(self):
        self.set_volume(self.volume_high)

    def pause(self):
        d = copy(_base_dict)
        d['method'] = 'core.playback.pause'
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)

    def resume(self):
        d = copy(_base_dict)
        d['method'] = 'core.playback.resume'
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)

    def get_items(self, uri):
        d = copy(_base_dict)
        d['method'] = 'core.playlists.get_items'
        d['params'] = {'uri': uri}
        r = requests.post(self.url, headers={"content-type":"application/json"}, data=json.dumps(d), timeout=self.timeout)
        if 'result' in r.json():
            return [e['uri'] for e in r.json()['result']]
        else:
            return None

    def get_tracks(self, uri):
        tracks = self.browse(uri)
        ret = [t['uri'] for t in tracks if t['type'] == 'track']

        sub_tracks = [t['uri'] for t in tracks if t['type'] != 'track']
        for t in sub_tracks:
            ret = ret + self.get_tracks(t)
        return ret

    def get_local_albums(self):
        p = self.browse('local:directory?type=album')
        return {e['name']: e for e in p if e['type'] == 'album'}

    def get_local_artists(self):
        p = self.browse('local:directory?type=artist')
        return {e['name']: e for e in p if e['type'] == 'artist'}

    def get_local_genres(self):
        p = self.browse('local:directory?type=genre')
        return {e['name']: e for e in p if e['type'] == 'directory'}

    def get_local_track_names(self):
        p = self.browse('local:directory?type=track')
        return {e['name']: e for e in p if e['type'] == 'track'}

    def get_local_playlists(self):
        p = self.get_playlists('m3u')
        return {e['name']: e for e in p}

    def get_spotify_playlists(self):
        p = self.get_playlists('spotify')
        return {e['name'].split('(by')[0].strip().lower(): e for e in p}

    def get_gmusic_albums(self):
        p = self.browse('gmusic:album')
        p = {e['name']: e for e in p if e['type'] == 'directory'}
        return {e.split(' - ')[1]: p[e] for e in p}

    def get_gmusic_artists(self):
        p = self.browse('gmusic:artist')
        return {e['name']: e for e in p if e['type'] == 'directory'}

    def get_gmusic_radio(self):
        p = self.browse('gmusic:radio')
        return {e['name']: e for e in p if e['type'] == 'directory'}
