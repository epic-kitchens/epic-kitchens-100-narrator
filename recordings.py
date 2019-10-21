import glob
import logging
import math
import os
import bisect

LOG = logging.getLogger('epic_narrator.recordings')


class Recordings:
    def __init__(self, output_parent, video_path, audio_extension='wav'):
        self.base_folder = Recordings.get_recordings_path(output_parent)
        self.video_path = video_path
        self.video_narrations_folder = Recordings.get_recordings_path_for_video(self.base_folder, self.video_path,
                                                                                from_parent_folder=False)
        self.audio_extension = audio_extension
        self._recordings = {}
        self._recording_times = []
        self._highlighted_rec_index = None
        os.makedirs(self.video_narrations_folder, exist_ok=True)

    def add_recording(self, time, overwrite=False):
        LOG.info("Adding recording at {!r} (overwrite={})".format(time, overwrite))
        os.makedirs(self.video_narrations_folder, exist_ok=True)
        path = os.path.join(self.video_narrations_folder, '{}.{}'.format(time, self.audio_extension))

        if not overwrite:
            self._recordings[time] = path
            # the insort below is equivalent to the two calls afterwards. We need the rec index, so we separate
            # the two
            # bisect.insort(self._recording_times, time)
            rec_index = bisect.bisect_left(self._recording_times, time)
            self._recording_times.insert(rec_index, time)
        else:
            rec_index = None

        return path, rec_index

    def delete_recording(self, time):
        if time in self._recordings:
            LOG.info("Deleting recording at {!r}".format(time))
            filepath = self._recordings[time]
            os.remove(filepath)
            LOG.info("Deleted recording {}".format(filepath))
            del self._recordings[time]
            self._recording_times.remove(time)  # no need to sort when we delete

    def delete_last(self):
        self.delete_recording(self._recording_times[-1])

    def scan_folder(self):
        LOG.info("Scanning {} for audio files".format(self.video_narrations_folder))
        audio_files = glob.glob(os.path.join(self.video_narrations_folder,
                                            '*.{}'.format(self.audio_extension)))
        LOG.info("Found {} existing recordings".format(len(audio_files)))
        return audio_files

    def narrations_exist(self):
        return os.path.exists(self.video_narrations_folder) and len(self.scan_folder()) > 0

    def load_narrations(self):
        for f in self.scan_folder():
            LOG.debug("Loading recording {}".format(f))
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

    def get_closest_recording(self, time_ms, neighbourhood=1000):
        if not self._recording_times:
            return None

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

    def _set_currently_highlighted_recording_from_time(self, time):
        closest = self.get_closest_recording(time, neighbourhood=None)

        if closest is not None:
            self._highlighted_rec_index = self._recording_times.index(closest)

    def _set_currently_highlighted_recording_from_index(self, rec_index):
        if 0 <= rec_index < len(self._recording_times):
            self._highlighted_rec_index = rec_index

    def get_next_from_highlighted(self, time, neighbourhood=1000):
        if self._highlighted_rec_index is None:
            self._set_currently_highlighted_recording_from_time(time)

        if self._highlighted_rec_index is not None and self._highlighted_rec_index + 1 < len(self._recording_times):
            next_rec = self._recording_times[self._highlighted_rec_index+1]
            dist = next_rec - time

            if dist < 0:
                # we are dragging behind, so let's find the closest one from the current highlighted
                for t in self._recording_times[self._highlighted_rec_index+1:]:
                    if t - time >= 0:
                        return t
            elif dist < neighbourhood:
                return next_rec
            else:
                return None
        else:
            return None

    def get_next_from_index(self, index):
        idx = max(0, min(index+1, len(self._recording_times)-1))
        return self._recording_times[idx]

    def get_previous_from_index(self, index):
        idx = max(0, min(index-1, len(self._recording_times) - 1))
        return self._recording_times[idx]

    def is_last_recording(self, rec_time):
        return self._recording_times[-1] == rec_time

    def move_highlighted_next(self):
        if self._highlighted_rec_index is not None and self._highlighted_rec_index + 1 < len(self._recording_times):
            self._highlighted_rec_index += 1

    def reset_highlighted(self):
        self._highlighted_rec_index = None

    @staticmethod
    def get_recordings_path(output_parent):
        return os.path.join(output_parent, 'epic_narrator_recordings')

    @staticmethod
    def get_recordings_path_for_video(output_path, video_path, from_parent_folder=True):
        video_name = os.path.splitext(os.path.basename(video_path))[0]

        if from_parent_folder is True:
            base_folder = Recordings.get_recordings_path(output_path)
        else:
            base_folder = output_path

        return os.path.join(base_folder, video_name)


def ms_to_timestamp(millis):
    seconds = (millis / 1000) % 60
    minutes = (millis / (1000 * 60)) % 60
    hours = (millis / (1000 * 60 * 60)) % 24

    sec_frac, _ = math.modf(seconds)

    return '{:02d}:{:02d}:{:02d}.{:03d}'.format(int(hours), int(minutes), int(seconds), int(sec_frac*1000))