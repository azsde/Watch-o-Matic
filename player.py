#!/usr/bin/python3
import argparse
import vlc
import os
import keyboard

from time import sleep

class Player:

    VIDEO_INDEX_FILE = "video-index.txt"

    def __init__(self):
        # Create VLC instance
        self.vlc_instance = vlc.Instance("--no-xlib")
        self.screen_disabled = False

    def createPlaylist(self, path):
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
        self.player.event_manager().event_attach(vlc.EventType.MediaListPlayerStopped, self.on_event)
        self.player.get_media_player().event_manager().event_attach(vlc.EventType.MediaPlayerPlaying, self.on_event)
        # Set the loop option for the media list player
        self.player.set_playback_mode(vlc.PlaybackMode.loop)

    def play_last_played_video(self):
        try:
            with open(Player.VIDEO_INDEX_FILE, "r") as file:
                index = int(file.read())
                self.player.play_item_at_index(index)
        except FileNotFoundError:
            self.play()
            pass


    # Define callback function for media player events
    def on_event(self, event):
        if event.type == vlc.EventType.MediaListPlayerStopped:
            print("Media player is stopped")
        elif event.type == vlc.EventType.MediaPlayerPlaying:
            self.save_video_index(self.get_index_of_current_item())

    def save_video_index(self, index):
        with open(Player.VIDEO_INDEX_FILE, "w") as file:
            file.write(str(index))

    def play(self):
        self.player.play()

    def next(self):
        self.player.next()

    def pause(self):
        self.player.pause()

    def previous(self):
        self.player.previous()

    def stop(self):
        self.player.stop()

    def get_state(self):
        return self.player.get_state()

    def get_index_of_current_item(self):
        item = self.player.get_media_player().get_media()
        return self.mediaList.index_of_item(item)

    def toggle_play_pause(self):
        if (self.player.get_state() == vlc.State.Playing):
            self.pause()
        elif (self.player.get_state() == vlc.State.Paused):
            self.play()

    def toggleScreen(self):
        print("toggleScreen")
        backlight_file = '/sys/class/backlight/rpi_backlight/bl_power'

        # Read the current backlight state
        with open(backlight_file, 'r') as file:
            current_state = file.read().strip()

        # Toggle the backlight state
        new_state = '0' if current_state == '1' else '1'

        # Write the new backlight state
        with open(backlight_file, 'w') as file:
            file.write(new_state)

        print(f"Backlight state toggled. New state: {new_state}")

        if (new_state == '1'):
            self.screen_disabled = True
            self.player.pause()
        elif (new_state == '0'):
            self.screen_disabled = False
            self.player.play()

    def on_key_press(self, event):
        key = event.name
        if key == '0' and not self.screen_disabled:
            self.toggle_play_pause()
        elif key == '1' and not self.screen_disabled:
           self.next()
        elif key == '2' and not self.screen_disabled:
            self.previous()
        elif key == '3':
            self.toggleScreen()
        elif key == '4':
            self.player.stop()
        else:
            print("Key not supported : ", key)

    def release(self):
        self.vlc_instance.release()

if __name__ == '__main__':

    # Create the argument parser
    parser = argparse.ArgumentParser()

    # Define the arguments
    parser.add_argument("-i", "--input", help="Main folder containing the video files", required=True)
    args = parser.parse_args()

    player = Player()
    player.createPlaylist(args.input)
    player.play_last_played_video()

    # Hook keyboard key pressed
    keyboard.on_press(player.on_key_press)

    while (player.get_state() != vlc.State.Stopped):
        sleep(0.5)
    player.release()
