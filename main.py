import argparse
import faulthandler
import logging
import os
from logging.handlers import RotatingFileHandler

from controller import Controller
from recorder import Recorder
from settings import Settings
from ui import MainWindow

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG = logging.getLogger('epic_narrator')

parser = argparse.ArgumentParser(
        description="EPIC Narrator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument(
        '--query-audio-devices',
        '--query_audio_devices',
        action='store_true',
        help='Print the audio devices available in your system'
)
parser.add_argument(
        '--set-audio-device',
        '--set_audio_device',
        type=int, default=-1,
        help='Set audio device to be used for recording, given the device id. '
             'Use `--query_audio_devices` to get the devices available in your system '
             'with their corresponding ids')
parser.add_argument('--verbosity',
                    default='info',
                    choices=['debug', 'info', 'warning', 'error', 'critical'],
                    help="Logging verbosity, one of 'debug', 'info', 'warning', "
                         "'error', 'critical'.")
parser.add_argument('--log-file', type=str, help='Path to log file.')


def main(args):
    setup_logging(args)
    commit_hash = get_git_commit_hash()
    LOG.info("Starting the EPIC-narrator" +
             (" ({})".format(commit_hash) if commit_hash is not None else ""))

    if args.query_audio_devices:
        print(Recorder.get_devices())
        exit()

    if args.set_audio_device >= 0:
        LOG.info('Changing default mic device to {}'.format(args.set_audio_device))
        Recorder.set_default_device(args.set_audio_device)

    controller = Controller()
    main_window = MainWindow(controller)
    main_window.show()
    Gtk.main()




def get_git_commit_hash():
    import subprocess

    try:
        output = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=SCRIPT_DIR,
                                check=True,
                                stdout=subprocess.PIPE)
        return output.stdout.decode('utf-8').strip()
    except Exception:
        return None


def setup_logging(args):
    log_level = getattr(logging, args.verbosity.upper())

    '''
    if args.log_file is not None:
        logging.basicConfig(filename=args.log_file)
    else:
        logging.basicConfig()
    '''
    log_path = os.path.join(Settings.get_epic_narrator_directory(),
                            'narrator.log') if args.log_file is None else args.log_file

    # add a rotating handler
    handler = RotatingFileHandler(log_path, maxBytes=5000000, backupCount=3)
    LOG.addHandler(handler)
    LOG.setLevel(log_level)


if __name__ == '__main__':
    faulthandler.enable()
    main(parser.parse_args())