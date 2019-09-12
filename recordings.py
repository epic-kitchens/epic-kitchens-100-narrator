import glob
import math
import os
import bisect


class Recordings:
    def __init__(self, base_folder, video_path, audio_extension='wav'):
        self.base_folder = os.path.join(base_folder, 'epic_narrator_recordings')
        self.video_path = video_path
        self.video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        self.video_annotations_folder = os.path.join(self.base_folder, self.video_name)
        self.audio_extension = audio_extension
        self._recordings = {}
        self._recording_times = []
        os.makedirs(self.video_annotations_folder, exist_ok=True)

    def add_recording(self, time):
        os.makedirs(self.video_annotations_folder, exist_ok=True)
        path = os.path.join(self.video_annotations_folder, '{}.{}'.format(time, self.audio_extension))
        self._recordings[time] = path
        bisect.insort(self._recording_times, time)
        return path

    def delete_recording(self, time):
        if time in self._recordings:
            os.remove(self._recordings[time])
            del self._recordings[time]
            self._recording_times.remove(time)  # no need to sort when we delete

    def delete_last(self):
        self.delete_recording(self._recording_times[-1])

    def scan_folder(self):
        return glob.glob(os.path.join(self.video_annotations_folder, '*.{}'.format(self.audio_extension)))

    def annotations_exist(self):
        return os.path.exists(self.video_annotations_folder) and len(self.scan_folder()) > 0

    def load_annotations(self):
        for f in self.scan_folder():
            time_ms = int(os.path.splitext(os.path.basename(f))[0])
            self._recordings[time_ms] = f
            bisect.insort(self._recording_times, time_ms)

    def get_path_for_recording(self, time_ms):
        if time_ms in self._recordings:
            return self._recordings[time_ms]
        else:
            return None

    def get_recordings_times(self):
        return self._recording_times

    def get_last_recording_time(self):
        return self._recording_times[-1]

    def get_closet_recording(self, time_ms, neighbourhood=1000):
        """
            Assumes myList is sorted. Returns closest value to myNumber.

            If two numbers are equally close, return the smallest number.
            """
        pos = bisect.bisect_left(self._recording_times, time_ms)

        if pos == 0:
            closest = self._recording_times[0]
        elif pos == len(self._recording_times):
            closest = self._recording_times[-1]
        else:
            before = self._recording_times[pos - 1]
            after = self._recording_times[pos]

            if after - time_ms < time_ms - before:
                closest = after
            else:
                closest = before

        dist = abs(closest-time_ms)

        if neighbourhood is None or (dist <= neighbourhood):  # pick only recordings ahead
            return closest
        else:
            return None

    def empty(self):
        return not bool(self._recordings)

    def recording_exists(self, time_ms):
        return time_ms in self._recordings


def ms_to_timestamp(millis):
    seconds = (millis / 1000) % 60
    minutes = (millis / (1000 * 60)) % 60
    hours = (millis / (1000 * 60 * 60)) % 24

    sec_frac, _ = math.modf(seconds)

    return '{:02d}:{:02d}:{:02d}.{:03d}'.format(int(hours), int(minutes), int(seconds), int(sec_frac*1000))