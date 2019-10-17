# EPIC Narrator
[![CircleCI](https://circleci.com/gh/epic-kitchens/epic-narrator.svg?style=svg)](https://circleci.com/gh/epic-kitchens/epic-narrator)

**EPIC-narrator** is a tool written in Python to annotate actions in videos via narration. 

# Installation

[VLC player](https://www.videolan.org/vlc/) must be installed in your system, regardless of your OS
(unless you use flatpak).

## Linux

### Flatpak

Download the flatpak bundled with all the dependencies 
[here](https://github.com/epic-kitchens/epic-narrator/releases/tag/flatpak)

To use the flatpak bundle you will need to install first [Flatpak](https://flatpak.org/setup/) on your Linux distro: 

to install the narrator flatpak:

```flatpak install epic_narrator.flatpak```

to run it:

```flatpak run uk.ac.bris.epic.narrator```

### Conda

If you don't want to use flatpak, use conda with the provided environment to 
install the necessary dependencies:

```bash
conda env create -f environment.yml
```

Alternatively, you can try to install the necessary modules yourself:

- [GTK 3](https://www.gtk.org/)
- [python-vlc](https://pypi.org/project/python-vlc/)
- [pysoundfile](https://pypi.org/project/PySoundFile/)
  - This requires the `libsndfile` library to be installed in your system. 
    In Linux this should be available in all distributions. For Windows and MacOS 
    `pip install pysoundfile` should install the library automatically for you. 
- [pysounddevice](https://pypi.org/project/sounddevice/)
   - This requires [PortAudio](http://www.portaudio.com/) to be installed in your system. 
     In Linux this should be available in all distributions. For Windows and MacOS 
    `pip install sounddevice` should install the library automatically for you.
- [PyGObject](https://pypi.org/project/PyGObject/)
- [matplotlib](https://pypi.org/project/matplotlib/)
- [PyYAML](https://pypi.org/project/PyYAML/)

Note that the narrator works with Python 3 only. 

##### Choppy playback

If you experience choppy playback on Linux your VLC is probably not decoding the videos correctly.

Try to install `libva1, libva-{mesa,vdpau}-driver` to fix this issue. More on this [here](https://wiki.archlinux.org/index.php/Hardware_video_acceleration)

##### Invisible icons/checkboxes

If you don't see some icons or checkboxes, 
try to install the package [`adwaita-icon-theme-full`](https://packages.ubuntu.com/xenial/gnome/adwaita-icon-theme-full)
via `apt` or your distribution's package manager.

## Mac OS

Use [brew](https://brew.sh/) and pip to install the dependencies. 
Note that you should use pip3 (i.e. pip for python 3.x)

**Important:** if you use conda, make sure you run `conda deactivate` before running the commands below 
(even the `base` environment must be deactivated)

```bash
brew install pygobject3 gtk+3 adwaita-icon-theme
python3 -m pip install matplotlib python-vlc sounddevice soundfile PyYAML
```

Bear in mind that the `brew` installation might take a while.

If you get the following error

```ERROR: Could not find an activated virtualenv (required)```

Try to export the following variable 

```export PIP_REQUIRE_VIRTUALENV=false```

*before* installing the python dependencies with `pithon3 -m pip` 

# Usage

Start the program with `python epic_narrator.py`. Once the program has started:

1. Make sure your microphone input is correctly being captured. You can do this by checking the signal
   displayed in the monitor level. If you don't see any signal as you speak try to select a different audio
   interface ([see below how](#Selecting-audio-interface)).
2. Load the video: `File -> Load video`
3. Choose where you want to save your recordings. The program will create the folders 
   `epic_narrator_recordings/video_name/` under your selected output folder.
4. Play the video and narrate actions 
 
### Playing and recording 

Use the playback buttons to pause/play the video, as well as seeking backwards and forwards and mute/unmute 
the video. 

You can use the slider to move across the  video. 

You can also change the speed of the playback.

To annotate an action press the microphone button. 
This will pause the video and will start recording your voice immediately. Once you have narrated the action, press 
the button again to stop the recording and continue annotating. The end of the recording will be delayed by 0.5 seconds
to avoid clipping. 

Alternatively, if you switch the option `Settings -> Hold to record` you can record while holding down either the record
button or the enter key. In this case the recording will stop immediately as soon as you release the key or the button.

### Jumping to, playing, deleting and overwriting recordings

You will see all your recorded actions in the right-hand side panel.
 
- You can jump to the action location by left-clicking on the timestamp.
- You can overwrite a recording by right-clicking on the timestamp (see more below).
- You can also play and delete each recording with the corresponding buttons.
- If you want to play a recording and also jump to the video location at the same time, right-click the
recording play button.

Finally, you can listen to the recordings as you watch the video by ticking the box `Play recordings with video`, which 
is located next to the time label. 
 
### Keyboard shortcuts

- `left arrow`: seek backwards
- `right arrow`: seek forwards
- `space bar`: pause/play video
- `enter`: start/stop recording
- `delete` or `backspace`: delete the highlighted recording
- `m`: mute/unmute video
- `o`: overwrite highlighted recording
 
### Overwriting recording

You can override a recording by right-clicking on its timestamp on the recording panel.
Alternatively, you can press `o`, which will overwrite the highlighted recording.

In any case, you will be asked for a confirmation before overwriting the recording. 
The recording will start immediately as you confirm. To stop the recording you will have to either
click the record button or press Enter, even if you are using the hold-to-record mode
 
### Resume recording

To resume recording simply choose the same output folder you previously selected when you annotated the same video. 
This will automatically load all your recordings.

### Selecting audio device

Use the `Select microphone` menu to select the device you want to use. 
By default the program will use the first device listed in the menu.

In the unlikely case the program crashes at start time due to some issues with the audio interface, try to launch the
program as follows:
 
 ```bash
python epic_narrator.py --set_audio_device <device_id>
 ```
 
Run `python epic_narrator.py --query_audio_devices` to get the devices available in your system with their corresponding ids.

For example:

```bash
$ python epic_narrator.py --query_audio_devices
  0 HDA Intel PCH: ALC3220 Analog (hw:0,0), ALSA (2 in, 0 out)
< 1 HDA NVidia: HDMI 0 (hw:1,3), ALSA (0 in, 8 out)
  2 HDA NVidia: HDMI 1 (hw:1,7), ALSA (0 in, 8 out)
  3 DELL UZ2315H: USB Audio (hw:2,0), ALSA (2 in, 2 out)
  4 sysdefault, ALSA (128 in, 0 out)
> 5 default, ALSA (128 in, 0 out)
```

```bash
python epic_narrator.py --set_audio_device 3
```   

## Recordings

Recordings will be saved in mono uncompress format (`.wav`) sampled at the default sample rate of
your input audio interface.

## Settings

The narrator will save some settings under a directory named `epic_narrator` automatically created in your home directory.

The settings will save the path of the video you narrated last, as well as the output path and, the microphone id and a
few other things. 
