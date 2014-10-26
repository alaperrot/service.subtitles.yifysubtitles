# -*- coding: utf-8 -*-


import os
import sys
import urllib
import shutil

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin


__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode('utf-8')
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode('utf-8')


sys.path.append(__resource__)


from yifysubtitles import YifySubtitles, YifySubtitlesListener, YifySubtitlesLogger


class YifySubtitlesService(YifySubtitlesListener, YifySubtitlesLogger):
    """YIFY Subtitles provider."""

    def __init__(self, handle, parameters):
        """Constructor.

        :param handle: XBMC handle
        :type handle: unicode
        :param parameters: Parameter string
        :type parameters: unicode
        """

        super(YifySubtitlesService, self).__init__()

        self._handle = int(handle)
        self._set_parameters(parameters)
        self._set_languages()
        self._cleanup_temp()

        self._provider = YifySubtitles()
        self._provider.listener = self
        self._provider.logger = self
        self._provider.workdir = __temp__

    def run(self):
        """Run the service, performing the requested action."""

        if self._parameters['action'] == 'download':
            self._download(self._parameters['url'], self._parameters['filename'])

        elif self._parameters['action'] == 'search':
            self._search(xbmc.Player().getVideoInfoTag().getIMDBNumber())

        self._done()

    def _done(self):
        """Tell XBMC that we're done."""

        self.debug('Done')
        xbmcplugin.endOfDirectory(self._handle)

    def _download(self, url, filename):
        self._provider.download(url, filename)

    def _search(self, imdb_id):
        self._provider.search(imdb_id, self._languages)

    def on_subtitle_found(self, subtitle):
        self.info('Found {0} subtitle {1}:{2}'.format(subtitle['language'], subtitle['url'], subtitle['filename']))

        list_item = xbmcgui.ListItem(
            label=subtitle['language'],
            label2=os.path.basename(subtitle['filename']),
            iconImage=subtitle['rating'],
            thumbnailImage=xbmc.convertLanguage(subtitle['language'], xbmc.ISO_639_1),
        )

        list_item.setProperty('sync', 'false')
        list_item.setProperty('hearing_imp', 'false')

        url = 'plugin://{0}/?action=download&url={1}&filename={2}'.format(
            __scriptid__,
            subtitle['url'],
            subtitle['filename']
        )

        xbmcplugin.addDirectoryItem(handle=self._handle, url=url, listitem=list_item, isFolder=False)

    def on_subtitle_downloaded(self, path):
        self.info('Subtitle {0} downloaded'.format(path))

        list_item = xbmcgui.ListItem(label=path)
        xbmcplugin.addDirectoryItem(handle=self._handle, url=path, listitem=list_item, isFolder=False)

    def debug(self, message):
        xbmc.log(u'{0} - {1}'.format(u'YIFY Subtitles', message).encode('utf-8'), level=xbmc.LOGDEBUG)

    def info(self, message):
        xbmc.log(u'{0} - {1}'.format(u'YIFY Subtitles', message).encode('utf-8'), level=xbmc.LOGINFO)

    def warn(self, message):
        xbmc.log(u'{0} - {1}'.format(u'YIFY Subtitles', message).encode('utf-8'), level=xbmc.LOGWARNING)

    def error(self, message):
        xbmc.log(u'{0} - {1}'.format(u'YIFY Subtitles', message).encode('utf-8'), level=xbmc.LOGERROR)

    @staticmethod
    def _cleanup_temp():
        """Cleanup temporary folder."""

        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)

    def _set_languages(self):
        """Set accepted languages."""

        self._languages = []
        self._languages_codes = []
        if 'languages' in self._parameters:
            for language in urllib.unquote(self._parameters['languages']).decode('utf-8').split(','):
                self._languages.append(xbmc.convertLanguage(language, xbmc.ENGLISH_NAME))
                self._languages_codes.append(xbmc.convertLanguage(language, xbmc.ISO_639_1))

    def _set_parameters(self, parameters):
        """Set parameters from parameter string.

        :param parameters: Parameter string from the command line
        :type parameters: unicode
        """

        self._parameters = {}
        if len(parameters) >= 2:
            cleaned_parameters = parameters.replace('?', '')
            if cleaned_parameters[-1] == '/':
                cleaned_parameters = cleaned_parameters[:-2]
            for parameter in cleaned_parameters.split('&'):
                parameter_name, parameter_value = parameter.split('=', 1)
                self._parameters[parameter_name] = parameter_value


service = YifySubtitlesService(sys.argv[1], sys.argv[2])
service.run()
