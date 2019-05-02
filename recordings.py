import os


class Recordings:
    def __init__(self, base_folder, video_path):
        self.base_folder = base_folder
        self.video_path = video_path
        self.video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        self.video_annotations_folder = os.path.join(self.base_folder, '{}_annotations'.format(self.video_name))
        os.makedirs(self.video_annotations_folder, exist_ok=True)

    def create_recording_file_path(self, time, file_format='wav'):
        os.makedirs(self.video_annotations_folder, exist_ok=True)
        return os.path.join(self.video_annotations_folder, '{}.{}'.format(time, file_format))

