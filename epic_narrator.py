import vlc
import math
import numpy as np
import matplotlib.pyplot as plt
import queue
import gi
from recorder import Recorder
from recordings import Recordings

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_gtk3agg import (FigureCanvasGTK3Agg as FigureCanvas)

plt.switch_backend('GTK3Agg')  # VERY IMPORTANT, OTHERWISE IT CRASHES


def ms_to_timestamp(millis):
    seconds = (millis / 1000) % 60
    minutes = (millis / (1000 * 60)) % 60
    hours = (millis / (1000 * 60 * 60)) % 24

    sec_frac, _ = math.modf(seconds)

    return '{:02d}:{:02d}:{:02d}.{:03d}'.format(int(hours), int(minutes), int(seconds), int(sec_frac*1000))


class EpicAnnotator(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='Epic Annotator')

        self.video_length_ms = 0
        self.seek_step = 500  # 500ms
        self.connect('destroy', Gtk.main_quit)
        self.recorder = Recorder()

    def show(self):
        self.show_all()

    def setup_objects_and_events(self):
        self.file_menu = Gtk.Menu()
        self.load_video_menu_item = Gtk.MenuItem('Load video')
        self.file_menu.append(self.load_video_menu_item)
        self.file_menu_item = Gtk.MenuItem('File')
        self.file_menu_item.set_submenu(self.file_menu)
        self.menu_bar = Gtk.MenuBar()
        self.menu_bar.append(self.file_menu_item)

        self.load_video_menu_item.connect('button-press-event', self.open_file_chooser)

        # icons
        self.seek_backward_image = Gtk.Image.new_from_icon_name('media-seek-backward', Gtk.IconSize.BUTTON)
        self.seek_forward_image = Gtk.Image.new_from_icon_name('media-seek-forward', Gtk.IconSize.BUTTON)
        self.play_image = Gtk.Image.new_from_icon_name('media-playback-start', Gtk.IconSize.BUTTON)
        self.pause_image = Gtk.Image.new_from_icon_name('media-playback-pause', Gtk.IconSize.BUTTON)
        self.mute_image = Gtk.Image.new_from_icon_name('audio-volume-muted', Gtk.IconSize.BUTTON)
        self.unmute_image = Gtk.Image.new_from_icon_name('audio-volume-high', Gtk.IconSize.BUTTON)
        self.mic_image = Gtk.Image.new_from_icon_name('audio-input-microphone', Gtk.IconSize.BUTTON)
        self.record_image = Gtk.Image.new_from_icon_name('media-record', Gtk.IconSize.BUTTON)

        self.slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(0, 0, 100, 5, 10, 0))
        self.slider.connect('change-value', self.slider_moved)
        self.slider.connect('button-press-event', self.slider_clicked)
        self.slider.connect('button-release-event', self.slider_released)
        self.slider.set_hexpand(True)
        self.slider.set_valign(Gtk.Align.START)
        self.slider.set_draw_value(False)
        self.slider.add_mark(1, Gtk.PositionType.TOP, ' ')  # ugly empty mark to draw the necessary space from the start

        # buttons
        self.playback_button = Gtk.Button()
        self.record_button = Gtk.Button()
        self.mute_button = Gtk.Button()
        self.seek_backward_button = Gtk.Button()
        self.seek_forward_button = Gtk.Button()

        self.playback_button.set_image(self.play_image)
        self.record_button.set_image(self.mic_image)
        self.mute_button.set_image(self.unmute_image)
        self.seek_backward_button.set_image(self.seek_backward_image)
        self.seek_forward_button.set_image(self.seek_forward_image)

        self.seek_backward_button.connect('pressed', self.seek_backwards_pressed)
        self.seek_backward_button.connect('released', self.seek_backwards_released)
        self.seek_forward_button.connect('pressed', self.seek_forwards_pressed)
        self.seek_forward_button.connect('released', self.seek_forwards_released)
        self.playback_button.connect('clicked', self.toggle_player_playback)
        self.record_button.connect('clicked', self.record)
        self.mute_button.connect('clicked', self.toggle_audio)

        # video area
        self.video_area = Gtk.DrawingArea()
        self.video_area.set_size_request(800, 600)
        self.video_area.connect('realize', self._realized)

        # time label
        self.time_label = Gtk.Label()
        self.update_time_label(0)
        
        self.button_box = Gtk.ButtonBox()
        self.button_box.pack_start(self.seek_backward_button, False, False, 0)
        self.button_box.pack_start(self.seek_forward_button, False, False, 0)
        self.button_box.pack_start(self.playback_button, False, False, 0)
        self.button_box.pack_start(self.record_button, False, False, 0)
        self.button_box.pack_start(self.mute_button, False, False, 0)

        self.button_box.set_spacing(10)
        self.button_box.set_layout(Gtk.ButtonBoxStyle.CENTER)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.vbox)
        self.vbox.pack_start(self.menu_bar, True, True, 0)
        self.vbox.pack_start(self.video_area, True, True, 0)
        self.vbox.pack_start(self.time_label, False, True, 10)
        self.vbox.pack_start(self.slider, False, True, 0)
        self.vbox.pack_start(self.button_box, False, False, 20)

        self.monitor_fig, self.monitor_ax, self.monitor_lines = self.recorder.prepare_monitor_fig()
        self.recorder_plot_data = np.zeros((self.recorder.length, len(self.recorder.channels)))
        canvas = FigureCanvas(self.monitor_fig)  # a Gtk.DrawingArea
        canvas.set_size_request(100, 50)
        self.monitor_label = Gtk.Label()
        self.monitor_label.set_markup('<span foreground="white">Microphone level</span>')
        self.vbox.pack_start(self.monitor_label, False, False, 0)
        self.vbox.pack_start(canvas, False, False, 10)

        self.monitor_animation = FuncAnimation(self.monitor_fig, self.update_mic_monitor,
                                               interval=self.recorder.plot_interval_ms, blit=True)

        self.recorder.stream.start()

        self.toggle_media_controls(False)
        self.record_button.set_sensitive(False)
        self.mute_button.set_sensitive(False)

    def open_file_chooser(self, *args):
        dlg = Gtk.FileChooserDialog("Open video", self, action=Gtk.FileChooserAction.OPEN,
                                    buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        response = dlg.run()

        if response == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            self.load_video(path)

        dlg.destroy()

    def update_mic_monitor(self, *args):
        while True:
            try:
                data = self.recorder.q.get_nowait()
            except queue.Empty:
                break

            shift = len(data)
            self.recorder_plot_data = np.roll(self.recorder_plot_data, -shift, axis=0)
            self.recorder_plot_data[-shift:, :] = data

        for column, line in enumerate(self.monitor_lines):
            line.set_ydata(self.recorder_plot_data[:, column])
            color = 'red' if self.recorder.is_recording else 'white'
            line.set_color(color)

        return self.monitor_lines

    def record(self, *args):
        if not self.recorder.is_recording:
            self.record_button.set_image(self.record_image)
            self.monitor_label.set_markup('<span foreground="#ff3300">Microphone level</span>')
            self.toggle_media_controls(False)
            self.slider.add_mark(self.player.get_time(), Gtk.PositionType.TOP, '<span foreground="#ff3300">|</span>')

            if self.player.is_playing():
                self.pause_video(None)

            path = self.recordings.create_recording_file_path(self.player.get_time())
            self.recorder.start_recording(path)
        else:
            self.recorder.stop_recording()
            self.record_button.set_image(self.mic_image)
            self.monitor_label.set_markup('<span foreground="white">Microphone level</span>')
            self.play_video(None)
            self.toggle_media_controls(True)

    def toggle_media_controls(self, active):
        self.slider.set_sensitive(active)
        self.seek_backward_button.set_sensitive(active)
        self.seek_forward_button.set_sensitive(active)
        self.playback_button.set_sensitive(active)

    def seek_backwards_pressed(self, *args):
        # there is no hold event in Gtk apparently, so we need to do this
        timeout = 50
        self._timeout_id_backwards = GLib.timeout_add(timeout, self.seek_backwards)

    def seek_backwards_released(self, widget):
        # remove timeout
        GLib.source_remove(self._timeout_id_backwards)
        self._timeout_id_backwards = 0

    def seek_backwards(self):
        seek_pos = self.slider.get_value() - self.seek_step

        if seek_pos >= 1:
            self.player.set_time(int(seek_pos))
            self.video_moving(None)

        return True  # this will be called inside a timeout so we return True

    def seek_forwards_pressed(self, *args):
        # there is no hold event in Gtk apparently, so we need to do this
        timeout = 50
        self._timeout_id_forwards = GLib.timeout_add(timeout, self.seek_forwards)

    def seek_forwards_released(self, *args):
        # remove timeout
        GLib.source_remove(self._timeout_id_forwards)
        self._timeout_id_forwards = 0

    def seek_forwards(self):
        seek_pos = self.slider.get_value() + self.seek_step

        if seek_pos < self.video_length_ms:
            self.player.set_time(int(seek_pos))
            self.video_moving(None)

        return True  # this will be called inside a timeout so we return True

    def slider_clicked(self, *args):
        pass  # no need to do anything

    def slider_released(self, *args):
        slider_pos_ms = int(self.slider.get_value())
        self.player.set_time(slider_pos_ms)

    def pause_video(self, *args):
        self.player.pause()
        self.playback_button.set_image(self.play_image)

    def play_video(self, *args):
        self.player.play()
        self.playback_button.set_image(self.pause_image)

    def toggle_player_playback(self, *args):
        if self.player.is_playing():
            self.pause_video(args)
        else:
            self.player.play()
            self.play_video(args)

    def toggle_audio(self, *args):
        if self.player.audio_get_mute():
            self.mute_button.set_image(self.mute_image)
        else:
            self.mute_button.set_image(self.unmute_image)

        self.player.audio_toggle_mute()

    def update_time_label(self, ms):
        ms_str = ms_to_timestamp(ms)
        total_length_str = ms_to_timestamp(self.video_length_ms)
        self.time_label.set_text('{} / {}'.format(ms_str, total_length_str))

    def video_loaded(self, *args):
        # we need to play the video for a while to get the length in milliseconds,
        # so this will be called at the beginning
        self.video_length_ms = self.player.get_length()

        if self.video_length_ms > 0:
            self.slider.set_range(1, self.video_length_ms)
            return False  # video has loaded, will not call this again
        else:
            return True  # video not loaded yet, will try again later

    def video_moving(self, *args):
        current_time_ms = self.player.get_time()
        self.slider.set_value(current_time_ms)
        self.update_time_label(current_time_ms)

    def slider_moved(self, *args):
        # this is called when is moved by the user
        if self.video_length_ms == 0:
            return False  # just to make sure we don't move the slider before we get the video duration

        slider_pos_ms = self.slider.get_value()
        self.player.set_time(int(slider_pos_ms))
        self.update_time_label(slider_pos_ms)

        return False

    def video_ended(self, data):
        GLib.timeout_add(100, self.reload)  # need to call this with some delay otherwise it gets stuck

    def reload(self):
        self.player.set_media(self.player.get_media())
        self.slider.set_value(1)
        self.pause_video(None)
        return False  # return False so we stop this timer

    def setup_vlc_player(self, widget):
        self.vlc_instance = vlc.Instance('--no-xlib')
        self.player = self.vlc_instance.media_player_new()
        win_id = widget.get_window().get_xid()
        self.player.set_xwindow(win_id)

        events = self.player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.video_moving)
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self.video_ended)

    def _realized(self, widget):
        self.setup_vlc_player(widget)
        #self.load_video('/users/dm15712/Videos/whiskey_lab.mp4')

    def load_video(self, video_path):
        self.video_path = video_path
        Media = self.vlc_instance.media_new_path(self.video_path)
        self.player.set_mrl(Media.get_mrl())
        self.player.play()
        self.playback_button.set_image(self.pause_image)
        self.recordings = Recordings('./', self.video_path)

        self.toggle_media_controls(True)
        self.record_button.set_sensitive(True)
        self.mute_button.set_sensitive(True)

        GLib.timeout_add(50, self.video_loaded)  # we need to play to actualy play the video to get the time


if __name__ == '__main__':
    #FILE_PATH = '/users/dm15712/Videos/whiskey_lab.mp4'
    annotator = EpicAnnotator()
    annotator.setup_objects_and_events()
    annotator.show()
    Gtk.main()
    annotator.player.stop()
    annotator.vlc_instance.release()
