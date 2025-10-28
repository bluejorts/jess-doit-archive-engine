# Standard imports
import configparser
import contextlib
import glob
import os
import signal
import sys
import time
import traceback

# Package imports
import jdae.src.logos as logos
from jdae.src.configmanager import ConfigManager

# 3rd Party imports
import yt_dlp
from mutagen.id3 import ID3, TPE2, COMM
from mutagen.mp3 import MP3


class JDAE(object):
    # Title to print before logo
    PRGM_TITLE = "Jess' Archive Engine"

    # Naming template for files output by downloader
    OUTPUT_FILE_TMPL = "%(title)s-%(uploader)s.%(ext)s"

    # Logger helper class
    class YTDLLogger(object):
        """
        Logger to print yt_dlp output
        """

        print_flag = False

        def debug(self, msg):
            """
            Print out relevant download information from yt_dlp
            """
            if self.print_flag:
                print(msg)
                self.print_flag = False
            elif msg.startswith("[download]"):
                print(msg)
                self.print_flag = True

        def warning(self, msg):
            """
            Print out warning messages from yt_dlp
            """
            print(f"Warning: {msg}")

        def error(self, msg):
            """
            Print out error messages from yt_dlp
            """
            print(f"Error: {msg}")

    def __init__(self):
        """
        Constructor for JDAE
        """
        self.cm = ConfigManager()
        self.shutdown_requested = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals gracefully
        """
        print(f"\n\nReceived signal {signum}. Shutting down gracefully...")
        self.shutdown_requested = True
        sys.exit(0)

    def my_hook(self, d):
        """
        Hook for finished downloads - set file permissions
        """
        if d["status"] == "finished":
            print("Done downloading, now converting ...")
            # Set world read/write permissions on the downloaded file
            if 'filename' in d:
                try:
                    os.chmod(d['filename'], 0o666)  # rw-rw-rw-
                except Exception as e:
                    print(f"Warning: Could not set permissions on {d['filename']}: {e}")

    def boot_sequence(self):
        """
        Prints title + logo
        """
        print()
        print(self.PRGM_TITLE)
        print(logos.BOOT_LOGO_80)
        print("\nStarting automated archive client")

    def download_from_url(self, ytdl, url):
        """
        Download all relevant media from url

        Skips media that has already been downloaded
        """
        try:
            # Let yt-dlp handle everything including duplicate detection
            ytdl.download([url])
        except Exception as e:
            print(f"\nError occurred on page: {url}\n{e}\n")

    def extract_info_url(self, ytdl, url):
        """
        List all media that will be downloaded from url
        """
        try:
            ytdl.extract_info(url, download=False)
        except:
            print(f"\nError occurred on page: {url}\n")

    def fix_id3_tags(self, output_dir, album_artist_override, since_time=None):
        """
        Fix ID3 tags on MP3 files to ensure Album Artist is set correctly.
        This runs outside of yt-dlp to ensure the tags are properly set.

        Args:
            output_dir: Base directory to search for MP3 files
            album_artist_override: Value to set for Album Artist field
            since_time: Only process files modified after this timestamp (optional)
        """
        if not album_artist_override:
            return

        print(f"\nFixing ID3 tags - ensuring Album Artist is set to: {album_artist_override}")

        # Find all MP3 files in the output directory
        mp3_pattern = os.path.join(output_dir, "**", "*.mp3")
        mp3_files = glob.glob(mp3_pattern, recursive=True)

        files_processed = 0
        files_updated = 0

        for mp3_file in mp3_files:
            # Skip if we have a time filter and file is too old
            if since_time and os.path.getmtime(mp3_file) < since_time:
                continue

            try:
                # Load the MP3 file
                audio = MP3(mp3_file, ID3=ID3)

                # Check if ID3 tags exist, create if not
                if audio.tags is None:
                    audio.add_tags()

                # Get current album artist value
                current_album_artist = None
                if 'TPE2' in audio.tags:
                    current_album_artist = str(audio.tags['TPE2'])

                # Only update if different
                if current_album_artist != album_artist_override:
                    # Set the Album Artist (TPE2 frame)
                    audio.tags['TPE2'] = TPE2(encoding=3, text=album_artist_override)
                    audio.save()
                    files_updated += 1
                    print(f"  Updated: {os.path.basename(mp3_file)}")

                files_processed += 1

            except Exception as e:
                print(f"  Warning: Could not update ID3 tags for {mp3_file}: {e}")

        if files_processed > 0:
            print(f"\nID3 tag fixing complete: Processed {files_processed} files, updated {files_updated} files")

    def main(self):
        """
        Main JDAE program logic. Starts up and runs archive automation.
        """
        # Read settings and url list from config files
        url_list = self.cm.get_url_list()
        output_dir = self.cm.get_output_dir()
        archive_wait_time = self.cm.get_archive_freq()
        oauth = self.cm.get_oauth()
        req_int = self.cm.get_sleep_interval_requests()
        list_formats = self.cm.get_listformats()
        embed_metadata = self.cm.get_embed_metadata()
        album_artist_override = self.cm.get_album_artist_override()

        # Print boot sequence
        if not self.cm.get_skip_intro():
            self.boot_sequence()

        # Print list of pages to user that will be processed
        print("\nMonitoring the following pages:")
        for url in url_list:
            print(f" - {url}")

        # Construct output path template
        # Use playlist/album name if available, otherwise use 'tracks' for individual tracks
        # The playlist_title fallback ensures we get a folder name even for single tracks
        outtmpl = f"{output_dir}/%(playlist,playlist_title,uploader,channel|tracks)s/{self.OUTPUT_FILE_TMPL}"
        print(f"\n######\nARCHIVE OUTPUT DIRECTORY: {output_dir}")
        
        # Check for cookies.txt file in archive directory
        cookies_file = os.path.join(output_dir, "cookies.txt")
        if os.path.exists(cookies_file):
            print(f"Found cookies.txt - will use for authenticated downloads")
        else:
            cookies_file = None

        if self.cm.get_hq_en():
            # Set header for HD Soundcould Downloads
            yt_dlp.utils.std_headers["Authorization"] = oauth

        # Build parse_metadata list based on configuration
        parse_metadata = [
            # Artist is always the track uploader/creator
            "%(artist|creator|uploader|uploader_id)s:%(artist)s",
            # Album is playlist name (if from playlist)
            "%(playlist|playlist_title)s:%(album)s",
            # Map description to comment field
            "%(description)s:%(comment)s",
            # Map the original webpage URL to author URL field
            "%(webpage_url)s:%(author_url)s",
        ]
        
        # Add album artist mapping
        if album_artist_override:
            # Use the override value for album artist
            parse_metadata.append(f".*:%(album_artist)s:{album_artist_override}")
        else:
            # Use playlist creator or fall back to track uploader
            parse_metadata.append("%(playlist_uploader|channel|uploader)s:%(album_artist)s")
        
        # Options for yt_dlp instance
        ytdl_opts = {
            "format": "ba[acodec!*=opus]",
            "logger": self.YTDLLogger(),
            "outtmpl": outtmpl,
            "listformats": list_formats,
            "sleep_interval_requests": req_int,
            "progress_hooks": [self.my_hook],
            "download_archive": os.path.join(output_dir, "download_archive.txt"),  # Track downloaded videos
            "ignoreerrors": True,  # Continue on download errors
            "parse_metadata": parse_metadata,
        }
        
        # Add cookies file if present
        if cookies_file:
            ytdl_opts["cookiefile"] = cookies_file
        
        # Add metadata embedding options if enabled
        if embed_metadata:
            # Convert to mp3 format when metadata embedding is enabled for better compatibility
            ytdl_opts["writethumbnail"] = True
            ytdl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",  # 0 means best quality (VBR)
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                    "already_have_thumbnail": False,
                },
                {
                    "key": "Exec",
                    "exec_cmd": "chmod 666 {}",  # Set world read/write after processing
                    "when": "after_move"
                },
            ]
            print("\nMetadata embedding enabled - converting to mp3 with album art and ID3 tags")
        else:
            # Even without metadata, ensure proper permissions
            ytdl_opts["postprocessors"] = [
                {
                    "key": "Exec",
                    "exec_cmd": "chmod 666 {}",  # Set world read/write after download
                    "when": "after_move"
                },
            ]

        # Time to get started
        print("\nEngine ready - good luck")
        time.sleep(2)
        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
                while not self.shutdown_requested:
                    # Track the start time of this archive pass
                    pass_start_time = time.time()

                    # For every url in the url_list.ini run yt_dlp operation
                    for url in url_list:
                        if self.shutdown_requested:
                            break
                        print(f"\n######\n[URL] -- {url}\n")

                        # Download all media from url
                        self.download_from_url(ytdl, url)

                        # List all downloads available from url
                        # self.extract_info_url(ytdl, url)

                    if self.shutdown_requested:
                        break

                    # Fix ID3 tags on newly downloaded files
                    # Only process files modified since the start of this pass
                    self.fix_id3_tags(output_dir, album_artist_override, since_time=pass_start_time)

                    print(
                        f"\n######\nArchive pass completed. Will check again in {archive_wait_time}s ({archive_wait_time/3600}h)"
                    )

                    # Use shorter sleep intervals to check for shutdown
                    # This allows for quicker response to shutdown signals
                    wait_end = time.time() + archive_wait_time
                    while time.time() < wait_end and not self.shutdown_requested:
                        time.sleep(1)  # Check every second for shutdown
        except Exception as e:
            print(f"\nError: {e}")
            traceback.print_exc()
            print("\nArchive engine stopped")
            sys.exit(1)


if __name__ == "__main__":
    jdae = JDAE()
    jdae.main()
