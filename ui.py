import os
import queue
import sys
import matplotlib as mpl
import numpy as np

mpl.use('PS')
import matplotlib.pyplot as plt
import gi
from recordings import ms_to_timestamp

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango, GObject
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_gtk3agg import (FigureCanvasGTK3Agg as FigureCanvas)

if sys.platform.startswith('darwin'):
    plt.switch_backend('MacOSX')
else:
    plt.switch_backend('GTK3Agg')


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, controller, single_window=True):
        Gtk.ApplicationWindow.__init__(self, title='Epic Narrator')
        gtk_settings = Gtk.Settings.get_default()
        gtk_settings.set_property("gtk-application-prefer-dark-theme", False)

        try:
            # set an icon if running from the command line
            # this won't work inside flatpak, but in flatpak we have a .desktop file, so we just keep going
            self.set_icon_from_file(os.path.join("data", "epic.png"))
        except Exception:
            pass

        self.controller = controller
        self.ready = False

        # generic properties
        self.red_tick_colour = "#ff3300"
        self.single_window = single_window

        # setting menus
        self.menu_bar = Menu(controller, self)
        self.video_area = VideoArea(self.controller, self.single_window)

        # adding speed boxes, time label and play with rec checkbox
        self.speed_time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.speed_time_box.pack_start(Gtk.Label(label='Playback speed'), False, False, 10)
        self.add_speed_check_boxes()
        # time label
        self.time_label = Gtk.Label()
        self.update_time_label(0)
        self.play_recs_with_video_button = Gtk.CheckButton(label='Play recordings with video')
        # self.play_recs_with_video_button.connect('toggled', self.play_recs_with_video_toggled) #TODO connect this
        self.speed_time_box.pack_end(self.time_label, False, False, 0)
        self.speed_time_box.pack_end(self.play_recs_with_video_button, False, False, 5)

        # slider
        self.slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=None)
        self.set_slider()

        # boxes and packing
        self.video_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.video_box.pack_start(self.menu_bar, False, False, 0)

        # playback controller
        self.playback_controller = PlaybackController(self.controller)

        # microphone monitor
        self.monitor_label = Gtk.Label()
        self.set_monitor_label(False)
        self.mic_monitor = MicMonitor(self.controller)

        # path labels
        self.video_path_label = Gtk.Label(label=' ')
        self.recordings_path_label = Gtk.Label(label=' ')
        self.paths_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_path_labels()

        if self.single_window:
            self.video_box.pack_start(self.video_area.area, True, True, 0)
        else:
            self.video_area.area.show()
            # TODO: update this to have all windows nicely put together
            #self.video_area.move(0, 0)
            #self.move(0, self.video_height + 100)

            # enable only horizontal resize
            gh = Gdk.Geometry()
            gh.max_height = 300
            gh.min_height = 300
            gh.max_width = 2000
            gh.min_width = 900
            self.set_geometry_hints(None, gh, Gdk.WindowHints.MAX_SIZE)

        self.video_box.pack_start(self.speed_time_box, False, False, 10)
        self.video_box.pack_start(self.slider, False, False, 0)
        self.video_box.pack_start(self.playback_controller, False, False, 20)
        self.video_box.pack_start(self.monitor_label, False, False, 0)
        self.video_box.pack_start(self.mic_monitor, False, False, 10)
        self.video_box.pack_start(self.paths_box, False, False, 10)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_box.pack_start(self.video_box, False, True, 0)

        self.add(self.main_box)

        # TODO insteat of set focus of buttons just do nothing if video is not loaded

        self.connect('destroy', self.closing)
        self.connect('show', self.showing)

    def show(self):
        self.show_all()

    def showing(self, *args):
        self.ready = True

    def closing(self, *args):
        if not self.single_window:
            self.video_area.area.destroy()

        self.controller.shutting_down()

    def add_speed_check_boxes(self):
        saved_playback_speed = self.controller.get_setting('playback_speed', 1)
        speed_item = None
        speeds = [0.50, 0.75, 1, 1.50, 2]

        for speed in speeds:
            speed_item = Gtk.RadioButton(label='{:0.2f}'.format(speed), group=speed_item)
            #speed_item.connect('clicked', self.speed_selected, speed)  #TODO connect this
            speed_item.set_can_focus(False)

            if speed == saved_playback_speed:
                speed_item.set_active(True)

            self.speed_time_box.pack_start(speed_item, False, False, 0)

    def update_time_label(self, ms):
        ms_str = ms_to_timestamp(ms)
        total_length_str = ms_to_timestamp(self.controller.get_video_length())
        time_txt = ' {} / {} '.format(ms_str, total_length_str)
        self.time_label.set_markup('<span bgcolor="black" fgcolor="white"><tt>{}</tt></span>'.format(time_txt))

    def set_slider(self):
        # TODO connect this
        #self.slider.connect('change-value', self.slider_moved)
        #self.slider.connect('button-press-event', self.slider_clicked)
        #self.slider.connect('button-release-event', self.slider_released)
        self.slider.set_hexpand(True)
        self.slider.set_valign(Gtk.Align.CENTER)
        self.slider.set_draw_value(False)

    def add_time_tick(self, time_ms, colour=None):
        self.slider.add_mark(time_ms, Gtk.PositionType.TOP, None)

    def refresh_recording_ticks(self):
        self.slider.clear_marks()

        # TODO fix this
        #for time_ms in self.recordings.get_recordings_times():
        #    self.add_time_tick(time_ms, colour=self.red_tick_colour)

    def set_monitor_label(self, is_recording):
        colour = '#ff3300' if is_recording else 'black'
        self.monitor_label.set_markup('<span foreground="{}">Microphone level</span>'.format(colour))

    def set_path_labels(self):
        for path_labels in [self.video_path_label, self.recordings_path_label]:
            path_labels.set_property('lines', 1)
            path_labels.set_ellipsize(Pango.EllipsizeMode.START)
            path_labels.set_property('max-width-chars', 50)

        video_path_placeholder = Gtk.Label()
        video_path_placeholder.set_markup('<span><b>Annotating video:</b></span>')
        recordings_path_placeholder = Gtk.Label()
        recordings_path_placeholder.set_markup('<span><b>Saving recordings to:</b></span>')
        self.paths_box.pack_start(video_path_placeholder, False, False, 10)
        self.paths_box.pack_start(self.video_path_label, False, False, 0)
        self.paths_box.pack_end(self.recordings_path_label, False, False, 0)
        self.paths_box.pack_end(recordings_path_placeholder, False, False, 10)


