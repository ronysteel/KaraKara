import os
import random
import re
import json
import shutil
from collections import defaultdict

from pyramid.view import view_config
from pyramid.events import subscriber

from sqlalchemy.orm import joinedload, undefer

from externals.lib.misc import backup
from externals.lib.pyramid_helpers import get_setting
from externals.lib.pyramid_helpers.views.upload import EventFileUploaded

from ..model import DBSession
from ..model.model_tracks import Track
from ..model.actions import last_update

from . import web, action_ok, cache, etag_decorator, generate_cache_key, comunity_only, is_comunity  # action_error,

from ..views.tracks import invalidate_track
from ..templates import helpers as h

import logging
log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------

PATH_SOURCE_KEY = 'static.source'
PATH_BACKUP_KEY = 'static.backup'
PATH_UPLOAD_KEY = 'upload.path'

STATUS_TAGS = {
    'required': (),  # ('category', 'title'),
    'recomended': ('lang',),  # ('artist', ),
    'yellow': ('yellow', 'caution', 'warning', 'problem'),
    'red': ('red', 'broken', 'critical'),
    'black': ('black', 'delete', 'remove', 'depricated'),
    'green': ('green', 'ok', 'checked')
}

STATUS_LIGHT_ORDER = ('black', 'green', 'red', 'yellow')


def get_overall_status(status_keys, status_light_order=STATUS_LIGHT_ORDER):
    for light in status_light_order:
        if light in status_keys:
            return light


#-------------------------------------------------------------------------------
# Cache Management
#-------------------------------------------------------------------------------
LIST_CACHE_KEY = 'comunity_list'
list_cache_timestamp = None

list_version = random.randint(0, 2000000000)
def invalidate_list_cache(request=None):
    global list_version
    list_version += 1
    cache.delete(LIST_CACHE_KEY)


def _generate_cache_key_comunity_list(request):
    global list_version
    return '-'.join([generate_cache_key(request), str(last_update()), str(list_version), str(is_comunity(request))])


#-------------------------------------------------------------------------------
# Events
#-------------------------------------------------------------------------------

@subscriber(EventFileUploaded)
def file_uploaded(event):
    """
    Depricated.
    Files are now updated from processmedia2.
    This can be removed.
    """
    upload_path = get_setting(PATH_UPLOAD_KEY)
    path_source = get_setting(PATH_SOURCE_KEY)

    # Move uploaded files into media path
    uploaded_files = (f for f in os.listdir(upload_path) if os.path.isfile(os.path.join(upload_path, f)))
    for f in uploaded_files:
        shutil.move(
            os.path.join(upload_path, f),
            os.path.join(path_source, f),
        )

    invalidate_list_cache()


#-------------------------------------------------------------------------------
# Community Utils
#-------------------------------------------------------------------------------

class ComunityTrack():
    """
    Tracks are more than just a db entry. They have static data files accociated
    with them.
    These static data files are used to import tracks into the db.
    Rather than just changing our own local db, we need to update modify and manage
    these external static files.

    ComunityTrack is an object that wraps a Track with additional methods to
    manipulate these files.
    """
    _open = open

    @classmethod
    def factory(cls, track, request):
        return ComunityTrack(
            track=track,
            path_source=request.registry.settings[PATH_SOURCE_KEY],
            path_backup=request.registry.settings[PATH_BACKUP_KEY],
            open=cls._open
        )

    def __init__(self, track, path_source, path_backup, open=open):
        """
        Not to be called directly - use factory() instead
        """
        assert path_source
        assert path_backup
        self.path_source = path_source
        self.path_backup = path_backup

        assert track, 'track required'
        if isinstance(track, str):
            assert track != 'undefined'
            self.track_id = track
            self._track_dict = None
        if isinstance(track, dict):
            self.track_id = track['id']
            self._track_dict = track

        self._open = open  # Allow mockable open() for testing

    @property
    def track(self):
        if not self._track_dict:
            self._track_dict = DBSession.query(Track).options(
                joinedload(Track.tags),
                joinedload(Track.attachments),
                joinedload('tags.parent'),
            ).get(self.track_id).to_dict('full')
        return self._track_dict

    @property
    def tag_data_filename(self):
        return "TODO"

    @property
    def tag_data_raw(self):
        try:
            with self._open(self.tag_data_filename, 'r') as tag_data_filehandle:
                return tag_data_filehandle.read()
        except IOError as ex:
            log.error('Unable to load {} - {}'.format(self.tag_data_filename, ex))
            return ''
    @tag_data_raw.setter
    def tag_data_raw(self, tag_data):
        backup(self.tag_data_filename, self.path_backup)
        with self._open(self.tag_data_filename, 'w') as filehandle:
            filehandle.write(tag_data)

    @property
    def tag_data(self):
        return {tuple(line.split(':')) for line in self.tag_data_raw.split('\n')}

    @property
    def subtitles(self):
        return "TODO"
    @subtitles.setter
    def subtitles(self, subtitles):
        pass  # TODO

    @staticmethod
    def track_status(track_dict, status_tags=STATUS_TAGS, func_file_exists=lambda f: True):
        """
        Traffic light status system.
        returns a dict of status and reasons
        This just asserts based on
        """
        status_details = defaultdict(list)

        #func_is_folder(track_dict['source_filename'])
        if track_dict.get('duration', 0) <= 0:
            status_details['red'].append('invalid duration')

        # Tags
        # todo - how do we get requireg tags based on category? dont we have this info in 'search' somewhere?
        #        these should be enforced
        def check_tags(tag_list, status_key, message):
            for t in tag_list:
                if t not in track_dict['tags']:
                    status_details[status_key].append(message.format(t))
        check_tags(status_tags['recomended'], 'yellow', 'tag {0} suggested')
        check_tags(status_tags['required'], 'red', 'tag {0} missing')

        def flag_tags(tag_list, status_key):
            tags = track_dict.get('tags', {})
            for t in tag_list:
                message = ".\n".join(tags.get(t, [])) or (t in tags.get(None, []))
                if message:
                    status_details[status_key].append(message)
        flag_tags(status_tags['black'], 'black')
        flag_tags(status_tags['red'], 'red')
        flag_tags(status_tags['yellow'], 'yellow')
        flag_tags(status_tags['green'], 'green')

        # Lyrics
        # Do not do lyric checks if explicity stated they are not required.
        # Fugly code warning: (Unsure if both of these are needed for the hardsubs check)
        if ('hardsubs' not in track_dict['tags']) and ('hardsubs' not in track_dict['tags'].get(None, [])):
            lyrics = track_dict.get('lyrics', '')
            if not lyrics:
                status_details['red'].append('no lyrics')

        return {
            'status_details': status_details,
            'status': get_overall_status(status_details.keys()),
        }

    @property
    def status(self):
        return self.track_status(self.track, func_file_exists=lambda f: os.path.isfile(os.path.join(self.path_source, f)))


