import ctypes
import sys
import threading

import vlc
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

class Player:
    def __init__(self, widget, controller):
        self.controller = controller
        self.vlc_instance = vlc.Instance('--no-xlib')
        self.video_player = self.vlc_instance.media_player_new()
        self.video_length = 0
        self.set_vlc_window(widget)
        self.mute_video()
        main_events = self.video_player.event_manager()
        self._seeking_timeout = 0
        self.was_playing_before_seek = None
        self._is_seeking = False
        self.is_dragging = False
        self.seek_step = 500  # milliseconds
        self.seek_refresh = 50  # milliseconds

        # from lib vlc documentation. Make sure you don't use wait anywhere in the program
        '''
        while LibVLC is active, the wait() function shall not be called, and
        any call to waitpid() shall use a strictly positive value for the first
        parameter (i.e. the PID). Failure to follow those rules may lead to a
        deadlock or a busy loop.
        '''

        # VERY IMPORTANT: functions attached to vlc events will be run in a separate thread,
        # so implement all thread safety things you need, i.e. use glib.idle_add() to do stuff
        main_events.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.video_moving_handler)
        # main_events.event_attach(vlc.EventType.MediaPlayerEndReached, self.video_ended_handler)
        main_events.event_attach(vlc.EventType.MediaPlayerLengthChanged, self.video_loaded_handler)

        self.rec_player = self.vlc_instance.media_player_new()
        rec_events = self.rec_player.event_manager()
        # rec_events.event_attach(vlc.EventType.MediaPlayerStopped, self.finished_playing_recording_handler)

        # TODO connect vlc events

    def set_vlc_window(self, widget):
        if sys.platform.startswith('linux'):
            win_id = widget.get_window().get_xid()
            self.video_player.set_xwindow(win_id)
        elif sys.platform.startswith('darwin'):
            # ugly bit to get window if on mac os
            window = widget.get_property('window')
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
            gpointer = ctypes.pythonapi.PyCapsule_GetPointer(window.__gpointer__, None)
            libgdk = ctypes.CDLL("libgdk-3.dylib")
            libgdk.gdk_quartz_window_get_nsview.restype = ctypes.c_void_p
            libgdk.gdk_quartz_window_get_nsview.argtypes = [ctypes.c_void_p]
            handle = libgdk.gdk_quartz_window_get_nsview(gpointer)
            self.video_player.set_nsobject(int(handle))
        elif sys.platform.startswith('win'):
            window = widget.get_property('window')
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
            drawingarea_gpointer = ctypes.pythonapi.PyCapsule_GetPointer(window.__gpointer__, None)
            gdkdll = ctypes.CDLL("libgdk-3-0.dll")
            handle = gdkdll.gdk_win32_window_get_handle(drawingarea_gpointer)
            self.video_player.set_hwnd(int(handle))
        else:
            raise Exception('Cannot deal with this platform: {}'.format(sys.platform))

    def shutting_down(self):
        self.video_player.stop()
        self.rec_player.stop()
        self.vlc_instance.release()

    def load_video(self, video_path):
        media = self.vlc_instance.media_new_path(video_path)
        self.video_player.set_mrl(media.get_mrl())
        self.play_video()  # we need to play the video for a while to get the length in milliseconds,

    def video_loaded_handler(self, *args):
        GLib.idle_add(self.video_loaded)

    def video_loaded(self):
        self.pause_video()
        self.video_length = self.get_video_length()
        self.controller.video_loaded()

    def get_video_length(self):
        return self.video_player.get_length()

    def play_video(self):
        self.video_player.play()

    def pause_video(self):
        self.video_player.set_pause(True)

    def set_speed(self, speed):
        self.video_player.set_rate(speed)

    def mute_video(self):
        self.video_player.audio_set_mute(True)

    def unmute_video(self):
        self.video_player.audio_set_mute(False)

    def get_current_position(self):
        return max(0, self.video_player.get_time())

    def is_playing(self):
        return self.video_player.is_playing()

    def is_mute(self):
        return self.video_player.audio_get_mute()

    def is_seeking(self):
        return self._is_seeking or self._seeking_timeout != 0

    def video_moving_handler(self, *args):
        # this will be run in the main thread when possible
        GLib.idle_add(self.video_moving, priority=GLib.PRIORITY_HIGH)

    def video_moving(self):
        self.controller.signal_sender.emit('video_moving', self.get_current_position(), self.is_seeking())

    def start_seek(self, direction):
        if self.video_player.is_playing():
            self.pause_video()
            self.was_playing_before_seek = True
        else:
            self.was_playing_before_seek = False

        step = self.seek_step if direction == 'forward' else - self.seek_step
        self._seeking_timeout = GLib.timeout_add(self.seek_refresh, self.seek, step)

    def stop_seek(self):
        GLib.source_remove(self._seeking_timeout)
        self._seeking_timeout = 0

        if self.was_playing_before_seek:
            self.play_video()

        self._is_seeking = False

    def seek(self, step):
        seek_pos = self.get_current_position() + step

        if 0 < seek_pos < self.video_length:
            self._is_seeking = True
            self.video_player.set_time(int(seek_pos))
            self.controller.signal_sender.emit('video_moving', self.get_current_position(), self.is_seeking())
            return True
        else:
            return False

    def go_to(self, time_ms):
        self.video_player.set_time(int(time_ms))

    def play_recording(self, recording_path):
        audio_media = self.vlc_instance.media_new_path(recording_path)
        self.rec_player.audio_set_mute(False)  # we need to this every time
        self.rec_player.set_mrl(audio_media.get_mrl())
        self.rec_player.play()
