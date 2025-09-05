# Standard imports
import configparser
import contextlib
import json
import os
import signal
import sys
import time
import traceback
from datetime import datetime

# Package imports
import jdae.src.logos as logos
from jdae.src.configmanager import ConfigManager

# 3rd Party imports
import yt_dlp


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
        self.archive_history = {}
        self.history_file = None
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
        # Save any pending history
        if hasattr(self, 'archive_history') and self.history_file:
            self.save_archive_history()
        sys.exit(0)
    
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
            dir_path = os.path.dirname(self.history_file)
            os.makedirs(dir_path, exist_ok=True)
            # Set directory permissions to be accessible
            try:
                os.chmod(dir_path, 0o777)  # rwxrwxrwx for directories
            except:
                pass
            with open(self.history_file, 'w') as f:
                json.dump(self.archive_history, f, indent=2, sort_keys=True)
            # Set history file permissions
            try:
                os.chmod(self.history_file, 0o666)  # rw-rw-rw- for files
            except:
                pass
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
        output_dir = self.cm.get_output_dir()
        archive_wait_time = self.cm.get_archive_freq()
        oauth = self.cm.get_oauth()
        req_int = self.cm.get_sleep_interval_requests()
        list_formats = self.cm.get_listformats()
        embed_metadata = self.cm.get_embed_metadata()

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
        
        # Initialize archive history file path
        self.history_file = os.path.join(output_dir, "archive_history.json")
        self.load_archive_history()
        
        # Check for cookies.txt file in archive directory
        cookies_file = os.path.join(output_dir, "cookies.txt")
        if os.path.exists(cookies_file):
            print(f"Found cookies.txt - will use for authenticated downloads")
        else:
            cookies_file = None

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
                        
                    print(
                        f"\n######\nArchive pass completed. Will check again in {archive_wait_time}s ({archive_wait_time/3600}h)"
                    )

                    # Use shorter sleep intervals to check for shutdown
                    # This allows for quicker response to shutdown signals
                    wait_end = time.time() + archive_wait_time
                    while time.time() < wait_end and not self.shutdown_requested:
                        time.sleep(1)  # Check every second for shutdown
        except:
            traceback.print_exc()
            print("\nArchive engine stopped")


if __name__ == "__main__":
    jdae = JDAE()
    jdae.main()
