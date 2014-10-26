# -*- coding: utf-8 -*-


from StringIO import StringIO
from abc import abstractmethod, ABCMeta
from contextlib import closing
from urllib2 import urlopen
from zipfile import ZipFile
import re
import os


class YifySubtitlesLogger:
    """Abstract logger."""

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def debug(self, message):
        """Print a debug message.

        :param message: Message
        :type message: str
        """

    @abstractmethod
    def info(self, message):
        """Print an informative message.

        :param message: Message
        :type message: str
        """

    @abstractmethod
    def warn(self, message):
        """Print a warning message.

        :param message: Message
        :type message: str
        """

    @abstractmethod
    def error(self, message):
        """Print an error message.

        :param message: Message
        :type message: str
        """


class YifySubtitlesListener:
    """Abstract YIFY Subtitles event listener."""

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def on_subtitle_found(self, subtitle):
        """Event handler called when a matching subtitle has been found.

        :param subtitle: Subtitle details
        :type subtitle: dict of [str, str]
        """

    @abstractmethod
    def on_subtitle_downloaded(self, path):
        """Event handler called when a subtitle has been downloaded and unpacked.

        :param path: Subtitle path
        :type path: str
        """


class YifySubtitles:
    """YIFY Subtitles access class."""

    _extensions = ('.ass', '.smi', '.srt', '.ssa', '.sub', '.txt')

    def __init__(self):
        self.listener = None
        """:type: YifySubtitlesListener"""

        self.logger = None
        """:type: YifySubtitlesLogger"""

        self.workdir = None
        """:type: str"""

        self._base_url = 'http://www.yifysubtitles.com'

    def download(self, url, filename):
        """Download a subtitle.

        The on_subtitle_download() method of the registered listener will be called for each downloaded subtitle.

        :param url: URL to subtitle archive
        :type url: str
        :param filename: Path to subtitle file within the archive
        :type filename: str
        """

        path = os.path.join(self.workdir, os.path.basename(filename))

        self.logger.debug('Downloading subtitle archive from {0}'.format(url))
        with closing(urlopen(url)) as f:
            content = StringIO(f.read())

        self.logger.debug('Extracting subtitle to {0}'.format(path))
        with ZipFile(content) as z, closing(open(path, mode='wb')) as f:
            f.write(z.read(filename))

        self.listener.on_subtitle_downloaded(path)

    def search(self, imdb_id, languages):
        """Search movie subtitles from IMDB identifier.

        The on_subtitle_found() method of the registered listener will be called for each found subtitle.

        :param imdb_id: IMDB identifier
        :type imdb_id: str
        :param languages: Accepted languages
        :type languages: list of str
        """

        page = self._fetch_movie_page(imdb_id)
        self._list_subtitles(page, languages)

    def _fetch_movie_page(self, imdb_id):
        """Fetch the movie page for an IMDB identifier.

        :param imdb_id: IMDB identifier
        :type imdb_id: str
        :return: Movie page
        :rtype: unicode
        """

        url = '{0}/movie-imdb/{1}'.format(self._base_url, imdb_id)
        self.logger.debug('Fetching movie page from {0}'.format(url))

        with closing(urlopen(url)) as page:
            encoding = page.info().getparam('charset')
            return unicode(page.read(), encoding)

    def _fetch_subtitle_page(self, link):
        """Fetch a subtitle page.

        :param link: Relative URL to subtitle page
        :type link: str
        :return: Subtitle page
        :rtype: unicode
        """

        url = '{0}{1}'.format(self._base_url, link)
        self.logger.debug('Fetching subtitle page from {0}'.format(url))

        with closing(urlopen(url)) as page:
            encoding = page.info().getparam('charset')
            return unicode(page.read(), encoding)

    def _list_subtitles(self, page, languages):
        """List subtitles from the movie page.

        :param page: Movie page
        :type page: unicode
        :param languages: Accepted languages
        :type languages: list of str
        """

        pattern = re.compile(r'<li data-id=".*?"(?: class="((?:high|low)-rating)")?>\s*'
                             r'<span class="rating">\s*(?:<span.*?>.*?</span>\s*)*</span>\s*'
                             r'<a class="subtitle-page" href="(.*?)">\s*'
                             r'<span class="flag flag-.*?">.*?</span>\s*'
                             r'<span>(.*?)</span>.*?'
                             r'<span class="subdesc">.*?</span>\s*'
                             r'(?:<span class="verified-subtitle" title="verified">.*?</span>\s*)?'
                             r'</a>'
                             r'.*?'
                             r'</li>',
                             re.UNICODE)

        for match in pattern.findall(page):
            language = self._get_subtitle_language(match[2])
            page_url = match[1].encode('utf-8')
            rating = self._get_subtitle_rating(match[0])

            if language in languages:
                page = self._fetch_subtitle_page(page_url)
                subtitle_url = self._get_subtitle_url(page)

                self._list_subtitles_archive({
                    'language': language,
                    'rating': rating,
                    'url': subtitle_url,
                })

            else:
                self.logger.debug('Ignoring {0} subtitle {1}'.format(language, page_url))

    def _list_subtitles_archive(self, archive):
        """List subtitles from a ZIP archive.

        :param archive: ZIP archive URL
        :type archive: dict of [str, str]
        """

        with closing(urlopen(archive['url'])) as f:
            content = StringIO(f.read())

        with ZipFile(content) as f:
            filenames = [
                filename for filename in f.namelist()
                if filename.endswith(self._extensions) and not os.path.basename(filename).startswith('.')
            ]

        for filename in filenames:
            self.logger.debug('Found {0} subtitle {1}:{2}'.format(archive['language'], archive['url'], filename))
            self.listener.on_subtitle_found({
                'filename': filename,
                'language': archive['language'],
                'rating': archive['rating'],
                'url': archive['url'],
            })

    @staticmethod
    def _get_subtitle_language(language):
        """Get the XBMC english name for a YIFY subtitle language.

        :param language: Subtitle language
        :type language: unicode
        :return: XBMC language
        :rtype: str
        """

        return {
            u'Brazilian Portuguese': u'Portuguese (Brazil)',
            u'Farsi/Persian': u'Persian',
        }.get(language, language).encode('utf-8')

    @staticmethod
    def _get_subtitle_rating(rating):
        """Get XBMC subtitle rating.

        :param rating: Subtitles rating
        :type rating: unicode
        :return: Subtitles rating
        :rtype: str
        """

        return {
            u'high-rating': '5',
            u'low-rating': '0',
        }.get(rating, '3')

    @staticmethod
    def _get_subtitle_url(page):
        """Get the subtitle archive URL from the subtitle page.

        :param page: Subtitle page
        :type page: unicode
        :return: Subtitle URL
        :rtype: str
        """

        pattern = re.compile(r'<a href="([^"]*)" class="[^"]*\bdownload-subtitle\b[^"]*">', re.UNICODE)
        match = pattern.search(page)
        return str(match.group(1)) if match else None
