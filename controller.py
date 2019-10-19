import logging
import os
import traceback

import gi

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
        Gtk.main_quit()
        # TODO update these
        # narrator.is_shutting_down = True
        # narrator.player.stop()
        # narrator.vlc_instance.release()

    def prepare_monitor_figure(self):
        return self.recorder.prepare_monitor_fig()

    def change_mic(self, mic_id):
        # TODO STOP RECORDING
        if self.recorder.is_recording:
            pass

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



