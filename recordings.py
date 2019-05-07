import glob
import os


class Recordings:
    def __init__(self, base_folder, video_path, audio_extension='wav'):
        self.base_folder = base_folder
        self.video_path = video_path
        self.video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        self.video_annotations_folder = os.path.join(self.base_folder, '{}_annotations'.format(self.video_name))
        self.audio_extension = audio_extension
        self.recordings = {}
        os.makedirs(self.video_annotations_folder, exist_ok=True)

    def add_recording(self, time):
        os.makedirs(self.video_annotations_folder, exist_ok=True)
        path = os.path.join(self.video_annotations_folder, '{}.{}'.format(time, self.audio_extension))
        self.recordings[time] = path
        return path

    def delete_recording(self, time):
        if time in self.recordings:
            os.remove(self.recordings[time])
            del self.recordings[time]

    def scan_folder(self):
        return glob.glob(os.path.join(self.video_annotations_folder, '*.{}'.format(self.audio_extension)))

    def annotations_exist(self):
        return os.path.exists(self.video_annotations_folder) and len(self.scan_folder()) > 0

    def load_annotations(self):
        for f in self.scan_folder():
            time_ms = int(os.path.splitext(os.path.basename(f))[0])
            self.recordings[time_ms] = f
