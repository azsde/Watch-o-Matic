#!/usr/bin/python3
import argparse
import vlc
import os
import keyboard
import logging
import ctypes

from time import sleep

# VLC Logs Callback
libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('c'))
vsnprintf = libc.vsnprintf

vsnprintf.restype = ctypes.c_int
vsnprintf.argtypes = (
    ctypes.c_char_p,
    ctypes.c_size_t,
    ctypes.c_char_p,
    ctypes.c_void_p,
)

@vlc.CallbackDecorators.LogCb
def log_callback(data, level, ctx, fmt, args):
    # Skip if level is lower than warning
    if level < 3:
        return

    # Format given fmt/args pair
    BUF_LEN = 1024
    outBuf = ctypes.create_string_buffer(BUF_LEN)
    vsnprintf(outBuf, BUF_LEN, fmt, args)

    # Print it out, or do something else
    print('VLC LOG: ' + outBuf.raw.replace(b"\x00",b"").decode())

class Player:

    VIDEO_INDEX_FILE = "video-index.txt"

    def __init__(self, path):
        logger.debug("Creating vlc instance")

        # Create VLC instance
        self.vlc_instance = vlc.Instance("--no-xlib")

        # Redirect VLC logs to callback
        self.vlc_instance.log_set(log_callback, None)

        self.screen_disabled = False

        mp4_files = []
        self.mediaList = self.vlc_instance.media_list_new()
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".mp4"):
                    mp4_files.append(os.path.join(root, file))

        sorted_mp4_files = sorted(mp4_files)

        for file in sorted_mp4_files:
            self.mediaList.add_media(self.vlc_instance.media_new(os.path.join(path, file)))

        self.player = self.vlc_instance.media_list_player_new()
        self.player.set_media_list(self.mediaList)
        self.backend_media_player = self.player.get_media_player()
        self.player.event_manager().event_attach(vlc.EventType.MediaListPlayerStopped, self.on_event)
        self.backend_media_player.event_manager().event_attach(vlc.EventType.MediaPlayerPlaying, self.on_event)
        self.backend_media_player.event_manager().event_attach(vlc.EventType.MediaPlayerEncounteredError, self.on_event)
        # Set the loop option for the media list player
        self.player.set_playback_mode(vlc.PlaybackMode.loop)

    def play_last_played_video(self):
        logger.debug("Play last video")
        try:
            with open(Player.VIDEO_INDEX_FILE, "r") as file:
                index = int(file.read())
                self.player.play_item_at_index(index)
        except FileNotFoundError:
            logger.debug("Video index file not found, starting over.")
            self.play()
            pass

    # Define callback function for media player events
    def on_event(self, event):
        if event.type == vlc.EventType.MediaListPlayerStopped:
            logger.info("Media player is stopped")
        elif event.type == vlc.EventType.MediaPlayerPlaying:
            index = self.get_index_of_current_item()
            media = self.backend_media_player.get_media()
            logger.info(f"Starting video {index} - {media.get_mrl()}")
            self.save_video_index(index)
        elif event.type == vlc.EventType.MediaPlayerEncounteredError:
            logger.e("Event MediaPlayerEncounteredError received")

    def save_video_index(self, index):
        logger.debug(f"Saving video index {index}")
        with open(Player.VIDEO_INDEX_FILE, "w") as file:
            file.write(str(index))

    def play(self):
        logger.debug("Play")
        self.player.play()

    def next(self):
        logger.debug("Next")
        self.player.next()

    def pause(self):
        logger.debug("Pause")
        self.player.pause()

    def previous(self):
        logger.debug("Previous")
        self.player.previous()

    def stop(self):
        logger.debug("Stop")
        self.player.stop()

    def get_state(self):
        return self.player.get_state()

    def get_index_of_current_item(self):
        logger.debug("get_index_of_current_item")
        item = self.backend_media_player.get_media()
        return self.mediaList.index_of_item(item)

    def toggle_play_pause(self):
        logger.debug("toggle_play_pause")
        if (self.player.get_state() == vlc.State.Playing):
            self.pause()
        elif (self.player.get_state() == vlc.State.Paused):
            self.play()

    def toggleScreen(self):
        logger.debug("toggleScreen")
        backlight_file = '/sys/class/backlight/rpi_backlight/bl_power'

        # Read the current backlight state
        with open(backlight_file, 'r') as file:
            current_state = file.read().strip()

        # Toggle the backlight state
        new_state = '0' if current_state == '1' else '1'

        # Write the new backlight state
        with open(backlight_file, 'w') as file:
            file.write(new_state)

        logger.debug(f"Backlight state toggled. New state: {new_state}")

        if (new_state == '1'):
            self.screen_disabled = True
            if (self.get_state() == vlc.State.Playing):
                self.was_playing = True
                logger.debug("Screen off - Pausing playback")
                self.pause()
            else:
                self.was_playing = False
        elif (new_state == '0'):
            self.screen_disabled = False
            if (self.was_playing):
                logger.debug("Screen on - Resuming playback")
                self.play()

    def on_key_press(self, event):
        key = event.name
        if key == '0' and not self.screen_disabled:
            self.toggle_play_pause()
        elif key == '1' and not self.screen_disabled:
           self.previous()
        elif key == '2' and not self.screen_disabled:
            self.next()
        elif key == '3':
            self.toggleScreen()
        elif key == '4':
            self.player.stop()
        else:
            logger.debug("Key not supported : ", key)

    def release(self):
        self.backend_media_player.release()
        self.vlc_instance.release()

if __name__ == '__main__':

    # create logger
    logger = logging.getLogger("watchomatic")
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    fh = logging.FileHandler(r'logs.txt')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("======================")
    logger.info("Starting Watch-o-Matic")
    logger.info("======================")

    # Create the argument parser
    parser = argparse.ArgumentParser()

    # Define the arguments
    parser.add_argument("-i", "--input", help="Main folder containing the video files", required=True)
    args = parser.parse_args()

    player = Player(args.input)
    player.play_last_played_video()

    # Hook keyboard key pressed
    keyboard.on_press(player.on_key_press)

    while (True):
        if (player.get_state() == vlc.State.Stopped):
            logger.info("Player is stopped, exiting")
            break
        elif (player.get_state() == vlc.State.Error):
            logger.e("Player is in error state ! We should do something to reset it, exiting for now ...")
            break
        sleep(0.5)

    player.release()
