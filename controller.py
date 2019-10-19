import ctypes
import logging
import os
import sys
import traceback

import gi
import vlc

from recordings import Recordings

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from recorder import Recorder
from settings import Settings

LOG = logging.getLogger('epic_narrator.recorder')


class Controller:
    def __init__(self):
        self.settings = Settings()
        self.recorder = self.create_recorder()
        self.recordings = None
        self.video_player = None
        self.video_length = None
        self.is_video_loaded = False
        self.video_path = None  # TODO load things from settings
        self.output_path = None
        self.vlc_instance = None
        self.player = None
        self.rec_player = None

    def create_recorder(self):
        saved_microphone = self.settings.get_setting('microphone')

        if saved_microphone is not None:
            try:
                recorder = Recorder(device_id=saved_microphone)
            except Exception:
                recorder = Recorder()
                default_mic_device = Recorder.get_default_device()

                LOG.error('Could not use device with ID {}. This is likely due to a saved configuration '
                          'that is no longer available '
                          '(e.g. you used a device that is not plugged anymore).'
                          'Using default mic with ID {} now'.format(saved_microphone, default_mic_device))
                self.settings.update_settings(microphone=default_mic_device)
        else:
            recorder = Recorder()

        recorder.stream.start()

        return recorder

    def get_mic_devices(self):
        return Recorder.get_devices()

    def get_current_mic_device(self):
        return self.recorder.device_id

    def get_setting(self, key, default_value):
        setting = self.settings.get_setting(key)
        return setting if setting is not None else default_value

    def get_video_length(self):
        if self.video_length is None:
            if self.video_player is None:
                return 0
            else:
                pass # TODO get length from video player
        else:
            return self.video_length

    def set_video_length(self, video_length):
        self.video_length = video_length

    def get_recorder_data(self):
        return self.recorder.q.get_nowait()

    def is_recording(self):
        return self.recorder.is_recording

    def prepare_monitor_fig(self):
        return self.recorder.prepare_monitor_fig()

    def shutting_down(self, *args):
        '''
        if self.is_video_loaded:
            self.settings.update_settings(last_video_position=self.player.get_time())
        '''

        self.recorder.close_stream()
        self.player.stop()
        self.vlc_instance.release()
        Gtk.main_quit()

    def change_mic(self, mic_id):
        if self.recorder.is_recording:
            self.recorder.stop_recording()

        try:
            self.recorder.change_device(mic_id)
            self.recorder.stream.start()  # starts the microphone stream
            self.settings.update_settings(microphone=mic_id)
            return True
        except Exception:
            LOG.error(traceback.format_exc())
            return False

    def get_recorder_window_size(self):
        return self.recorder.get_window_size()

    def video_selected(self, video_path, widget):
        self.video_path = video_path

        video_folder = os.path.dirname(video_path)
        saved_output = self.get_setting('output_path', None)

        if saved_output is None or not os.path.exists(Recordings.get_recordings_path_for_video(saved_output,
                                                                                               video_path)):
            sf = saved_output if saved_output is not None and os.path.exists(saved_output) else video_folder
            output_path = widget.choose_output_folder(sf)
        else:
            output_path = saved_output

        self.settings.update_settings(last_video=video_path)
        self.settings.update_settings(video_folder=video_folder, output_path=output_path)

        self.setup_narrator(self.video_path)

    def ui_video_area_ready(self, widget):
        self.setup_vlc_player(widget)

    def setup_vlc_player(self, widget):
        self.vlc_instance = vlc.Instance('--no-xlib')
        self.player = self.vlc_instance.media_player_new()
        self.set_vlc_window(widget)
        main_events = self.player.event_manager()

        # from lib vlc documentation. Make sure you don't use wait anywhere in the program
        '''
        while LibVLC is active, the wait() function shall not be called, and
        any call to waitpid() shall use a strictly positive value for the first
        parameter (i.e. the PID). Failure to follow those rules may lead to a
        deadlock or a busy loop.
        '''

        # VERY IMPORTANT: functions attached to vlc events will be run in a separate thread,
        # so implement all thread safety things you need, i.e. use glib.idle_add() to do stuff
        #main_events.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.video_moving_handler)
        #main_events.event_attach(vlc.EventType.MediaPlayerEndReached, self.video_ended_handler)

        self.rec_player = self.vlc_instance.media_player_new()
        rec_events = self.rec_player.event_manager()
        #rec_events.event_attach(vlc.EventType.MediaPlayerStopped, self.finished_playing_recording_handler)

        # TODO connect vlc events

    def set_vlc_window(self, widget):
        if sys.platform.startswith('linux'):
            win_id = widget.get_window().get_xid()
            self.player.set_xwindow(win_id)
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
            self.player.set_nsobject(int(handle))
        elif sys.platform.startswith('win'):
            window = widget.get_property('window')
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
            drawingarea_gpointer = ctypes.pythonapi.PyCapsule_GetPointer(window.__gpointer__, None)
            gdkdll = ctypes.CDLL("libgdk-3-0.dll")
            handle = gdkdll.gdk_win32_window_get_handle(drawingarea_gpointer)
            self.player.set_hwnd(int(handle))
        else:
            raise Exception('Cannot deal with this platform: {}'.format(sys.platform))

    def setup_narrator(self, video_path):
        media = self.vlc_instance.media_new_path(video_path)
        self.player.set_mrl(media.get_mrl())

        self.is_video_loaded = False
        # self.mute_video() # TODO fix this

        playback_speed = self.get_setting('playback_speed', 1)

        if type(playback_speed) == float and 0 <= playback_speed <= 1:
            self.player.set_rate(playback_speed)

        #self.player.play()

        self.is_video_loaded = False
        self.mute_video()

        # TODO add mute and playback stuff and continue from here


