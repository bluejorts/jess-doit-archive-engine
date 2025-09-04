# Standard imports
import configparser
import contextlib
import json
import os
import time
import traceback
import importlib.resources as import_resources
from datetime import datetime

# Package imports
import jdae.src.logos as logos
from jdae.src.configmanager import ConfigManager

# 3rd Party imports
import pause
import yt_dlp

with contextlib.redirect_stdout(None):
    # This imports it with no stdout so we do not see the hello message
    import pygame


class JDAE(object):
    # Title to print before logo
    PRGM_TITLE = "Jess' Archive Engine"

    # Naming template for files output by downloader
    OUTPUT_FILE_TMPL = "%(title)s-%(id)s.%(ext)s"

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
        self.archive_history = {}
        self.history_file = None

    def load_archive_history(self):
        """
        Load the archive history from JSON file
        """
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.archive_history = json.load(f)
                print(f"Loaded archive history with {len(self.archive_history)} entries")
            except Exception as e:
                print(f"Warning: Could not load archive history: {e}")
                self.archive_history = {}
        else:
            print("Starting with empty archive history")
            self.archive_history = {}

    def save_archive_history(self):
        """
        Save the archive history to JSON file
        """
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.archive_history, f, indent=2, sort_keys=True)
        except Exception as e:
            print(f"Warning: Could not save archive history: {e}")

    def add_to_history(self, url, info):
        """
        Add a downloaded item to the archive history
        """
        item_id = info.get('id', url)
        self.archive_history[item_id] = {
            'title': info.get('title', 'Unknown'),
            'url': url,
            'uploader': info.get('uploader', 'Unknown'),
            'timestamp': datetime.now().isoformat(),
            'duration': info.get('duration', 0),
            'filesize': info.get('filesize', 0)
        }
        self.save_archive_history()

    def is_archived(self, item_id):
        """
        Check if an item has already been archived
        """
        return item_id in self.archive_history

    def my_hook(self, d):
        """
        Hook for finished downloads
        """
        if d["status"] == "finished":
            print("Done downloading, now converting ...")

    def boot_sequence(self, audio):
        """
        Prints title + logo, and plays startup audio
        """
        print()
        print(self.PRGM_TITLE)
        print(logos.BOOT_LOGO_80)

        # Use pygame to play audio across platforms
        # Do not call pygame.init(), we don't need all that
        pygame.mixer.init()
        pygame.mixer.music.load(audio)
        pygame.mixer.music.play()
        while pygame.mixer.get_busy():
            time.sleep(1)

        print("\nStarting automated archive client")

    def download_from_url(self, ytdl, url):
        """
        Download all relevant media from url

        Skips media that has already been downloaded
        """
        try:
            # First extract info to check what needs downloading
            info = ytdl.extract_info(url, download=False)
            
            if info is None:
                return
            
            # Check if it's a playlist or single track
            if 'entries' in info:
                # It's a playlist
                new_items = []
                skipped_count = 0
                
                for entry in info['entries']:
                    if entry and not self.is_archived(entry.get('id', '')):
                        new_items.append(entry)
                    else:
                        skipped_count += 1
                
                if skipped_count > 0:
                    print(f"Skipping {skipped_count} already archived items")
                
                if new_items:
                    print(f"Found {len(new_items)} new items to download")
                    # Download new items
                    for entry in new_items:
                        self.current_url = entry.get('url', url)
                        self.current_info = entry
                        try:
                            ytdl.download([entry['url']])
                            self.add_to_history(entry['url'], entry)
                        except Exception as e:
                            print(f"Error downloading {entry.get('title', 'item')}: {e}")
                else:
                    print("All items already archived, nothing to download")
            else:
                # It's a single track
                item_id = info.get('id', url)
                if self.is_archived(item_id):
                    print(f"Already archived: {info.get('title', url)}")
                else:
                    self.current_url = url
                    self.current_info = info
                    ytdl.download([url])
                    self.add_to_history(url, info)
                    
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

    def main(self):
        """
        Main JDAE program logic. Starts up and runs archive automation.
        """
        # Read settings and url list from config files
        url_list = self.cm.get_url_list()
        audio = self.cm.get_boot_audio()
        output_dir = self.cm.get_output_dir()
        archive_wait_time = self.cm.get_archive_freq()
        oauth = self.cm.get_oauth()
        req_int = self.cm.get_sleep_interval_requests()
        list_formats = self.cm.get_listformats()
        embed_metadata = self.cm.get_embed_metadata()

        # Print boot sequence and play audio
        if not self.cm.get_skip_intro():
            self.boot_sequence(audio)

        # Print list of pages to user that will be processed
        print("\nMonitoring the following pages:")
        for url in url_list:
            print(f" - {url}")

        # Construct output path template
        outtmpl = f"{output_dir}/archive/%(playlist)s/{self.OUTPUT_FILE_TMPL}"
        print(f"\n######\nARCHIVE OUTPUT DIRECTORY: {outtmpl}")
        
        # Initialize archive history file path
        self.history_file = os.path.join(output_dir, "archive_history.json")
        self.load_archive_history()

        if self.cm.get_hq_en():
            # Set header for HD Soundcould Downloads
            yt_dlp.utils.std_headers["Authorization"] = oauth

        # Options for yt_dlp instance
        ytdl_opts = {
            "format": "ba[acodec!*=opus]",
            "logger": self.YTDLLogger(),
            "outtmpl": outtmpl,
            "listformats": list_formats,
            "sleep_interval_requests": req_int,
            "progress_hooks": [self.my_hook],
        }
        
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
            ]
            print("\nMetadata embedding enabled - converting to mp3 with album art and ID3 tags")

        # Time to get started
        print("\nEngine ready - good luck")
        time.sleep(2)
        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
                while True:
                    # For every url in the url_list.ini run yt_dlp operation
                    for url in url_list:
                        print(f"\n######\n[URL] -- {url}\n")

                        # Download all media from url
                        self.download_from_url(ytdl, url)

                        # List all downloads available from url
                        # self.extract_info_url(ytdl, url)
                    print(
                        f"\n######\nArchive pass completed. Will check again in {archive_wait_time}s ({archive_wait_time/3600}h)"
                    )

                    # This is better than time.sleep for large durations
                    # If archive_wait_time is 6 hours and the PC goes into sleep mode after 30 min
                    # time.sleep will still have 5h 30m on the sleep timer
                    # This method ensures that if 6 hours pass in real world time that the wait will be over
                    pause.seconds(archive_wait_time)
        except:
            traceback.print_exc()
            print("\nArchive engine stopped")


if __name__ == "__main__":
    jdae = JDAE()
    jdae.main()
