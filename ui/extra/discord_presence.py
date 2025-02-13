import pygame
import typing
import threading
from ui.common import parse_music_stem

if typing.TYPE_CHECKING:
    from MILIMP import MILIMP


def discord_presence_connect(presence: "DiscordPresence"):
    try:
        presence.presence.connect()
    except presence.pypresence.DiscordNotFound as exc:
        presence.connect_error = str(exc)
        presence.discord_not_found = True
        return
    except presence.pypresence.PyPresenceException as exc:
        presence.connect_error = str(exc)
        presence.discord_not_found = False
        return
    presence.active = True
    presence.connecting = False
    presence.last_update = -9999


class DiscordPresence:
    def __init__(self, app: "MILIMP"):
        self.app = app
        self.active = False
        self.last_update = 0
        self.connect_error = None
        self.discord_not_found = False
        self.connect_start_time = 0
        self.connecting = False
        try:
            import pypresence

            self.pypresence = pypresence
            self.presence = pypresence.Presence("1278352362133782559")
        except (ImportError, ModuleNotFoundError):
            self.pypresence = None

    def start(self):
        if self.connecting:
            return
        if self.pypresence is None:
            btn = pygame.display.message_box(
                "Missing pypresence module",
                "Could not activate the discord presence as the 'pypresence' module is missing. "
                "Close the application, install the module (`pip install pypresence`) and try again.",
                "error",
                None,
                ("Understood", "Close App"),
            )
            if btn == 1:
                self.app.quit()
            return
        if self.connecting:
            return
        self.active = False
        self.connecting = True
        self.connect_start_time = pygame.time.get_ticks()
        thread = threading.Thread(target=discord_presence_connect, args=(self,))
        thread.start()

    def update(self):
        self.last_update = pygame.time.get_ticks()
        if not self.active:
            return
        if self.pypresence is None:
            return

        state = "Idle"
        details = None
        if self.app.view_state == "playlist":
            details = f"Playlist: {self.app.playlist_viewer.playlist.name}"
        elif self.app.view_state == "search":
            details = "Searching Music"
        start = self.app.start_time
        small_image = None
        small_text = None

        if self.app.music is not None:
            state = (
                f"Listening to: {parse_music_stem(self.app, self.app.music.realstem)}"
            )
            details = f"Playlist: {self.app.music.playlist.name}"
            start = self.app.music_start_time
            small_image = "mili_miniplayer_icon"
            small_text = "Music is playing"
            if self.app.music_paused:
                small_image = "mili_paused_icon"
                small_text = "Music is paused"

        try:
            self.presence.update(
                state=state,
                details=details,
                start=start,
                large_image="MILIMP_logo",
                large_text="MILIMP is connected to Discord",
                small_image=small_image,
                small_text=small_text,
            )
        except self.pypresence.PipeClosed:
            self.end()
            return
        except self.pypresence.PyPresenceException as exc:
            pygame.display.message_box(
                "Failed to update the discord presence",
                f"Updating the discord presence raised the following exception: '{
                    exc
                }'.",
                "error",
                None,
                ("Understood",),
            )
            self.active = False
            try:
                self.end()
            except Exception:
                pass

    def update_connecting(self):
        if pygame.time.get_ticks() - self.connect_start_time >= 10000:
            self.connecting = False
            self.active = False
            self.connect_error = None
            pygame.display.message_box(
                "Failed to connect to discord",
                "The connection with discord took too much time. Make sure you have an internet connection and try to connect again.",
                "error",
                None,
                ("Understood",),
            )

    def show_error(self):
        if self.discord_not_found:
            pygame.display.message_box(
                "Failed to connect to discord",
                "Discord must be installed and running for the discord presence to work.",
                "error",
                None,
                ("Understood",),
            )
        else:
            pygame.display.message_box(
                "Failed to connect to discord",
                f"The module 'pypresence' raised this exception while trying to connect to discord: '{
                    self.connect_error
                }'. "
                "Make sure discord is installed and open and that you have internet and try to connect again.",
                "error",
                None,
                ("Understood",),
            )
        self.connect_error = None
        self.discord_not_found = False
        self.connecting = False

    def end(self):
        self.active = False
        if self.pypresence is None:
            return
        self.presence.close()

    def toggle(self):
        if self.active:
            self.end()
        else:
            self.start()
