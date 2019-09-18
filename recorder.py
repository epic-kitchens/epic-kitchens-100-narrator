import sys
import time

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd
import queue
import matplotlib as mpl
import soundfile as sf


class Recorder:
    def __init__(self, channels=[1], device_id=0, window=200, downsample=10, plot_interval_ms=30, set_plot=False):
        self.mapping = [c - 1 for c in channels]  # Channel numbers start with 1
        self.q = queue.Queue()
        self.channels = channels
        self.device_info = sd.query_devices(device_id, 'input')
        self.device_id = device_id
        self.sample_rate = self.device_info['default_samplerate']
        self.downsample = downsample
        self.plot_interval_ms = plot_interval_ms
        self.window = window
        self.length = int(self.window * self.sample_rate / (1000 * self.downsample))
        self.window_data = np.zeros((self.length, len(self.channels)))
        self.is_recording = False
        self.current_file = None

        self.stream = sd.InputStream(device=self.device_id, channels=max(self.channels),
                                     samplerate=self.sample_rate, callback=self.audio_callback)

        if set_plot:
            self.monitor_fig, self.ax, self.lines = self.prepare_monitor_fig()
            self.monitor_animation = FuncAnimation(self.monitor_fig, self.update_monitor_animation,
                                                   interval=self.plot_interval_ms, blit=True)
        else:
            self.monitor_fig = None
            self.monitor_animation = None

    def change_device(self, device_id):
        self.close_stream()
        self.device_id = device_id
        self.stream = sd.InputStream(device=self.device_id, channels=max(self.channels),
                                     samplerate=self.sample_rate, callback=self.audio_callback)

    def close_stream(self):
        if self.is_recording:
            self.stop_recording()  # this will wait for any open files to be closed

        self.stream.close(ignore_errors=True)

    def start_recording(self, filename):
        self.is_recording = True
        self.current_file = sf.SoundFile(filename, mode='w', samplerate=int(self.sample_rate),
                                         channels=len(self.channels))
        
    def stop_recording(self):
        self.is_recording = False
        self.current_file.close()

        # while self.current_file is not None and not self.current_file.closed:
        #    time.sleep(0.01)  # waiting for file to be closed

    def prepare_monitor_fig(self):
        plt.style.use('dark_background')
        mpl.rcParams['toolbar'] = 'None'
        fig, ax = plt.subplots()
        lines = ax.plot(self.window_data, color='w')
        ax.axis((0, len(self.window_data), -0.25, 0.25))
        ax.set_yticks([0])
        ax.yaxis.grid(True)
        fig.tight_layout(pad=-5)
        ax.axis('off')
        fig.canvas.set_window_title('Epic Narrator Monitor')

        return fig, ax, lines

    def update_monitor_animation(self, frame):
        """This is called by matplotlib for each plot update.

        Typically, audio callbacks happen more frequently than plot updates,
        therefore the queue tends to contain multiple blocks of audio data.
        """

        while True:
            try:
                data = self.q.get_nowait()
            except queue.Empty:
                break

            shift = len(data)
            self.window_data = np.roll(self.window_data, -shift, axis=0)
            self.window_data[-shift:, :] = data

        for column, line in enumerate(self.lines):
            line.set_ydata(self.window_data[:, column], color='blue')

        return self.lines

    def audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""

        # Fancy indexing with mapping creates a (necessary!) copy:
        self.q.put(indata[::self.downsample, self.mapping])

        if self.current_file is None or self.current_file.closed:
            return

        if self.is_recording:
            self.current_file.buffer_write(indata, dtype='float32')

    def start_monitor(self):
        with self.stream:
            plt.show()

    @staticmethod
    def get_devices():
        return sd.query_devices()


if __name__ == '__main__':
    print(sd.query_devices())
    #recorder = Recorder(set_plot=True)
    #recorder.start_monitor()
