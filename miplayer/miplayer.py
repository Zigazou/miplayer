import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from minitel.Minitel import Minitel
import serial
import glob
import os
import time

from threading import Thread

def detect_serials():
    return [
        device for device in glob.glob("/dev/ttyUSB?")
        if os.access(device, os.R_OK) and os.access(device, os.W_OK)
    ]

class Player(Thread):
    def __init__(self, directory, minitel, pause):
        super(Player, self).__init__()

        self.directory = directory
        self.minitel = minitel
        self.pause = pause

        self.position = 0
        self.counter = -1

        self.files = glob.glob(self.directory + "/*.vdt")

    def next_file(self):
        filepath = self.files[self.position]

        self.position += 1
        if self.position >= len(self.files):
            self.position = 0

        return filepath

    def pause_between_pages(self):
        if self.counter < 0:
            self.counter = self.pause
            return False

        time.sleep(1)

        if self.minitel.sortie.empty():
            self.counter -= 1

        return True

    def run(self):
        self.alive = True
        counter = self.pause

        try:
            while self.alive:
                if self.pause_between_pages():
                    continue

                with open(self.next_file(), 'r') as content_file:
                    content = content_file.read()

                self.minitel.envoyer(content)
        finally:
            with self.minitel.sortie.mutex:
                self.minitel.sortie.queue.clear()

    def stop(self):

        self.alive = False
        self.join()

class MiPlayerHandler:
    def __init__(self, builder, window):
        self.minitels = []
        self.directories = []
        self.threads = []
        self.window = window

        self.labels = [
            builder.get_object("lbl_minitel1"),
            builder.get_object("lbl_minitel2"),
            builder.get_object("lbl_minitel3"),
            builder.get_object("lbl_minitel4"),
        ]

        self.plays = [
            builder.get_object("tbn_play1"),
            builder.get_object("tbn_play2"),
            builder.get_object("tbn_play3"),
            builder.get_object("tbn_play4"),
        ]

        self.playlists = [
            builder.get_object("btn_playlist1"),
            builder.get_object("btn_playlist2"),
            builder.get_object("btn_playlist3"),
            builder.get_object("btn_playlist4"),
        ]

        pass

    def reset(self):
        for minitel in self.minitels:
            minitel.close()

        self.directories = []
        self.threads = []

        for label in self.labels:
            label.set_text("Unknown")
            label.set_sensitive(False)

        for play in self.plays:
            play.set_sensitive(False)

        for playlist in self.playlists:
            playlist.set_sensitive(False)

    def refresh(self):
        self.reset()

        devices = detect_serials()

        for i in range(0, len(devices)):
            minitel = Minitel(devices[i])
            minitel.identifier()

            # Cannot identify a Minitel
            if minitel.capacite['version'] == None:
                continue

            self.minitels.append(minitel)
            self.directories.append(None)
            self.threads.append(None)

            if minitel.capacite['caracteres']:
                drcs = "DRCS"
            else:
                drcs = "-"

            label = ( minitel.capacite['nom']
                    + "\n"
                    + minitel.capacite['constructeur']
                    + "\n"
                    + minitel.capacite['version']
                    + "\n"
                    + drcs
                    )

            self.labels[i].set_text(label)
            self.labels[i].set_sensitive(True)
            self.playlists[i].set_sensitive(True)

    def on_delete_event(self):
        Gtk.main_quit()

    def on_btn_quit_clicked(self, widget):
        Gtk.main_quit()

    def on_btn_refresh_clicked(self, widget):
        pass

    def on_btn_playlist_clicked(self, widget):
        index = self.playlists.index(widget)

        dialog = Gtk.FileChooserDialog(
            "Open…",
            self.window,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            playlist = dialog.get_filename()
        else:
            playlist = None

        dialog.destroy()

        if playlist:
            self.directories[index] = playlist
            self.plays[index].set_sensitive(True)

    def on_tbn_play_toggled(self, widget):
        index = self.plays.index(widget)

        if widget.get_active():
            self.threads[index] = Player(
                self.directories[index],
                self.minitels[index],
                3
            )

            try:
                self.threads[index].start()
            except (KeyboardInterrupt, SystemExit):
                pass
        else:
            self.threads[index].stop()
            self.threads[index] = None

        self.playlists[index].set_sensitive(not widget.get_active())

def miplayer():
    builder = Gtk.Builder()
    builder.add_from_file("miplayer.glade")
    window = builder.get_object("miplayer")
    window.fullscreen()
    mihandler = MiPlayerHandler(builder, window)
    builder.connect_signals(mihandler)
    mihandler.refresh()
    window.show_all()

    Gtk.main()

miplayer()

