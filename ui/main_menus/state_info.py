import mili
import pygame
from ui.common import *


class StateInfoUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.cache = mili.ImageCache()

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 230000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.back()
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.cache}
            )

            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": "60" if self.app.split_w > 1500 else "80",
                    "resizey": True,
                    "align": "center",
                    "spacing": self.mult(13),
                    "offset": (0, -self.app.tbarh),
                    "blocking": None,
                }
                | mili.CENTER,
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.mili.text_element(
                    "App State Information",
                    {"size": self.mult(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                with self.mili.begin(
                    None,
                    {
                        "fillx": "80" if self.app.split_w > 1500 else "95",
                        "resizey": True,
                        "pad": 0,
                        "spacing": 0,
                    }
                    | mili.CENTER,
                ):
                    app = self.app
                    self.ui_column("Volume", app.volume)
                    self.ui_column("Music Playing", app.music is not None, boolean=True)
                    self.ui_column("Shuffle Playlist", app.shuffle, boolean=True)
                    self.ui_column("Playlist Loops", app.loops, boolean=True)
                    if app.music is not None:
                        self.ui_column("Music Name", app.music.realname)
                        self.ui_column("Music Paused", app.music_paused, boolean=True)
                        self.ui_column("Music Loops", app.music_loops, boolean=True)
                        self.ui_column("Music Timestamp", f"{app.get_music_pos():.2f}")
                        self.ui_column(
                            "Music Is Video", app.music.isvideo, boolean=True
                        )
                        if app.music.isvideo:
                            frame = self.app.music_controls.async_videoclip
                            if frame.original_size is not None:
                                self.ui_column(
                                    "Video Source Resolution",
                                    f"{int(frame.original_size.x)}x{int(frame.original_size.y)} px",
                                )
                            self.ui_column(
                                "Video Playing Resolution",
                                f"{int(frame.videoclip.size[0])}x{int(frame.videoclip.size[1])} px,",
                            )
                            self.ui_column(
                                "Video Thread Framerate",
                                f"{frame.current_fps:.2f}"
                                if app.videoclip_threaded
                                else "Not multithreaded",
                                app.videoclip_threaded,
                            )
                            self.ui_column(
                                "Video Source Framerate",
                                f"{frame.videoclip.fps:.0f}",
                            )
                    self.ui_column("User Framerate", app.user_framerate)
                    self.ui_column("Target Framerate", app.target_framerate)
                    self.ui_column("Current Framerate", f"{app.clock.get_fps():.2f}")
                    self.ui_column("Videoclip On", app.videoclip_on, boolean=True)
                    self.ui_column(
                        "Videoclip Threaded", app.videoclip_threaded, boolean=True
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
                        "Last Data Save",
                        f"{(pygame.time.get_ticks() - app.last_save) / 1000:.0f} Seconds Ago",
                    )

                self.mili.element((0, 0, 0, self.mult(10)))

            self.ui_overlay_btn(self.anim_close, self.back, ICONS.close, tooltip="Back")

    def ui_column(self, title, value, active=True, boolean=False):
        with self.mili.begin(
            None, {"fillx": True, "resizey": True, "axis": "x", "pad": 0, "spacing": 0}
        ) as parent:
            self.mili.element(
                None,
                {"fillx": "30", "filly": True},
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
                    "size": self.mult(18),
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
                    "size": self.mult(17),
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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return True
        return False
