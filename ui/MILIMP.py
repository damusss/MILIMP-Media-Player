import sys
import time
import shutil
import pathlib
from pygame._sdl2 import video as pgvideo
from pygame import _sdl2 as pgsdl2

from ui.common import *
from ui.state import MusicState
from ui.main_menus.history import HistoryUI
from ui.main_menus.settings import SettingsUI
from ui.main_menus.state_info import StateInfoUI
from ui.main_menus.notifications import NotificationsUI
from ui.main_menus.backup_save import BackupSaveUI
from ui.main_menus.health_check import HealthCheckUI
from ui.main_menus.queue import QueueUI
from ui.yt_search import YTSearchUI
from ui.list_viewer import ListViewerUI
from ui.explorer import ExplorerUI
from ui.main_menus.edit_keybinds import EditKeybindsUI
from ui.music_controls import MusicControlsUI
from ui.playlist_viewer import PlaylistViewerUI
from ui.extra.discord_presence import DiscordPresence
from ui.main_menus.music_fullscreen import MusicFullscreenUI
from ui.common.data import (
    HistoryData,
    MusicData,
    Playlist,
    PlaylistGroup,
    YTVideoResult,
    Notification,
    MenuButton,
    safeguard_window,
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

    def init_load_icons(self):
        ICONS.load()
        self.window.set_icon(ICONS.playlist_cover)

    def init_pygame(self):
        if os.path.exists(RUNNING_INSTANCE_SENTINEL):
            pygame.display.message_box(
                "Instance Already Running",
                f"An instance of the same application is already running. Use that one or close that one before running again. If your previous app has crashed, delete the {RUNNING_INSTANCE_SENTINEL} file.",
                "info",
            )
            sys.exit()
        with open(RUNNING_INSTANCE_SENTINEL, "w") as file:
            file.write("")
        pygame.init()
        win = pygame.Window(
            "MILIMP Media Player",
            PREFERRED_SIZES,
            resizable=True,
            borderless=True,
        )
        if USE_RENDERER:
            self.canva = pgvideo.Renderer(win)
        else:
            self.canva = None
        super().__init__(win, canva=self.canva)
        self.window.minimum_size = WIN_MIN_SIZE
        pygame.key.set_repeat(500, 30)
        print(f"MILI {mili.VERSION_STR}")
        if mili.VERSION < (1, 0, 6) or pygame.vernum < (2, 5, 5):
            pygame.display.message_box(
                "Outdated dependencies",
                "The core dependencies of the media player are outdated, please update them to the latest version. "
                f"pygame-ce: needed >=2.5.5, found {pygame.ver}. MILI: needed >=1.0.6, found {mili.VERSION_STR}. "
                "The application will now quit.",
                "error",
                None,
                ("Understood",),
            )
            pygame.quit()
            sys.exit()
        if not os.path.exists("data"):
            os.mkdir("data")
        self.custom_borders = mili.CustomWindowBorders(
            self.window,
            RESIZE_SIZE,
            RESIZE_SIZE * 2,
            30,
            True,
            RATIO_MIN,
        )
        display_size = pygame.display.get_desktop_sizes()[0]
        self.custom_behavior = mili.CustomWindowBehavior(
            self.window,
            self.custom_borders,
            display_size,
            mili.CustomWindowBehavior.usable_display_area_from_taskbar(
                display_size, 30, "bottom"
            ),
        )

    def init_attributes(self):
        # components
        self.state = MusicState(self)
        self.playlist_viewer = PlaylistViewerUI(self)
        self.list_viewer = ListViewerUI(self)
        self.yt_search = YTSearchUI(self)
        self.explorer = ExplorerUI(self)
        self.music_controls = MusicControlsUI(self)
        self.settings = SettingsUI(self)
        self.history = HistoryUI(self)
        self.discord_presence = DiscordPresence(self)
        self.keybinds = Keybinds(self)
        self.edit_keybinds = EditKeybindsUI(self)
        self.music_fullscreen = MusicFullscreenUI(self)
        self.state_info = StateInfoUI(self)
        self.notifications_ui = NotificationsUI(self)
        self.queue = QueueUI(self)
        self.backup_save = BackupSaveUI(self)
        self.health_check = HealthCheckUI(self)
        self.prefabs = UIComponent(self)
        self.mult = self.prefabs.mult
        self.mult_fs = self.prefabs.mult_fs
        # settings
        self.custom_title = True
        self.strip_youtube_id = False
        self.universal_font = False
        self.save_use_renderer = USE_RENDERER
        # status
        self.start_style = mili.PADLESS | {"spacing": 0}
        self.start_time = time.time()
        self.view_state = "list"
        self.modal_state = "none"
        self.playlists: list[Playlist] = []
        self.history_data: list[HistoryData] = []
        self.favorites: list[MusicData] = []
        self.win_focused = True
        self.ui_mult = 1
        self.input_stolen = False
        self.listening_key = False
        self.last_save = 0
        self.stolen_cursor = False
        self.cursor_hover = False
        self.tooltip_hover_time = 0
        self.tooltip_data = None
        self.split_screen = False
        self.split_w = self.window.size[0]
        self.split_size = self.window.size
        self.aborted = False
        self.notifications: list[Notification] = []
        self.before_super_fullscreen_height = 0
        self.super_fullscreen = False
        # bg effect/mili
        self.bg_effect_image = None
        self.bg_black_image = None
        self.bg_cache = mili.ImageCache()
        self.anims = [animation(-3) for i in range(4)]
        self.anim_settings = animation(-5)
        # menu
        self.menu_open = False
        self.menu_data: Playlist | MusicData | PlaylistGroup | YTVideoResult = None
        self.menu_buttons: list[MenuButton] = None
        self.menu_pos = None
        # music
        self.tbarh = 0

    def init_load_data(self):
        if not os.path.exists("data"):
            os.mkdir("data")
        for name in [
            "mp3_converted",
            "covers",
            "music_covers",
            "yt_downloads",
            "yt_temp",
            "yt_playlists",
        ]:
            if not os.path.exists(f"{DATA_PATH}/{name}"):
                os.mkdir(f"{DATA_PATH}/{name}")

        playlist_data = load_json(f"{DATA_PATH}/playlists.json", [])
        shutil.copyfile(
            f"{DATA_PATH}/playlists.json", f"{DATA_PATH}/playlists_backup.json"
        )
        history_data = load_json(f"{DATA_PATH}/history.json", [])

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
                    name,
                    paths,
                    pdata.get("groups", []),
                    pdata.get("yt_link", None),
                    pdata.get("yt_name", None),
                    {
                        pathlib.Path(strpath): alias
                        for strpath, alias in pdata.get("aliases", {}).items()
                    },
                    pdata.get("folder_path", None),
                    [pathlib.Path(strpath) for strpath in pdata.get("favorites", [])],
                    ICONS.loading,
                    startup=self,
                )
            )

        for hdata in history_data:
            obj = HistoryData.load_from_data(hdata, self)
            if obj is not None:
                self.history_data.append(obj)

        if os.path.exists(f"{DATA_PATH}/search_results.json"):
            data = load_json(f"{DATA_PATH}/search_results.json", [])
            self.yt_search.video_results = [YTVideoResult.load(dt) for dt in data]

    def init_mili_settings(self):
        self.mili.default_styles(
            line={"color": (255,) * 3},
            circle={"antialias": True},
            image={"smoothscale": True},
        )
        self.apply_font()

    def init_load_settings(self):
        custom_title = True
        win_pos = self.window.position
        win_size = self.window.size
        discord_presence = False
        default_binds = self.keybinds.get_save_data()
        minip_data = [MINIP_PREFERRED_SIZES, None, True]
        data = load_json(
            f"{DATA_PATH}/settings.json",
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
                "strip_youtube_id": True,
                "taskbar_height": 0,
                "videoclip_threaded": True,
                "videoclip_on": True,
                "universal_font": False,
                "yt_search": "",
                "yt_fetch_amount": 7,
                "yt_search_method": "yt-dlp",
                "yt_show_details": True,
                "show_favorites": True,
                "last_explorer_path": os.getcwd(),
                "explorer_history": [os.getcwd()],
                "explorer_favorites": [],
                "explorer_history_idx": 0,
                "miniplayer": minip_data,
                "keybinds": default_binds,
            },
        )
        if isinstance(data, dict):
            self.state.volume = data.get("volume", 1)
            self.state.loops = data.get("loops", True)
            self.state.shuffle = data.get("shuffle", False)
            self.state.user_framerate = data.get("fps", 60)
            custom_title = data.get("custom_title", True)
            win_pos = safeguard_window(data.get("win_pos", win_pos), True)
            win_size = safeguard_window(data.get("win_size", win_size))
            discord_presence = data.get("discord_presence", False)
            self.keybinds.load_from_data(data.get("keybinds", default_binds))
            maximized = data.get("maximized", False)
            before_maximize_data = data.get("before_maximize_data", None)
            if maximized:
                self.custom_behavior.maximize()
            self.custom_behavior.before_maximized_data = before_maximize_data
            self.strip_youtube_id = data.get("strip_youtube_id", True)
            taskbar_height = data.get("taskbar_height", 0)
            self.custom_behavior.usable_display_area = (
                mili.CustomWindowBehavior.usable_display_area_from_taskbar(
                    self.custom_behavior.display_size, taskbar_height, "bottom"
                )
            )
            self.state.videoclip_threaded = data.get("videoclip_threaded", True)
            self.state.videoclip_on = data.get("videoclip_on", True)
            minip = self.music_controls.minip
            minip.last_size, minip.last_pos, minip.last_borderless = data.get(
                "miniplayer", minip_data
            )
            self.universal_font = data.get("universal_font", False)
            self.yt_search.search_entryline.set_text(data.get("yt_search", ""))
            self.yt_search.fetch_amount = data.get("yt_fetch_amount", 7)
            self.yt_search.search_method = data.get("yt_search_method", "yt-dlp")
            self.yt_search.search_dm.selected = self.yt_search.search_method
            self.list_viewer.show_favorites = data.get("show_favorites", True)
            self.explorer.last_path = pathlib.Path(
                data.get("last_explorer_path", os.getcwd())
            )
            self.explorer.history = [
                pathlib.Path(hpath)
                for hpath in data.get("explorer_history", [self.explorer.last_path])
            ]
            self.explorer.history_idx = data.get("explorer_history_idx", 0)
            self.explorer.favorites = [
                pathlib.Path(path) for path in data.get("explorer_favorites", [])
            ]
            self.playlist_viewer.yt_show_details = data.get("yt_show_details")
        self.target_framerate = self.state.user_framerate
        if win_pos != self.window.position and win_pos is not None:
            self.window.position = win_pos
        if win_size != self.window.size and win_size is not None:
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
            "Loading icons and data...",
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

    def apply_font(self):
        self.mili.default_style(
            "text",
            {
                "sysfont": False,
                "name": "appdata/universal.ttf"
                if self.universal_font
                else "appdata/ytfont.ttf",
                "growx": True,
                "growy": True,
                "cache": "auto",
            },
        )

    @property
    def focused(self):
        return self.win_focused or self.yt_search.embed is not None

    def notify(self, kind, message=None, error=False, hidden=False):
        if message is None:
            kind, message = kind
        print(message)
        self.notifications.append(Notification(kind, message, error, hidden))
        if len(self.notifications) > HISTORY_LEN:
            self.notifications.pop(0)
        return message

    def toggle_custom_title(self):
        if self.custom_title:
            self.custom_title = False
            self.window.borderless = False
            self.window.resizable = True
        else:
            self.custom_title = True
            self.window.borderless = True
            self.window.resizable = True

    def add_to_history(self):
        if self.state.music.virtual:
            return
        pos = self.state.get_music_pos()
        data = HistoryData(self.state.music, pos, self.state.music.duration)
        for olddata in self.history_data.copy():
            if olddata.music is self.state.music:
                self.history_data.remove(olddata)
        self.history_data.append(data)
        if len(self.history_data) > HISTORY_LEN:
            self.history_data.pop(0)

    def remove_from_history(self, music: MusicData):
        for olddata in self.history_data.copy():
            if olddata.music is music:
                self.history_data.remove(olddata)

    def when_end_music(self):
        self.close_menu()
        if self.modal_state == "fullscreen":
            self.modal_state = "none"
        self.discord_presence.update()

    def save(self):
        self.last_save = pygame.time.get_ticks()
        if self.state.music is not None:
            self.add_to_history()
        playlist_data = [
            {
                "name": p.name,
                "yt_link": p.yt_link,
                "yt_name": p.yt_name,
                "folder_path": str(p.folder_path) if p.is_folder else None,
                "paths": [
                    [str(m.realpath), "converted"] if m.converted else str(m.realpath)
                    for m in p.musiclist
                ],
                "groups": [group.get_save_data() for group in p.groups],
                "aliases": {str(path): alias for path, alias in p.aliases.items()},
                "favorites": [str(path) for path in p.favorites],
            }
            for p in self.playlists
        ]
        history_data = [history.get_save_data() for history in self.history_data]
        write_json(f"{DATA_PATH}/playlists.json", playlist_data)
        write_json(f"{DATA_PATH}/history.json", history_data)
        minip = self.music_controls.minip
        minip.save_state()
        write_json(
            f"{DATA_PATH}/settings.json",
            {
                "volume": self.state.volume,
                "loops": self.state.loops,
                "shuffle": self.state.shuffle,
                "fps": self.state.user_framerate,
                "custom_title": self.custom_title,
                "win_pos": self.window.position,
                "win_size": self.window.size,
                "before_maximize_data": self.custom_behavior.before_maximized_data,
                "maximized": self.custom_behavior.maximized,
                "discord_presence": self.discord_presence.active,
                "strip_youtube_id": self.strip_youtube_id,
                "taskbar_height": self.custom_behavior.display_size[1]
                - self.custom_behavior.usable_display_area.h,
                "videoclip_threaded": self.state.videoclip_threaded,
                "videoclip_on": self.state.videoclip_on,
                "universal_font": self.universal_font,
                "yt_search": self.yt_search.search_entryline.text,
                "yt_fetch_amount": self.yt_search.fetch_amount,
                "yt_search_method": self.yt_search.search_method,
                "yt_show_details": self.playlist_viewer.yt_show_details,
                "last_explorer_path": str(self.explorer.last_path),
                "miniplayer": [minip.last_size, minip.last_pos, minip.last_borderless],
                "explorer_history_idx": self.explorer.history_idx,
                "show_favorites": self.list_viewer.show_favorites,
                "explorer_history": [str(hpath) for hpath in self.explorer.history],
                "explorer_favorites": [str(path) for path in self.explorer.favorites],
                "keybinds": self.keybinds.get_save_data(),
            },
        )
        write_json(f"{DATA_PATH}/gpu.json", self.save_use_renderer)
        for playlist in self.playlists:
            if playlist.cover is not None:
                if not os.path.exists(f"{DATA_PATH}/covers/{playlist.name}.png"):
                    pygame.image.save(
                        playlist.cover, f"{DATA_PATH}/covers/{playlist.name}.png"
                    )
        if len(self.yt_search.video_results) > 0:
            write_json(
                f"{DATA_PATH}/search_results.json",
                [video.save() for video in self.yt_search.video_results],
            )
        if os.path.exists(f"{DATA_PATH}/yt_temp"):
            thumbs = set([video.thumbnail for video in self.yt_search.video_results])
            channels = set([video.channel_id for video in self.yt_search.video_results])
            for file in os.listdir(f"{DATA_PATH}/yt_temp"):
                name = file.removesuffix(".png").removesuffix(".jpg")
                if name.startswith("channel_"):
                    if name.removeprefix("channel_") not in channels:
                        os.remove(f"{DATA_PATH}/yt_temp/{file}")
                else:
                    if name not in thumbs:
                        os.remove(f"{DATA_PATH}/yt_temp/{file}")
        self.notify(NOTIF.DATA)

    def update(self):
        self.window.title = f"MILIMP (FPS: {self.clock.get_fps():.0f})"
        if pygame.time.get_ticks() - self.last_save >= SAVE_COOLDOWN:
            self.save()

        prev = self.target_framerate
        self.target_framerate = self.state.user_framerate
        if not self.focused and (
            not self.music_controls.minip.focused
            or self.music_controls.minip.window is None
        ):
            self.target_framerate = 10
        elif self.state.need_low_fps:
            self.target_framerate = 30
            if prev == 60:
                self.notify(NOTIF.FPS)

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

        if self.custom_title and not self.super_fullscreen:
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

        if len(mili.get_font_cache()) > 30:
            mili.clear_font_cache()

        self.split_w = self.window.size[0]
        self.split_size = self.window.size
        self.split_screen = False
        if (
            self.window.size[0] >= self.window.size[1] * 1.4
            and self.state.music is not None
            and self.modal_state != "fullscreen"
        ):
            self.split_screen = True
            self.split_w = self.window.size[0] / SPLIT_SCREEN
            self.split_size = (self.split_w, self.window.size[1])

        if self.state.async_videoclip is not None:
            self.state.async_videoclip.active = False

        if (
            self.bg_effect_image is not None
            and self.bg_effect_image.size != self.window.size
        ):
            self.make_bg_image()

    def ui(self):
        self.mili.rect({"color": (BG_CV,) * 3, "border_radius": 0})
        if self.custom_title and not self.super_fullscreen:
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
                elif self.view_state == "explorer":
                    self.explorer.ui()
            else:
                if self.view_state == "list":
                    self.list_viewer.ui_check()
                elif self.view_state == "playlist":
                    self.playlist_viewer.ui_check()
                elif self.view_state == "search":
                    self.yt_search.ui_check()
                elif self.view_state == "explorer":
                    self.explorer.ui_check()
                self.mili.element(None, {"filly": True, "blocking": None})

            if self.modal_state == "settings":
                self.settings.ui()
            elif self.modal_state == "fullscreen":
                self.music_fullscreen.ui()
            elif self.modal_state == "history":
                self.history.ui()
            elif self.modal_state == "keybinds":
                self.edit_keybinds.ui()
            elif self.modal_state == "state_info":
                self.state_info.ui()
            elif self.modal_state == "notifs":
                self.notifications_ui.ui()
            elif self.modal_state == "backup_save":
                self.backup_save.ui()
            elif self.modal_state == "health_check":
                self.health_check.ui()
            elif self.modal_state == "queue":
                self.queue.ui()

            if not self.split_screen:
                self.mili.id_checkpoint(ID_POST_OFFSET)
                self.music_controls.ui()

            self.mili.id_checkpoint(ID_POST_OFFSET + 10000)
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
                self.mili.id_checkpoint(ID_POST_OFFSET + 20000)
                self.music_controls.ui_split_screen()
                self.mili.id_checkpoint(ID_POST_OFFSET + 30000)
                self.music_controls.ui()
            self.mili.end()

        if (
            self.view_state == "list"
            and self.custom_title
            and pygame.key.get_pressed()[pygame.K_BACKSLASH]
        ):
            self.mili.text_element(
                f"developer version {DEV_VERSION}",
                {"size": self.mult_fs(13), "color": (100,) * 3},
                None,
                mili.FLOATING | {"blocking": None},
            )

        if self.modal_state != "none" and self.menu_data != "controls":
            self.close_menu()
        self.mili.id_checkpoint(ID_POST_OFFSET + 50000)
        if self.menu_open:
            self.ui_menu()
        self.mili.id_checkpoint(ID_POST_OFFSET + 60000)

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

    def ui_tooltip(self):
        pad = self.mult(2)
        txtstyle = {
            "size": self.mult_fs(13),
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
                    tooltip="Restore window"
                    if self.custom_behavior.maximized
                    else "Maximize window",
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
        elif self.view_state == "explorer":
            self.explorer.ui_top_buttons()

    def ui_bg_effect(self):
        if not self.state.bg_effect:
            return
        self.mili.image(self.bg_effect_image, {"ready": not USE_RENDERER})
        self.mili.image(
            self.bg_black_image, {"cache": self.bg_cache, "ready": not USE_RENDERER}
        )

    def ui_menu(self):
        with self.mili.begin(
            (self.menu_pos, (0, 0)),
            {
                "resizex": True,
                "resizey": True,
                "ignore_grid": True,
                "parent_id": 0,
                "axis": "x",
                "layout": "grid",
                "z": 9999,
                "padx": self.mult(7),
                "pady": self.mult(7),
                "blocking": None,
                "size_clamp": {"max": (self.window.size[0] - self.menu_pos[0], None)},
            },
        ) as menu:
            self.mili.rect({"color": (MENU_CV[0],) * 3, "border_radius": self.mult(27)})
            self.mili.rect(
                {"color": (MENU_CV[1],) * 3, "border_radius": self.mult(27), "outline": 1}
            )
            for bdata in self.menu_buttons:
                bdata: MenuButton
                self.prefabs.ui_image_btn(
                    bdata.icon,
                    bdata.action,
                    bdata.animation,
                    40,
                    "50",
                    bdata.tooltip,
                    3,
                    RED_COLS if bdata.red else None,
                )
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
                btndata.animation.goto_a()
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

    def action_maximize(self):
        self.custom_behavior.toggle_maximize()
        self.make_bg_image()

    def action_minimize(self):
        self.custom_behavior.minimize()

    def can_interact(self):
        return (
            self.can_abs_interact()
            and self.custom_borders.can_interact()
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
        elif self.modal_state == "state_info":
            if self.state_info.event(event):
                return
        elif self.modal_state == "notifs":
            if self.notifications_ui.event(event):
                return
        elif self.modal_state == "backup_save":
            if self.backup_save.event(event):
                return
        elif self.modal_state == "health_check":
            if self.health_check.event(event):
                return
        elif self.modal_state == "queue":
            if self.queue.event(event):
                return
        if self.view_state == "list":
            self.list_viewer.event(event)
        elif self.view_state == "playlist":
            self.playlist_viewer.event(event)
        elif self.view_state == "search":
            self.yt_search.event(event)
        elif self.view_state == "explorer":
            self.explorer.event(event)

    def shortcuts_event(self, event):
        if self.listening_key:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.custom_borders.active = True
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
                elif Keybinds.check("open_queue", event):
                    self.open_settings()
                    self.settings.action_queue()
                elif Keybinds.check("minimize_window", event):
                    self.action_minimize()
                elif Keybinds.check("maximize_window", event):
                    self.action_maximize()

    def quit_abort(self):
        if self.yt_search.embed is not None:
            self.yt_search.embed.close()
        if self.state.async_videoclip is not None:
            self.state.async_videoclip.alive = False
            if self.state.videoclip_threaded:
                self.state.async_videoclip.thread.join()
        self.state.async_videoclip = None
        if os.path.exists(RUNNING_INSTANCE_SENTINEL):
            os.remove(RUNNING_INSTANCE_SENTINEL)
        print("Application quit without saving")
        pygame.quit()
        raise SystemExit

    def quit(self):
        if self.custom_behavior.fullscreen:
            self.custom_behavior.fullscreen_off()
        if self.yt_search.embed is not None:
            self.yt_search.embed.close()
        if self.state.async_videoclip is not None:
            self.state.async_videoclip.alive = False
            if self.state.videoclip_threaded:
                self.state.async_videoclip.thread.join()
        if self.state.async_audioplayer is not None:
            self.state.async_audioplayer.alive = False
            self.state.async_audioplayer.thread.join()
        yt_syncer = self.playlist_viewer.yt_syncer
        if yt_syncer.alive and yt_syncer.thread is not None:
            yt_syncer.alive = False
            yt_syncer.force_quit = True
            yt_syncer.thread.join()
            yt_syncer.playlist = None
        self.state.async_videoclip = None
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
        if os.path.exists(RUNNING_INSTANCE_SENTINEL):
            os.remove(RUNNING_INSTANCE_SENTINEL)
        print("Application quit")
        pygame.quit()
        raise SystemExit

    def run(self):
        while self.running:
            self.mili.start(self.start_style, window_position=self.window.position)
            for event in pygame.event.get():
                if event.type == pygame.WINDOWCLOSE and event.window == self.window:
                    self.quit()
                    return
                else:
                    self.event(event)

            if self.mili.canva.backend == "surface":
                self.mili.canva.surface = self.window.get_surface()
            if self.clear_color is not None:
                self.mili.canva._clear(self.clear_color, self.window)
            self.update()
            self.ui()
            try:
                self.mili.update_draw()
            except pgsdl2.error as sdlerror:
                print(f"SDL Error: {sdlerror}")
            self.post_draw()
            self.mili.canva._flip(self.window)
            self.delta_time = self.clock.tick(self.target_framerate) / 1000