class Menu(Gtk.MenuBar):
    def __init__(self, controller, main_window):
        Gtk.MenuBar.__init__(self)
        self.controller = controller
        self.main_window = main_window
        self.file_menu = Gtk.Menu()
        self.load_video_menu_item = Gtk.MenuItem(label='Load video')
        self.load_video_menu_item.connect('button-press-event', self.choose_video)
        self.file_menu.append(self.load_video_menu_item)
        self.file_menu_item = Gtk.MenuItem(label='File')
        self.file_menu_item.set_submenu(self.file_menu)

        self.mic_menu = Gtk.Menu()
        self.mic_menu_item = Gtk.MenuItem(label='Select microphone')
        self.mic_menu_item.set_submenu(self.mic_menu)
        self.set_mic_items(controller.get_mic_devices(), controller.get_current_mic_device())

        self.settings_menu = Gtk.Menu()
        self.hold_to_record_menu_item = Gtk.CheckMenuItem(label='Hold to record')
        self.hold_to_record_menu_item.set_active(controller.get_setting('hold_to_record', False))
        # self.hold_to_record_menu_item.connect('toggled', self.hold_to_record_toggled) #TODO connect this

        self.play_after_delete_menu_item = Gtk.CheckMenuItem(label='Play video after deleting recording')
        self.play_after_delete_menu_item.set_active(controller.get_setting('play_after_delete', False))
        # self.play_after_delete_menu_item.connect('toggled', self.play_after_delete_toggled) #TODO connect this

        self.settings_menu.append(self.hold_to_record_menu_item)
        self.settings_menu.append(self.play_after_delete_menu_item)
        self.settings_menu_item = Gtk.MenuItem(label='Settings')
        self.settings_menu_item.set_submenu(self.settings_menu)

        self.append(self.file_menu_item)
        self.append(self.mic_menu_item)
        self.append(self.settings_menu_item)

    def set_mic_items(self, mic_devices, current_mic):
        mic_item = None

        for dev in mic_devices:
            dev_idx = dev['dev_idx']
            dev_name = dev['dev_name']
            mic_item = Gtk.RadioMenuItem(label=dev_name, group=mic_item)
            mic_item.connect('activate', self.microphone_selected, dev_idx)

            if dev_idx == current_mic:
                mic_item.set_active(True)

            self.mic_menu.append(mic_item)

    def microphone_selected(self, mic_item, mic_id):
        if self.main_window.ready and mic_id != self.controller.get_current_mic_device():
            ok = self.controller.change_mic(mic_id)

            if not ok:
                dialog = Gtk.MessageDialog(parent=self.main_window, flags=0, message_type=Gtk.MessageType.ERROR,
                                           title='Cannot use this device')
                dialog.add_button("OK", Gtk.ResponseType.OK)
                dialog.format_secondary_text('Please select another device and check you can see a signal in the '
                                             'microphone level when you speak')
                dialog.run()
                dialog.destroy()

    def choose_video(self, *args):
        if self.controller.is_video_loaded:
            confirm_dialog = Gtk.MessageDialog(parent=self.main_window, flags=0, message_type=Gtk.MessageType.QUESTION,
                                               title='Confirm loading another video')
            confirm_dialog.format_secondary_text('Are you sure you want to load another video?')
            confirm_dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            confirm_dialog.add_button("OK", Gtk.ResponseType.OK)
            response = confirm_dialog.run()

            if response != Gtk.ResponseType.OK:
                confirm_dialog.destroy()
                return

            confirm_dialog.destroy()

        file_dialog = Gtk.FileChooserDialog(title="Open video", parent=self.main_window, action=Gtk.FileChooserAction.OPEN)
        file_dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        file_dialog.add_button("OK", Gtk.ResponseType.OK)

        video_file_filter = Gtk.FileFilter()
        video_file_filter.set_name("Video files")
        video_file_filter.add_mime_type("video/*")
        file_dialog.add_filter(video_file_filter)

        all_file_filter = Gtk.FileFilter()
        all_file_filter.set_name('All files')
        all_file_filter.add_pattern('*')
        file_dialog.add_filter(all_file_filter)

        saved_video_folder = self.controller.get_setting('video_folder', None)

        if saved_video_folder is not None and os.path.exists(saved_video_folder):
            file_dialog.set_current_folder(saved_video_folder)

        response = file_dialog.run()

        if response == Gtk.ResponseType.OK:
            path = file_dialog.get_filename()

            if os.path.isdir(path):
                message_dialog = Gtk.MessageDialog(parent=self.main_window, flags=0, message_type=Gtk.MessageType.ERROR,
                                                   title='Invalid path')
                message_dialog.add_button("OK", Gtk.ResponseType.OK)
                message_dialog.format_secondary_text('You cannot select a folder!')
                message_dialog.run()
                message_dialog.destroy()
                file_dialog.destroy()
                self.choose_video()
            else:
                file_dialog.destroy()
                self.controller.video_selected(path, self)
        else:
            file_dialog.destroy()

    def choose_output_folder(self, output):
        dialog = Gtk.FileChooserDialog(title="Select output folder", parent=self.main_window,
                                       action=Gtk.FileChooserAction.SELECT_FOLDER)

        dialog.add_button("OK", Gtk.ResponseType.OK)
        dialog.set_current_folder(output)
        dialog.run()
        path = dialog.get_filename()
        dialog.destroy()

        return path


