import mili
import pygame
import threading
import shutil
from ui.common import *


class StateInfoUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.cache = mili.ImageCache()
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, {"short_size": 7, "axis": "y"})
        self.sbar_size = self.scrollbar.style["short_size"]
        self.ytdlp_dep = shutil.which("yt-dlp")
        self.ffmpeg_dep = shutil.which("ffmpeg")
        self.ffplay_dep = shutil.which("ffplay")
        if self.ytdlp_dep is None:
            self.ytdlp_dep = "Not Found"
        if self.ffmpeg_dep is None:
            self.ffmpeg_dep = "Not Found"
        if self.ffplay_dep is None:
            self.ffplay_dep = "Not Found"

    def ui(self):
        handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

        self.mili.id_checkpoint(ID_OFFSET + 230000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.back()
            self.mili.image(
                SURF, {"fill": True, "fill_color": MENU_BG_COL, "cache": self.cache}
            )
            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": "60" if self.app.split_w > 1500 else "90",
                    "filly": "80"
                    if self.state.music is not None or self.app.split_w < 800
                    else "65",
                    "align": "center",
                    "spacing": self.mult(13),
                    "offset": (
                        0,
                        (-self.app.music_controls.cont_height / 2)
                        * (not self.app.split_screen)
                        - self.app.tbarh / 2,
                    ),
                    "blocking": None,
                }
                | mili.CENTER,
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.mili.text_element(
                    "State Information",
                    {"size": self.mult_fs(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                with self.mili.begin(
                    None,
                    {
                        "fillx": "100",
                        "filly": True,
                        "pad": 0,
                        "spacing": 0,
                    }
                    | mili.CENTER,
                ) as cont:
                    self.scroll.update(cont)
                    self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                    self.scrollbar.update(cont)
                    self.ui_scrollbar()
                    app = self.app
                    state = self.state
                    self.ui_column("Volume", state.volume)
                    self.ui_column(
                        "Music Name",
                        state.music.name_or_alias(self.app)
                        if state.music is not None
                        else "Not playing",
                        active=state.music is not None,
                    )
                    self.ui_column("Shuffle Playlist", state.shuffle, boolean=True)
                    self.ui_column("Playlist Loops", state.loops, boolean=True)
                    if state.music is not None:
                        self.ui_column("Music Paused", state.music_paused, boolean=True)
                        self.ui_column("Music Loops", state.music_loops, boolean=True)
                        mpos = state.get_music_pos()
                        duration = ""
                        if isinstance(state.music.duration, float):
                            duration = f" ({format_music_time(mpos, state.music.duration)} | {(mpos / state.music.duration) * 100:.2f}%)"
                        self.ui_column("Music Timestamp", f"{mpos:.2f}{duration}")
                        self.ui_column(
                            "Music Is Video", state.music.isvideo, boolean=True
                        )
                        if state.music.isvideo:
                            frame = state.async_videoclip
                            if frame.stream is not None:
                                self.ui_column(
                                    "Video Resolution",
                                    f"{int(frame.stream.coded_width)}x{int(frame.stream.coded_height)} px",
                                )
                                if isinstance(state.music.duration, float):
                                    fps = frame.stream.average_rate
                                    if fps is not None:
                                        frames = int(state.music.duration * fps)
                                        frameno = int(
                                            frames * (mpos / state.music.duration)
                                        )
                                        self.ui_column(
                                            "Video Frame", f"{frameno}/{frames}"
                                        )
                                fps = frame.stream.average_rate
                                if fps is None:
                                    fps = "?"
                                else:
                                    fps = f"{fps:.0f}"
                                self.ui_column(
                                    "Video Thread Framerate",
                                    (
                                        "Music paused"
                                        if state.music_paused
                                        else f"{frame.current_fps:.2f}/{fps} FPS"
                                    )
                                    if state.videoclip_threaded
                                    else "Not multithreaded",
                                    state.videoclip_threaded and not state.music_paused,
                                )
                    self.ui_column("User Framerate", f"{state.user_framerate} FPS")
                    self.ui_column(
                        "Current Framerate",
                        f"{app.clock.get_fps():.2f}/{app.target_framerate} FPS",
                    )
                    self.ui_column("Videoclip On", state.videoclip_on, boolean=True)
                    self.ui_column(
                        "Videoclip Threaded", state.videoclip_threaded, boolean=True
                    )
                    self.ui_column("Window Focused", app.focused, boolean=True)
                    self.ui_column(
                        "Using Universal Font", app.universal_font, boolean=True
                    )
                    self.ui_column(
                        "Discord Presence Active",
                        app.discord_presence.active,
                        boolean=True,
                    )
                    self.ui_column(
                        "UI Hardware Accelerated", USE_RENDERER, boolean=True
                    )
                    self.ui_column(
                        "Last Data Save",
                        f"{(pygame.time.get_ticks() - app.last_save) / 1000:.0f} Seconds Ago",
                    )
                    self.ui_column(
                        "Foreign Dependencies",
                        f"yt-dlp: {self.ytdlp_dep}, ffmpeg: {self.ffmpeg_dep}, ffplay: {self.ffplay_dep}",
                    )
                    self.ui_column("Data Path", DATA_PATH)
                    self.ui_column("Thread Count", f"{threading.active_count()}")

                self.mili.element((0, 0, 0, self.mult(10)))

            self.ui_overlay_btn(self.anim_close, self.back, ICONS.close, tooltip="Back")

    def ui_column(self, title, value, active=True, boolean=False):
        with self.mili.begin(
            None,
            {
                "fillx": "94",
                "resizey": True,
                "axis": "x",
                "pad": 0,
                "spacing": 0,
                "offset": self.scroll.get_offset(),
            },
        ) as parent:
            self.mili.element(
                None,
                {"fillx": "42", "filly": True},
            )
            self.mili.rect(
                {
                    "color": (MODALB_CV[1],) * 3,
                    "border_radius": 0,
                    "outline": 1,
                    "draw_above": True,
                }
            )
            self.mili.text(
                title,
                {
                    "size": self.mult_fs(18),
                    "growx": False,
                    "growy": False,
                    "align": "left",
                    "font_align": pygame.FONT_LEFT,
                    "color": (150,) * 3,
                },
            )
            self.mili.element(
                (0, 0, mili.percentage(100 - 25, parent.data.rect.w), 0),
                {"fillx": str(100 - 25)},
            )
            self.mili.rect(
                {
                    "color": (MODALB_CV[1],) * 3,
                    "border_radius": 0,
                    "outline": 1,
                    "draw_above": True,
                }
            )
            self.mili.text(
                {True: "Yes", False: "No"}[value] if boolean else value,
                {
                    "size": self.mult_fs(17),
                    "growx": False,
                    "slow_grow": True,
                    "wraplen": "100",
                    "color": (
                        "white" if not boolean else ("#78c1a3" if value else "#f38989")
                    )
                    if active
                    else (120,) * 3,
                    "align": "left",
                    "font_align": pygame.FONT_LEFT,
                },
            )

    def back(self):
        self.app.modal_state = "settings"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.MOUSEWHEEL:
            handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return True
        return False
