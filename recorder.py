import logging

import sounddevice as sd
import queue
import soundfile as sf

LOG = logging.getLogger('epic_narrator.recorder')


class Recorder:
    def __init__(self, channels=[1], device_id=sd.default.device[0], window=200, downsample=10):
        LOG.info("Creating recorder for device id {}".format(device_id))
        self.mapping = [c - 1 for c in channels]  # Channel numbers start with 1
        self.q = queue.Queue()
        self.channels = channels
        self.device_info = sd.query_devices(device_id, 'input')
        self.device_id = device_id
        self.sample_rate = self.device_info['default_samplerate']
        self.downsample = downsample
        self.window = window
        self.length = int(self.window * self.sample_rate / (1000 * self.downsample))
        self.is_recording = False
        self.current_file = None

        self.stream = sd.InputStream(device=self.device_id, channels=max(self.channels),
                                     samplerate=self.sample_rate, callback=self.audio_callback)

    def change_device(self, device_id):
        LOG.info("Changing recorder device to {}".format(device_id))
        self.close_stream()
        self.device_id = device_id
        self.stream = sd.InputStream(device=self.device_id, channels=max(self.channels),
                                     samplerate=self.sample_rate, callback=self.audio_callback)

    def close_stream(self):
        if self.is_recording:
            self.stop_recording()  # this will wait for any open files to be closed

        self.stream.close(ignore_errors=True)

    def start_recording(self, filename):
        LOG.info("Starting new recording, saving to {}".format(filename))
        self.is_recording = True
        self.current_file = sf.SoundFile(filename, mode='w', samplerate=int(self.sample_rate),
                                         channels=len(self.channels))
        
    def stop_recording(self):
        LOG.info("Stopping recording, saved to {}".format(self.current_file.name))
        self.is_recording = False
        LOG.debug("Closing {}".format(self.current_file.name))
        self.current_file.hide()

        # while self.current_file is not None and not self.current_file.closed:
        #    time.sleep(0.01)  # waiting for file to be closed

    def audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""

        # Fancy indexing with mapping creates a (necessary!) copy:
        self.q.put(indata[::self.downsample, self.mapping])

        if self.current_file is None or self.current_file.closed:
            return

        if self.is_recording:
            self.current_file.buffer_write(indata, dtype='float32')

    def get_window_size(self):
        return self.length, len(self.channels)

    @staticmethod
    def get_devices():
        all_devices = sd.query_devices()
        input_devices = []

        for dev_idx, dev in enumerate(all_devices):
            if 0 < dev['max_input_channels'] < 32:  # 32 to avoid getting virtual alsa device
                input_devices.append({'dev_idx': dev_idx, 'dev_name': dev['name']})

        return input_devices

    @staticmethod
    def set_default_device(dev_id):
        sd.default.device = dev_id

    @staticmethod
    def get_default_device():
        return sd.default.device[0]


if __name__ == '__main__':
    print(sd.query_devices())
    #recorder = Recorder(set_plot=True)
    #recorder.start_monitor()
    print(Recorder.get_devices())