class VideoArea:
    def __init__(self, controller, single_window, width=900, height=400):
        self.video_width = width
        self.video_height = height
        self.single_window = single_window
        self.controller = controller

        if self.single_window:
            self.area = Gtk.DrawingArea()
        else:
            self.area = Gtk.Window(title='Epic Narrator')
            self.area.set_deletable(False)

        self.area.set_size_request(self.video_width, self.video_height)
        self.area.connect('realize', self.ready)

        if self.single_window:
            # self.video_area.connect('configure_event', self.video_area_resized)
            self.area.connect('draw', self.draw_video_area)

    def draw_video_area(self, widget, cairo_ctx):
        # this fixes the broken video area that might happen when resizing the window, depending on the system
        cairo_ctx.set_source_rgb(0, 0, 0)
        cairo_ctx.paint()

    def ready(self, widget):
        self.controller.ui_video_area_ready(widget)


class PlaybackController(Gtk.ButtonBox):
    def __init__(self, controller):
        Gtk.ButtonBox.__init__(self)
        self.controller = controller
        self.seek_backward_image = Gtk.Image.new_from_icon_name('media-seek-backward', Gtk.IconSize.BUTTON)
        self.seek_forward_image = Gtk.Image.new_from_icon_name('media-seek-forward', Gtk.IconSize.BUTTON)
        self.play_image = Gtk.Image.new_from_icon_name('media-playback-start', Gtk.IconSize.BUTTON)
        self.pause_image = Gtk.Image.new_from_icon_name('media-playback-pause', Gtk.IconSize.BUTTON)
        self.mute_image = Gtk.Image.new_from_icon_name('audio-volume-muted', Gtk.IconSize.BUTTON)
        self.unmute_image = Gtk.Image.new_from_icon_name('audio-volume-high', Gtk.IconSize.BUTTON)
        self.mic_image = Gtk.Image.new_from_icon_name('audio-input-microphone', Gtk.IconSize.BUTTON)
        self.record_image = Gtk.Image.new_from_icon_name('media-record', Gtk.IconSize.BUTTON)

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

        # TODO connect these
        '''
        self.seek_backward_button.connect('pressed', self.seek_backwards_pressed)
        self.seek_backward_button.connect('released', self.seek_backwards_released)
        self.seek_forward_button.connect('pressed', self.seek_forwards_pressed)
        self.seek_forward_button.connect('released', self.seek_forwards_released)
        self.playback_button.connect('clicked', self.toggle_player_playback)
        self.record_button.connect('pressed', self.record_button_clicked)
        self.record_button.connect('released', self.record_button_released)
        self.mute_button.connect('clicked', self.toggle_audio)
        '''

        self.pack_start(self.seek_backward_button, False, False, 0)
        self.pack_start(self.seek_forward_button, False, False, 0)
        self.pack_start(self.playback_button, False, False, 0)
        self.pack_start(self.record_button, False, False, 0)
        self.pack_start(self.mute_button, False, False, 0)
        self.set_spacing(10)
        self.set_layout(Gtk.ButtonBoxStyle.CENTER)


