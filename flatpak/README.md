# Instructions to build Epic Narrator with flatpak

First of all, install [flatpak-builder](http://docs.flatpak.org/en/latest/flatpak-builder.html) 
on your system (using apt, yum, dnf or whatever your distribution uses)

You will then need to install GTK's SDK:

```bash
$ flatpak install flathub org.gnome.Sdk//3.32
$ flatpak install flathub org.gnome.Platform//3.32
```

Then `cd` into this directory, keeping the folder structure untouched, and run

```bash
$ flatpak-builder --repo=repo --force-clean build-dir epic.narrator.json
``` 

This will download all the libraries' sources and will compile everything.
Expect some 20-30 minutes for the command to finish, since it will build a lot of stuff,
e.g. `vlc` and all its dependencies. Fortunately, everything is cached internally, so
following builds will be fast.

Once the command above has finished, run the command below to create the bundle:

```bash
$ flatpak build-bundle repo epic_narrator.flatpak uk.ac.bris.epic.narrator
```

This will create a file named `epic_narrator.flatpak`. This is the bundle containing the
narrator packed with all the dependencies. The bundle can then be installed with

```bash
$ flatpak install epic_narrator.flatpak
```

Once installed, the narrator can be run with

```bash
$ flatpak run uk.ac.bris.epic.narrator
```

### Building script

The two building commands are run by the simple script `build_flatpak.sh`. 
Once you're set up, you may thus want to run the following for convenience:   

```bash
$ sh build_flatpak.sh
```
