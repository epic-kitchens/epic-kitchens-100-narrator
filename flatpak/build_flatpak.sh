#!/bin/sh
flatpak-builder --repo=repo --force-clean build-dir epic.narrator.json
flatpak build-bundle repo epic_narrator.flatpak uk.ac.bris.epic.narrator