class MicMonitor(FigureCanvas):
    def __init__(self, controller, plot_interval_ms=30):
        # microphone monitor
        self.controller = controller
        self.fig, self.ax, self.lines, self.data = self.prepare_monitor_fig()
        FigureCanvas.__init__(self, self.fig)  # a Gtk.DrawingArea
        self.set_size_request(100, 50)
        self.monitor_animation = FuncAnimation(self.fig, self.update_mic_monitor, interval=plot_interval_ms, blit=True)

    def prepare_monitor_fig(self):
        plt.style.use('dark_background')
        mpl.rcParams['toolbar'] = 'None'
        fig, ax = plt.subplots()

        window_length, n_channels = self.controller.get_recorder_window_size()
        data = np.zeros((window_length, n_channels))
        lines = ax.plot(data, color='w')
        ax.axis((0, len(data), -0.25, 0.25))
        ax.set_yticks([0])
        ax.yaxis.grid(True)
        fig.tight_layout(pad=-5)
        ax.axis('off')
        fig.canvas.set_window_title('Epic Narrator Monitor')

        return fig, ax, lines, data

    def update_mic_monitor(self, *args):
        while True:
            try:
                data = self.controller.get_recorder_data()
            except queue.Empty:
                break

            shift = len(data)
            self.data = np.roll(self.data, -shift, axis=0)
            self.data[-shift:, :] = data

        for column, line in enumerate(self.lines):
            line.set_ydata(self.data[:, column])
            color = 'red' if self.controller.is_recording() else 'white'
            line.set_color(color)

        return self.lines
