print("MILIMP Media Player")
import sys
import mili
import time
import shutil
import pygame
import pathlib
import threading
import faulthandler

pygame.mixer.pre_init(buffer=2048)

from ui.common import *
from ui.main_menus.history import HistoryUI
from ui.main_menus.settings import SettingsUI
from ui.yt_search import YTSearchUI
from ui.list_viewer import ListViewerUI
from ui.main_menus.edit_keybinds import EditKeybindsUI
from health_check import main as health_check
from ui.music_controls import MusicControlsUI
from ui.playlist_viewer import PlaylistViewerUI
from ui.extra.discord_presence import DiscordPresence
from ui.main_menus.music_fullscreen import MusicFullscreenUI
from ui.common.data import (
    HistoryData,
    MusicData,
    Playlist,
    NotCached,
    PlaylistGroup,
    AsyncVideoclipGetter,
    YTVideoResult,
)

try:
    faulthandler.enable()
except RuntimeError:
    ...

if "win" in sys.platform or os.name == "nt":
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "damusss.milimp_media_player.1.0"
    )


class MILIMP(mili.GenericApp):
    def __init__(self):
        self.init_pygame()
        self.init_attributes()
        self.init_data_folder_check()
        self.init_load_settings()
        self.init_loading_screen()
        self.init_load_icons()
        self.init_load_data()
        self.init_mili_settings()
        self.init_try_set_icon_mac()
        self.make_bg_image()
        self.init_health_check()

    def init_load_icons(self):
        ICONS.load()
        self.window.set_icon(ICONS.playlist_cover)

    def init_health_check(self):
        thread = threading.Thread(target=health_check)
        thread.start()

    def init_pygame(self):
        pygame.init()
        super().__init__(
            pygame.Window(
                "MILIMP Media Player",
                PREFERRED_SIZES,
                resizable=True,
                borderless=True,
            )
        )
        self.window.minimum_size = WIN_MIN_SIZE
        pygame.key.set_repeat(500, 30)
        print(f"MILI {mili.VERSION_STR}")
        if mili.VERSION < (1, 0, 4) or pygame.vernum < (2, 5, 2):
            pygame.display.message_box(
                "Outdated dependencies",
                "The core dependencies of the media player are outdated, please update them to the latest version. "
                f"pygame-ce: needed >=2.5.2, found {pygame.ver}. MILI: needed >=1.0.4, found {mili.VERSION_STR}. "
                "The application will now quit.",
                "error",
                None,
                ("Understood",),
            )
            pygame.quit()
            sys.exit()

    def init_attributes(self):
        # components
        self.playlist_viewer = PlaylistViewerUI(self)
        self.list_viewer = ListViewerUI(self)
        self.yt_search = YTSearchUI(self)
        self.music_controls = MusicControlsUI(self)
        self.settings = SettingsUI(self)
        self.history = HistoryUI(self)
        self.discord_presence = DiscordPresence(self)
        self.keybinds = Keybinds(self)
        self.edit_keybinds = EditKeybindsUI(self)
        self.music_fullscreen = MusicFullscreenUI(self)
        self.prefabs = UIComponent(self)
        # settings
        self.user_framerate = 60
        self.volume = 1
        self.loops = True
        self.shuffle = False
        self.custom_title = True
        self.before_maximize_data = None
        self.maximized = False
        self.strip_youtube_id = False
        self.taskbar_height = 0
        # status
        self.start_style = mili.PADLESS | {"spacing": 0}
        self.start_time = time.time()
        self.vol_before_mute = 1
        self.view_state = "list"
        self.modal_state = "none"
        self.playlists: list[Playlist] = []
        self.history_data: list[HistoryData] = []
        self.win_focused = True
        self.ui_mult = 1
        self.input_stolen = False
        self.listening_key = False
        self.last_save = SAVE_COOLDOWN
        self.stolen_cursor = False
        self.cursor_hover = False
        self.tooltip_hover_time = 0
        self.tooltip_data = None
        self.split_screen = False
        self.split_w = self.window.size[0]
        self.split_size = self.window.size
        self.startup_covers_toload: list[tuple[MusicData, str]] = []
        # bg effect/mili
        self.bg_effect_image = None
        self.bg_black_image = None
        self.bg_effect = False
        self.bg_cache = mili.ImageCache()
        self.anims = [animation(-3) for i in range(4)]
        self.anim_settings = animation(-5)
        # menu
        self.menu_open = False
        self.menu_data: Playlist | MusicData | PlaylistGroup | YTVideoResult = None
        self.menu_buttons = None
        self.menu_pos = None
        # music
        self.music: MusicData = None
        self.music_paused = False
        self.music_index = -1
        self.music_play_time = 0
        self.music_play_offset = 0
        self.music_loops = False
        self.music_start_time = None
        # custom title
        self.tbarh = 0
        self.custom_borders = mili.CustomWindowBorders(
            self.window,
            RESIZE_SIZE,
            RESIZE_SIZE * 2,
            30,
            True,
            RATIO_MIN,
            on_resize=lambda: (self.make_bg_image(), self.on_resize_move()),
            on_move=self.on_resize_move,
        )

    def init_load_data(self):
        if not os.path.exists("data"):
            os.mkdir("data")
        for name in [
            "mp3_converted",
            "covers",
            "music_covers",
            "yt_downloads",
            "yt_temp",
        ]:
            if not os.path.exists(f"data/{name}"):
                os.mkdir(f"data/{name}")

        playlist_data = load_json("data/playlists.json", [])
        shutil.copyfile("data/playlists.json", "data/playlists_backup.json")
        history_data = load_json("data/history.json", [])

        for pdata in playlist_data:
            name = pdata["name"]
            paths = [
                pathlib.Path(path)
                if isinstance(path, str)
                else [pathlib.Path(path[0]), path[1]]
                for path in pdata["paths"]
            ]
            self.playlists.append(
                Playlist(
                    name, paths, pdata.get("groups", []), ICONS.loading, startup=self
                )
            )

        for hdata in history_data:
            obj = HistoryData.load_from_data(hdata, self)
            if obj is not None:
                self.history_data.append(obj)

        if os.path.exists("data/search_results.json"):
            data = load_json("data/search_results.json", [])
            self.yt_search.video_results = [YTVideoResult.load(dt) for dt in data]

    def init_mili_settings(self):
        self.mili.default_styles(
            text={
                "sysfont": False,
                "name": "appdata/ytfont.ttf",
                "growx": True,
                "growy": True,
            },
            line={"color": (255,) * 3},
            circle={"antialias": True},
            image={"smoothscale": True},
        )

    def init_load_settings(self):
        custom_title = True
        win_pos = self.window.position
        win_size = self.window.size
        discord_presence = False
        default_binds = self.keybinds.get_save_data()
        minip_data = [MINIP_PREFERRED_SIZES, None, True]
        data = load_json(
            "data/settings.json",
            {
                "volume": 1,
                "loops": True,
                "shuffle": False,
                "fps": 60,
                "custom_title": True,
                "win_pos": win_pos,
                "win_size": win_size,
                "before_maximize_data": None,
                "maximized": False,
                "discord_presence": discord_presence,
                "strip_youtube_id": False,
                "taskbar_height": 0,
                "videoclip_threaded": True,
                "yt_search": "",
                "yt_fetch_amount": 7,
                "yt_search_method": "yt-dlp",
                "miniplayer": minip_data,
                "keybinds": default_binds,
            },
        )
        if isinstance(data, dict):
            self.volume = data.get("volume", 1)
            self.loops = data.get("loops", True)
            self.shuffle = data.get("shuffle", False)
            self.user_framerate = data.get("fps", 60)
            custom_title = data.get("custom_title", True)
            win_pos = data.get("win_pos", win_pos)
            win_size = data.get("win_size", win_size)
            discord_presence = data.get("discord_presence", False)
            self.keybinds.load_from_data(data.get("keybinds", default_binds))
            self.maximized = data.get("maximized", False)
            self.before_maximize_data = data.get("before_maximize_data", None)
            self.strip_youtube_id = data.get("strip_youtube_id", False)
            self.taskbar_height = data.get("taskbar_height", 0)
            self.videoclip_threaded = data.get("videoclip_threaded", True)
            minip = self.music_controls.minip
            minip.last_size, minip.last_pos, minip.last_borderless = data.get(
                "miniplayer", minip_data
            )
            self.yt_search.search_entryline.set_text(data.get("yt_search", ""))
            self.yt_search.fetch_amount = data.get("yt_fetch_amount", 7)
            self.yt_search.search_method = data.get("yt_search_method", "yt-dlp")
            self.yt_search.search_dm.selected = self.yt_search.search_method
        self.target_framerate = self.user_framerate
        if win_pos != self.window.position:
            self.window.position = win_pos
        if win_size != self.window.size:
            self.window.size = win_size
        if not custom_title:
            self.toggle_custom_title()
        if discord_presence:
            self.discord_presence.start()

    def init_data_folder_check(self):
        if not os.path.exists("appdata"):
            pygame.display.message_box(
                "appdata folder not found",
                "appdata folder not found. The folder is required to load icons. "
                "If you moved the application, remember to move the appdata (and data) folder aswell. The application will now quit.",
                "error",
                None,
                ("Understood",),
            )
            pygame.quit()
            raise SystemExit

    def init_loading_screen(self):
        screen = self.window.get_surface()
        screen.fill((BG_CV,) * 3)
        txt = pygame.font.Font("appdata/ytfont.ttf", 30).render(
            "Loading tracks and covers...",
            True,
            "white",
            wraplength=int(screen.width / 1.2),
        )
        screen.blit(txt, txt.get_rect(center=(screen.width / 2, screen.height / 2)))
        self.window.flip()

    def init_try_set_icon_mac(self):
        if not (os.name == "posix" and sys.platform == "darwin"):
            return
        try:
            from AppKit import NSApplication, NSImage
            from Foundation import NSURL

            app = NSApplication.sharedApplication()
            icon_image = NSImage.alloc().initByReferencingFile_(
                "appdata/icons/playlist.png"
            )
            app.setApplicationIconImage_(icon_image)

        except ImportError:
            if not os.path.exists("ignore-pyobjc-dep.txt"):
                btn = pygame.display.message_box(
                    "Could not set taskbar icon",
                    "The module 'pyobjc' is required to set the taskbar icon on MacOS. Please make sure the module is "
                    "installed the next time you run the application. Create a file named 'ignore-pyobjc-dep.txt' "
                    "to suppress this warning.",
                    "warn",
                    None,
                    ("Understood", "Create ignore file"),
                )
                if btn == 1:
                    with open("ignore-pyobjc-dep.txt", "w") as file:
                        file.write("")
        except Exception:
            pass

    @property
    def focused(self):
        return self.win_focused or self.yt_search.embed is not None

    @property
    def music_videoclip(self):
        if self.music_controls.async_videoclip is None:
            return None
        return self.music_controls.async_videoclip.videoclip

    def toggle_custom_title(self):
        if self.custom_title:
            self.custom_title = False
            self.window.borderless = False
            self.window.resizable = True
        else:
            self.custom_title = True
            self.window.borderless = True
            self.window.resizable = True

    def get_music_pos(self):
        return (
            self.music_play_offset
            + (pygame.time.get_ticks() - self.music_play_time) / 1000
        )

    def set_music_pos(self, pos):
        if (
            self.music is None
            or not self.music.pos_supported
            or self.music.duration in [None, NotCached]
        ):
            return
        self.music_play_time = pygame.time.get_ticks()
        self.music_play_offset = pos
        pygame.mixer.music.set_pos(pos)

    def add_to_history(self):
        pos = self.get_music_pos()
        data = HistoryData(self.music, pos, self.music.duration)
        for olddata in self.history_data.copy():
            if olddata.music is self.music:
                self.history_data.remove(olddata)
        self.history_data.append(data)
        if len(self.history_data) > HISTORY_LEN:
            self.history_data.pop(0)

    def remove_from_history(self, music: MusicData):
        for olddata in self.history_data.copy():
            if olddata.music is music:
                self.history_data.remove(olddata)

    def play_music(self, music: MusicData, idx):
        if music.pending:
            self.end_music()
            return
        if self.music_controls.async_videoclip is not None:
            self.music_controls.async_videoclip.alive = False
            if self.videoclip_threaded:
                self.music_controls.async_videoclip.thread.join()
        self.music_controls.async_videoclip = None

        if self.music is not None:
            self.add_to_history()
        if not os.path.exists(music.audiopath):
            music.playlist.remove(music.audiopath)
            pygame.display.message_box(
                "Failed playing music",
                "The request music was renamed or deleted externally, therefore the path was removed from the playlist.",
                "error",
                None,
                ("Understood",),
            )
            return
        self.music = music
        self.music_paused = False
        self.music_index = idx
        self.music_start_time = time.time()
        self.music_play_offset = 0
        if self.music.duration is NotCached:
            self.music.cache_duration()

        if self.music.isvideo:
            self.music_controls.async_videoclip = AsyncVideoclipGetter(
                str(self.music.realpath)
            )
            if self.videoclip_threaded:
                thread = threading.Thread(
                    target=self.music_controls.async_videoclip.loop
                )
                self.music_controls.async_videoclip.thread = thread
                thread.start()
            else:
                self.music_controls.async_videoclip.load_videoclip()

        self.music_controls.offset = 0
        self.music_controls.offset_restart_time = pygame.time.get_ticks()
        self.music_controls.music_videoclip_cover = None
        self.music_controls.last_videoclip_cover = None

        pygame.mixer.music.load(self.music.audiopath)
        pygame.mixer.music.play(0)
        pygame.mixer.music.set_endevent(MUSIC_ENDEVENT)
        pygame.mixer.music.set_volume(self.volume)

        self.music_play_time = pygame.time.get_ticks()
        self.discord_presence.update()

    def end_music(self):
        if self.music_controls.async_videoclip is not None:
            self.music_controls.async_videoclip.alive = False
            if self.videoclip_threaded:
                self.music_controls.async_videoclip.thread.join()
        self.close_menu()
        if self.modal_state == "fullscreen":
            self.modal_state = "none"
        if self.music is not None:
            self.add_to_history()
        self.music = None
        self.music_paused = False
        self.bg_effect = False
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        if self.music_controls.minip.window is not None:
            self.music_controls.minip.close()
        if self.music_videoclip is not None:
            self.music_videoclip.close()
        self.music_controls.async_videoclip = None
        self.discord_presence.update()
        self.music_controls.clean_ui = False

    def save(self):
        if self.music is not None:
            self.add_to_history()
        playlist_data = [
            {
                "name": p.name,
                "paths": [
                    [str(m.realpath), "converted"] if m.converted else str(m.realpath)
                    for m in p.musiclist
                ],
                "groups": [group.get_save_data() for group in p.groups],
            }
            for p in self.playlists
        ]
        history_data = [history.get_save_data() for history in self.history_data]
        write_json("data/playlists.json", playlist_data)
        write_json("data/history.json", history_data)
        minip = self.music_controls.minip
        minip.save_state()
        write_json(
            "data/settings.json",
            {
                "volume": self.volume,
                "loops": self.loops,
                "shuffle": self.shuffle,
                "fps": self.user_framerate,
                "custom_title": self.custom_title,
                "win_pos": self.window.position,
                "win_size": self.window.size,
                "before_maximize_data": self.before_maximize_data,
                "maximized": self.maximized,
                "discord_presence": self.discord_presence.active,
                "strip_youtube_id": self.strip_youtube_id,
                "taskbar_height": self.taskbar_height,
                "videoclip_threaded": self.videoclip_threaded,
                "yt_search": self.yt_search.search_entryline.text,
                "yt_fetch_amount": self.yt_search.fetch_amount,
                "yt_search_method": self.yt_search.search_method,
                "miniplayer": [minip.last_size, minip.last_pos, minip.last_borderless],
                "keybinds": self.keybinds.get_save_data(),
            },
        )
        for playlist in self.playlists:
            if playlist.cover is not None:
                if not os.path.exists(f"data/covers/{playlist.name}.png"):
                    pygame.image.save(
                        playlist.cover, f"data/covers/{playlist.name}.png"
                    )
        if len(self.yt_search.video_results) > 0:
            write_json(
                "data/search_results.json",
                [video.save() for video in self.yt_search.video_results],
            )
        if os.path.exists("data/yt_temp"):
            thumbs = set([video.thumbnail for video in self.yt_search.video_results])
            channels = set([video.channel_id for video in self.yt_search.video_results])
            for file in os.listdir("data/yt_temp"):
                name = file.removesuffix(".png").removesuffix(".jpg")
                if name.startswith("channel_"):
                    if name.removeprefix("channel_") not in channels:
                        os.remove(f"data/yt_temp/{file}")
                else:
                    if name not in thumbs:
                        os.remove(f"data/yt_temp/{file}")
        print("Data saved correctly")

    def update(self):
        self.window.title = f"MILIMP (FPS: {self.clock.get_fps():.0f})"
        if pygame.time.get_ticks() - self.last_save >= SAVE_COOLDOWN:
            self.last_save = pygame.time.get_ticks()
            self.save()

        if self.startup_covers_toload is not None:
            llen = len(self.startup_covers_toload)
            if llen > 0:
                for i in range(min(10, llen)):
                    obj, path = self.startup_covers_toload.pop()
                    obj.load_cover_async(path, ICONS.loading)
            else:
                self.startup_covers_toload = None

        self.target_framerate = self.user_framerate
        if (
            not self.focused
            and (
                self.music_controls.music_videoclip_cover is None
                or self.music_paused
                or self.music is None
            )
            and (
                not self.music_controls.minip.focused
                or self.music_controls.minip.window is None
            )
        ):
            self.target_framerate = 10

        self.stolen_cursor = False
        self.cursor_hover = False
        if self.custom_title and self.can_abs_interact():
            self.stolen_cursor = self.custom_borders.update()

        ratio = self.window.size[0] / self.window.size[1]
        if ratio < RATIO_MIN:
            self.window.size = (self.window.size[1] * RATIO_MIN, self.window.size[1])
            self.make_bg_image()

        multx = self.window.size[0] / UI_SIZES[0]
        multy = self.window.size[1] / UI_SIZES[1]
        self.ui_mult = min(1.2, max(0.4, (multx * 0.1 + multy * 1) / 1.1))

        if self.custom_title and not self.music_controls.super_fullscreen:
            self.tbarh = 30
        else:
            self.tbarh = 0

        self.start_style = mili.PADLESS | {"spacing": 0}
        mili.animation.update_all()
        self.input_stolen = False

        if (
            self.discord_presence.active
            and pygame.time.get_ticks() - self.discord_presence.last_update
            >= DISCORD_COOLDOWN
        ):
            self.discord_presence.update()

        if self.discord_presence.connect_error is not None:
            self.discord_presence.show_error()
        else:
            if self.discord_presence.connecting:
                self.discord_presence.update_connecting()

        if len(mili.get_font_cache()) > 20:
            mili.clear_font_cache()

        self.split_w = self.window.size[0]
        self.split_size = self.window.size
        self.split_screen = False
        if (
            self.window.size[0] >= self.window.size[1] * 1.4
            and self.music is not None
            and self.modal_state != "fullscreen"
        ):
            self.split_screen = True
            self.split_w = self.window.size[0] / SPLIT_SCREEN
            self.split_size = (self.split_w, self.window.size[1])

        self.music_controls.videoclip_rects = []
        if self.music_controls.async_videoclip is not None:
            self.music_controls.async_videoclip.active = False

    def ui(self):
        self.mili.rect({"color": (BG_CV,) * 3, "border_radius": 0})
        if self.custom_title:
            self.mili.rect(
                {
                    "color": (BORDER_CV,) * 3,
                    "outline": 1,
                    "draw_above": True,
                    "border_radius": 0,
                }
            )
        self.ui_bg_effect()
        self.ui_top()

        left_perc = 100 * (self.split_w / self.window.size[0])
        right_perc = 100 - left_perc
        if self.split_screen:
            self.mili.begin(
                None,
                mili.FILL | mili.X | mili.PADLESS | {"spacing": 0, "blocking": None},
            )
        with self.mili.begin(
            None,
            {
                "fillx": f"{left_perc}" if self.split_screen else True,
                "filly": True,
                "blocking": None,
            }
            | mili.PADLESS,
        ):
            self.mili.id_checkpoint(20)
            if self.modal_state != "fullscreen":
                if self.view_state == "list":
                    self.list_viewer.ui()
                elif self.view_state == "playlist":
                    self.playlist_viewer.ui()
                elif self.view_state == "search":
                    self.yt_search.ui()
            else:
                if self.view_state == "list":
                    self.list_viewer.ui_check()
                elif self.view_state == "playlist":
                    self.playlist_viewer.ui_check()
                elif self.view_state == "search":
                    self.yt_search.ui_check()
                self.mili.element(None, {"filly": True, "blocking": None})

            if self.modal_state == "settings":
                self.settings.ui()
            elif self.modal_state == "fullscreen":
                self.music_fullscreen.ui()
            elif self.modal_state == "history":
                self.history.ui()
            elif self.modal_state == "keybinds":
                self.edit_keybinds.ui()

            if not self.split_screen:
                self.mili.id_checkpoint(5000)
                self.music_controls.ui()

            self.mili.id_checkpoint(5100)
            if (
                self.playlist_viewer.modal_state == "none"
                and self.list_viewer.modal_state == "none"
                and self.yt_search.modal_state == "none"
                and self.modal_state == "none"
            ):
                self.prefabs.ui_overlay_btn(
                    self.anim_settings,
                    self.open_settings,
                    ICONS.settings,
                    0,
                    tooltip="Open settings",
                )

        if self.split_screen:
            with self.mili.begin(
                None,
                {
                    "fillx": f"{right_perc}",
                    "filly": True,
                    "spacing": 0,
                    "blocking": None,
                }
                | mili.PADLESS,
            ):
                self.mili.id_checkpoint(4950)
                self.music_controls.ui_split_screen()
                self.mili.id_checkpoint(5000)
                self.music_controls.ui()
            self.mili.end()

        if (
            self.view_state == "list"
            and self.custom_title
            and pygame.key.get_pressed()[pygame.K_BACKSLASH]
        ):
            self.mili.text_element(
                f"developer version {DEV_VERSION}",
                {"size": self.mult(13), "color": (100,) * 3},
                None,
                mili.FLOATING | {"blocking": None},
            )

        if self.modal_state != "none" and self.menu_data != "controls":
            self.close_menu()
        self.mili.id_checkpoint(5200)
        if self.menu_open:
            self.ui_menu()
        self.mili.id_checkpoint(5500)

        if not self.cursor_hover:
            self.tooltip_data = None
        elif self.tooltip_data:
            if pygame.time.get_ticks() - self.tooltip_hover_time >= TOOLTIP_COOLDOWN:
                self.ui_tooltip()

        if not self.stolen_cursor and self.cursor_hover and self.focused:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        elif not self.stolen_cursor and self.focused:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if not self.custom_borders.dragging and not self.custom_borders.resizing:
            self.custom_borders.cumulative_relative = pygame.Vector2()

        if self.music_controls.async_videoclip is not None:
            self.music_controls.async_videoclip.rects = (
                self.music_controls.videoclip_rects
            )

    def ui_tooltip(self):
        pad = self.mult(2)
        txtstyle = {
            "size": self.mult(13),
            "color": (120,) * 3,
            "slow_grow": True,
            "pady": pad,
            "padx": pad,
        }
        size = self.mili.text_size(self.tooltip_data, txtstyle)
        if size.x > self.window.size[0] / 1.1:
            txtstyle["wraplen"] = self.window.size[0] / 1.1
            size = self.mili.text_size(self.tooltip_data, txtstyle)
        mpos = pygame.Vector2(pygame.mouse.get_pos())
        posx = min(mpos.x, self.window.size[0] - size.x - pad * 4)
        posy = max(mpos.y - pad * 3 - size.y, pad * 2)
        if self.mili.element(
            ((posx, posy), (0, 0)),
            {"blocking": False, "ignore_grid": True, "parent_id": 0, "z": 999999},
        ):
            self.mili.rect({"color": (10,) * 3, "border_radius": 0})
            self.mili.text(self.tooltip_data, txtstyle)
            self.mili.rect({"color": (30,) * 3, "outline": 1, "border_radius": 0})

    def ui_top(self):
        if self.custom_title:
            with self.mili.begin(
                (0, 0, 0, self.tbarh), {"fillx": True, "blocking": False}
            ):
                self.mili.rect({"border_radius": 0, "color": (BORDER_CV / 8,) * 3})

                self.prefabs.ui_overlay_top_btn(
                    self.anims[0],
                    self.quit,
                    ICONS.close,
                    "right",
                    red=True,
                    tooltip="Quit app",
                )
                self.prefabs.ui_overlay_top_btn(
                    self.anims[1],
                    self.action_maximize,
                    ICONS.maximize,
                    "right",
                    1,
                    tooltip="Restore window" if self.maximized else "Maximize window",
                )
                self.prefabs.ui_overlay_top_btn(
                    self.anims[2],
                    self.action_minimize,
                    ICONS.minimize,
                    "right",
                    2,
                    tooltip="Minimize window",
                )
                self.prefabs.ui_overlay_top_btn(
                    self.anims[3],
                    self.toggle_custom_title,
                    ICONS.resize,
                    "right",
                    3,
                    tooltip="Disable custom borders",
                )
        else:
            self.prefabs.ui_overlay_top_btn(
                self.anims[0], self.quit, ICONS.close, "right", tooltip="Quit app"
            )
        if self.view_state == "playlist":
            self.playlist_viewer.ui_top_buttons()
        elif self.view_state == "list":
            self.list_viewer.ui_top_buttons()
        elif self.view_state == "search":
            self.yt_search.ui_top_buttons()

    def ui_bg_effect(self):
        if not self.bg_effect:
            return
        self.mili.image(self.bg_effect_image, {"ready": True})
        self.mili.image(self.bg_black_image, {"cache": self.bg_cache, "ready": True})

    def ui_menu(self):
        with self.mili.begin(
            (self.menu_pos, (0, 0)),
            {
                "resizex": True,
                "resizey": True,
                "ignore_grid": True,
                "parent_id": 0,
                "axis": "x",
                "z": 9999,
                "padx": self.mult(7),
                "pady": self.mult(7),
                "blocking": None,
            },
        ) as menu:
            self.mili.rect({"color": (MENU_CV[0],) * 3, "border_radius": "50"})
            self.mili.rect(
                {"color": (MENU_CV[1],) * 3, "border_radius": "50", "outline": 1}
            )
            for bdata in self.menu_buttons:
                br = "50"
                tooltip = None
                if len(bdata) == 3:
                    bimage, baction, banim = bdata
                elif len(bdata) == 4:
                    if len(bdata[-1]) <= 2:
                        bimage, baction, banim, br = bdata
                    else:
                        bimage, baction, banim, tooltip = bdata
                elif len(bdata) == 5:
                    bimage, baction, banim, br, tooltip = bdata
                self.prefabs.ui_image_btn(bimage, baction, banim, 40, br, tooltip)
            if (
                not menu.absolute_hover
                and any([btn is True for btn in pygame.mouse.get_pressed()])
                and (
                    self.music_controls.dots_rect is None
                    or not self.music_controls.dots_rect.collidepoint(
                        pygame.mouse.get_pos()
                    )
                )
            ):
                self.close_menu()

    def tick_tooltip(self, text):
        if text != self.tooltip_data:
            self.tooltip_data = text
            self.tooltip_hover_time = pygame.time.get_ticks()

    def open_settings(self):
        self.modal_state = "settings"

    def change_state(self, state):
        self.view_state = state
        self.close_menu()
        self.mili.clear_memory()
        self.discord_presence.update()

    def close_menu(self):
        if self.menu_buttons is not None:
            for btndata in self.menu_buttons:
                anim = btndata[2]
                anim.goto_a()
        self.menu_open = False
        self.menu_buttons = None
        self.menu_pos = None

    def open_menu(self, data, *buttons, pos=None):
        self.menu_open = True
        self.menu_data = data
        self.menu_buttons = buttons
        if pos is None:
            self.menu_pos = pygame.mouse.get_pos()
        else:
            self.menu_pos = pos

    def mult(self, size):
        return max(1, int(size * self.ui_mult))

    def action_maximize(self):
        if self.maximized:
            do_drag = pygame.Rect(0, 0, self.window.size[0], 30).collidepoint(
                pygame.mouse.get_pos()
            )
            self.window.position = self.before_maximize_data[0]
            self.window.size = self.before_maximize_data[1]
            self.maximized = False
            self.before_maximize_data = None
            self.custom_borders.resizing = self.custom_borders.dragging = False
            if do_drag:
                self.custom_borders.dragging = True
                pygame.mouse.set_pos((self.window.size[0] / 2, 15))
                self.custom_borders._press_rel = pygame.mouse.get_pos()
                self.custom_borders._press_global = (
                    pygame.Vector2(pygame.mouse.get_pos()) + self.window.position
                )
                self.custom_borders._start_val = pygame.Vector2(self.window.position)
        else:
            self.before_maximize_data = self.window.position, self.window.size
            self.window.position = (0, 0)
            desktop_size = pygame.display.get_desktop_sizes()[0]
            self.window.size = (desktop_size[0], desktop_size[1] - self.taskbar_height)
            self.maximized = True
        self.make_bg_image()

    def action_minimize(self):
        self.window.minimize()

    def on_resize_move(self):
        if self.maximized and self.custom_borders.relative.length() != 0:
            self.action_maximize()

    def can_interact(self):
        return (
            self.can_abs_interact()
            and not self.custom_borders.resizing
            and not self.custom_borders.dragging
            and self.custom_borders.cumulative_relative.length() == 0
            and (
                self.yt_search.embed is None
                or not self.yt_search.embed_ui.rect.collidepoint(
                    pygame.mouse.get_pos(True)
                )
            )
        )

    def can_abs_interact(self):
        if self.music_controls.minip.window is None:
            return True
        return not self.music_controls.minip.focused and self.focused

    def make_bg_image(self):
        self.bg_black_image = pygame.Surface(self.window.size, pygame.SRCALPHA)
        self.bg_effect_image = pygame.Surface(self.window.size, pygame.SRCALPHA)
        for i in range(self.bg_black_image.height):
            alpha = pygame.math.lerp(0, 255, i / (self.bg_black_image.height / 1.5))
            self.bg_black_image.fill(
                (0, 0, 0, alpha), (0, i, self.bg_black_image.width, 1)
            )

    def event(self, event):
        self.shortcuts_event(event)
        if event.type == pygame.WINDOWFOCUSGAINED and event.window == self.window:
            self.win_focused = True
            if self.yt_search.embed is not None:
                self.yt_search.embed.send("show")
        if event.type == pygame.WINDOWFOCUSLOST and event.window == self.window:
            self.win_focused = False
            if self.yt_search.embed is not None:
                if not pygame.Rect(self.window.position, self.window.size).collidepoint(
                    pygame.mouse.get_pos(True)
                ) and (
                    self.music_controls.minip.window is None
                    or not self.music_controls.minip.window.focused
                ):
                    self.yt_search.embed.send("hide")
            self.close_menu()
        if event.type == pygame.WINDOWRESIZED and event.window == self.window:
            self.make_bg_image()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.tooltip_data = None
            if self.menu_open:
                self.close_menu()
                return
        self.music_controls.event(event)
        if not self.can_interact():
            return
        if self.modal_state == "settings":
            if self.settings.event(event):
                return
        elif self.modal_state == "history":
            if self.history.event(event):
                return
        elif self.modal_state == "keybinds":
            if self.edit_keybinds.event(event):
                return
        elif self.modal_state == "fullscreen":
            if self.music_fullscreen.event(event):
                return
        if self.view_state == "list":
            self.list_viewer.event(event)
        elif self.view_state == "playlist":
            self.playlist_viewer.event(event)
        elif self.view_state == "search":
            self.yt_search.event(event)

    def shortcuts_event(self, event):
        if self.listening_key:
            return
        if event.type == pygame.KEYDOWN:
            if Keybinds.check("quit", event):
                self.quit()
            elif Keybinds.check("save", event):
                self.save()
            elif self.can_interact():
                if Keybinds.check("toggle_settings", event):
                    if self.modal_state == "settings":
                        self.settings.close()
                    else:
                        self.open_settings()
                elif Keybinds.check("new/add", event):
                    if self.view_state == "list":
                        if self.list_viewer.modal_state != "new_playlist":
                            self.list_viewer.action_new()
                    elif self.view_state == "playlist":
                        if self.playlist_viewer.modal_state != "add":
                            self.playlist_viewer.action_add_music()
                elif Keybinds.check("open_history", event):
                    self.open_settings()
                    self.settings.action_history()
                elif Keybinds.check("open_keybinds", event):
                    self.open_settings()
                    self.settings.action_keybinds()
                elif Keybinds.check("minimize_window", event):
                    self.action_minimize()
                elif Keybinds.check("maximize_window", event):
                    self.action_maximize()

    def quit(self):
        if self.yt_search.embed is not None:
            self.yt_search.embed.close()
        if self.music_controls.async_videoclip is not None:
            self.music_controls.async_videoclip.alive = False
            if self.videoclip_threaded:
                self.music_controls.async_videoclip.thread.join()
        for playlist in self.playlists:
            for music in playlist.musiclist:
                if music.pending:
                    btn = pygame.display.message_box(
                        "Wait before closing",
                        "Some tracks are still being converted. Please wait until they are converted "
                        "before closing the application, otherwise the files will be corrupted.",
                        "warn",
                        None,
                        ("Understood", "Close Anyways"),
                    )
                    if btn == 0:
                        return
        self.save()
        print("Application quit")
        pygame.quit()
        raise SystemExit


if __name__ == "__main__":
    MILIMP().run()