#-------------------------------------------------------------------------------
# Community Views
#-------------------------------------------------------------------------------

@view_config(route_name='comunity')
@web
def comunity(request):
    return action_ok()


@view_config(route_name='comunity_upload')
@web
def comunity_upload(request):
    return action_ok()


@view_config(route_name='comunity_list')
@etag_decorator(_generate_cache_key_comunity_list)
@web
@comunity_only
def comunity_list(request):

    def _comnunity_list():

        def track_dict_to_status(track_dict):
            track_dict['status'] = ComunityTrack.factory(track_dict, request).status
            del track_dict['tags']
            del track_dict['attachments']
            del track_dict['lyrics']
            return track_dict

        # Get tracks from db
        tracks = [
            # , exclude_fields=('lyrics','attachments','image')
            track_dict_to_status(track.to_dict('full')) \
            for track in DBSession.query(Track) \
                .order_by(Track.source_filename) \
                .options( \
                    joinedload(Track.tags), \
                    joinedload(Track.attachments), \
                    joinedload('tags.parent'), \
                    undefer('lyrics'), \
                )
        ]

        # TODO: look at meta
        # TODO: look at path_upload

        return {
            'tracks': tracks,
            # TODO: add further details of currently processing files?
        }

    # Invalidate cache if db has updated
    last_update_timestamp = last_update()
    global list_cache_timestamp
    if list_cache_timestamp is None or last_update_timestamp != list_cache_timestamp:
        list_cache_timestamp = last_update_timestamp
        invalidate_list_cache(request)

    data_tracks = cache.get_or_create(LIST_CACHE_KEY, _comnunity_list)
    return action_ok(data=data_tracks)


@view_config(route_name='comunity_track', request_method='GET')
@web
@comunity_only
def comunity_track(request):
    id = request.matchdict['id']
    log.debug('comunity_track {}'.format(id))
    ctrack = ComunityTrack.factory(id, request)
    return action_ok(data={
        'track': ctrack.track,
        'status': ctrack.status,
        'tag_matrix': {},
        'tag_data': ctrack.tag_data_raw,
        'subtitles': ctrack.subtitles,
    })
    # Todo - should throw action error with details on fail. i.e. if static files unavalable


@view_config(route_name='comunity_track', request_method='POST')
@web
@comunity_only
def comunity_track_update(request):
    id = request.matchdict['id']
    log.debug('comunity_track_update {}'.format(id))
    ctrack = ComunityTrack.factory(id, request)
    # Save tag data
    if 'tag_data' in request.params:
        ctrack.tag_data_raw = request.params['tag_data']

    # TODO: subtitles

    return action_ok()


# A temp hack to allow te updating of tags for searching to be visible in the comunity interface
from .settings import update_settings
COMUNITY_VISIBLE_SETTINGS = ('karakara.print_tracks.fields', 'karakara.search.tag.silent_forced', 'karakara.search.tag.silent_hidden')
@view_config(route_name='comunity_settings')
@web
@comunity_only
def community_settings(request):

    # '{0} -> list' is a hack. This assumes that all data types given to this method are lists
    # This will have to be updated
    update_settings(request.registry.settings, {k: '{0} -> list'.format(v) for k, v in request.params.items() if k in COMUNITY_VISIBLE_SETTINGS})

    return action_ok(data={'settings': {
        setting_key: request.registry.settings.get(setting_key)
        for setting_key in COMUNITY_VISIBLE_SETTINGS
    }})
