import glob
import math
import os


class Recordings:
    def __init__(self, base_folder, video_path, audio_extension='wav'):
        self.base_folder = os.path.join(base_folder, 'epic_annotator_recordings')
        self.video_path = video_path
        self.video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        self.video_annotations_folder = os.path.join(self.base_folder, self.video_name)
        self.audio_extension = audio_extension
        self._recordings = {}
        os.makedirs(self.video_annotations_folder, exist_ok=True)

    def add_recording(self, time):
        os.makedirs(self.video_annotations_folder, exist_ok=True)
        path = os.path.join(self.video_annotations_folder, '{}.{}'.format(time, self.audio_extension))
        self._recordings[time] = path
        return path

    def delete_recording(self, time):
        if time in self._recordings:
            os.remove(self._recordings[time])
            del self._recordings[time]

    def delete_last(self):
        last = sorted(self._recordings.keys())[-1]
        self.delete_recording(last)

    def scan_folder(self):
        return glob.glob(os.path.join(self.video_annotations_folder, '*.{}'.format(self.audio_extension)))

    def annotations_exist(self):
        return os.path.exists(self.video_annotations_folder) and len(self.scan_folder()) > 0

    def load_annotations(self):
        for f in self.scan_folder():
            time_ms = int(os.path.splitext(os.path.basename(f))[0])
            self._recordings[time_ms] = f

    def get_path_for_recording(self, time_ms):
        return self._recordings[time_ms]

    def get_recordings_times(self):
        return sorted(list(self._recordings.keys()))

    def get_last_recording_time(self):
        return sorted(self._recordings.keys())[-1]

    def empty(self):
        return not bool(self._recordings)


def ms_to_timestamp(millis):
    seconds = (millis / 1000) % 60
    minutes = (millis / (1000 * 60)) % 60
    hours = (millis / (1000 * 60 * 60)) % 24

    sec_frac, _ = math.modf(seconds)

    return '{:02d}:{:02d}:{:02d}.{:03d}'.format(int(hours), int(minutes), int(seconds), int(sec_frac*1000))