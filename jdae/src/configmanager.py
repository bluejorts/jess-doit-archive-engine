import os


class ConfigManager(object):
    """
    Manages configuration from environment variables
    """

    def __init__(self):
        """
        ConfigManager constructor - validates required environment variables
        """
        # Check for required URL list
        if not os.environ.get('URL_LIST'):
            print("WARNING: URL_LIST environment variable not set. Please set it to a comma-separated list of URLs to archive.")

    def get_url_list(self):
        """
        Returns list of URLs from environment variable
        Expects comma-separated list in URL_LIST env var
        """
        url_string = os.environ.get('URL_LIST', '')
        if not url_string:
            return []
        
        # Split by comma and strip whitespace
        urls = [url.strip() for url in url_string.split(',')]
        # Filter out empty strings
        return [url for url in urls if url]

    def get_skip_intro(self):
        """
        Returns skip intro bool value
        """
        val = os.environ.get('SKIP_INTRO', 'false').lower()
        return val in ['true', '1', 'yes']

    def get_output_dir(self):
        """
        Returns base directory for archive output
        """
        # Default to /archive for Docker, ~/JDAE_OUTPUT for local
        default = '/archive' if os.path.exists('/.dockerenv') else os.path.expanduser('~/JDAE_OUTPUT')
        return os.environ.get('OUTPUT_DIR', default)

    def get_archive_freq(self):
        """
        Returns the number of seconds to wait between archive runs
        """
        # Default to 6 hours
        hours = float(os.environ.get('ARCHIVE_FREQUENCY_HOURS', '6'))
        return int(hours * 3600)

    def get_oauth(self):
        """
        Returns Soundcloud OAuth value to enable HQ downloads
        """
        return os.environ.get('SOUNDCLOUD_OAUTH', '')

    def get_hq_en(self):
        """
        Returns the True/False value for High Quality Enable
        """
        val = os.environ.get('HIGH_QUALITY_ENABLE', 'false').lower()
        return val in ['true', '1', 'yes']

    def get_sleep_interval_requests(self):
        """
        Returns rate limit delay in seconds between requests
        """
        return int(os.environ.get('RATE_LIMIT_SEC', '3'))

    def get_listformats(self):
        """
        Returns listformats bool value for debugging available formats
        """
        val = os.environ.get('LIST_FORMATS', 'false').lower()
        return val in ['true', '1', 'yes']

    def get_embed_metadata(self):
        """
        Returns embed_metadata bool value for enabling metadata and thumbnail embedding
        """
        val = os.environ.get('EMBED_METADATA', 'true').lower()
        return val in ['true', '1', 'yes']

    def get_album_artist_override(self):
        """
        Returns album artist override value if set
        If set, this value will be used as album artist for all downloads
        """
        return os.environ.get('ALBUM_ARTIST_OVERRIDE', '')