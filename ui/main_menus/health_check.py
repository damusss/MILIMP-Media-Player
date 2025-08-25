import mili
import pygame
import threading
import pathlib
from ui.common import *
from ui.common.data import MusicData, NotCached, create_backup_async
from functools import partial
import tkinter.filedialog as filedialog


class HealthCheckUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_delete = animation(-3)
        self.cache = mili.ImageCache()
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, {"short_size": 7, "axis": "y"})
        self.sbar_size = self.scrollbar.style["short_size"]
        self.unused = []

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
            perc = 70 if self.app.split_w > 1500 else 90
            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": str(perc),
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
                    "Health Check",
                    {"size": self.mult_fs(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                self.mili.text_element(
                    "Unused files are files in the data folders that the playlists are not using (for example outdated covers or converted MP3s)",
                    {
                        "color": (150,) * 3,
                        "size": self.mult_fs(15),
                        "slow_grow": True,
                        "growx": False,
                        "wraplen": mili.percentage(perc - 5, self.app.split_w),
                    },
                    (0, 0, mili.percentage(perc - 5, self.app.split_w), 0),
                    {"align": "center", "fillx": True, "blocking": None},
                )
                if len(self.unused) == 0:
                    self.mili.text_element(
                        "No unused files found! App is healthy.",
                        {
                            "color": (255,) * 3,
                            "size": self.mult_fs(22),
                            "slow_grow": True,
                            "growx": mili.percentage(perc - 5, self.app.split_w),
                            "wraplen": "100",
                        },
                        (0, 0, mili.percentage(perc - 5, self.app.split_w), 0),
                        {"align": "center", "fillx": True, "blocking": None},
                    )
                else:
                    self.ui_unused()
                    self.ui_image_btn(
                        ICONS.delete,
                        self.action_delete,
                        self.anim_delete,
                        tooltip="Delete unused files",
                    )

            self.ui_overlay_btn(
                self.anim_close, self.back, ICONS.close, tooltip="Close"
            )

    def ui_unused(self):
        with self.mili.push_styles(rect={"border_radius": 0}):
            with self.mili.begin(
                None,
                {
                    "fillx": "97",
                    "resizey": True,
                    "size_clamp": {"max": (None, self.app.window.size[1] / 1.8)},
                    "spacing": 0,
                    "pad": 0,
                },
            ) as cont:
                self.scroll.update(cont)
                self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                self.scrollbar.update(cont)
                self.ui_scrollbar()
                for utype, path in self.unused:
                    with self.mili.begin(
                        None,
                        {
                            "fillx": "97",
                            "resizey": True,
                            "axis": "x",
                            "spacing": 0,
                            "pad": 0,
                            "offset": self.scroll.get_offset(),
                        },
                    ):
                        with self.mili.element(
                            None,
                            {
                                "fillx": "20",
                                "filly": True,
                            },
                        ):
                            self.mili.rect(mili.style.outline((MODALB_CV[1],) * 3))
                            self.mili.text(
                                utype,
                                {
                                    "size": self.mult_fs(16),
                                    "growx": False,
                                    "slow_grow": True,
                                },
                            )
                        with self.mili.element(
                            None,
                            {
                                "fillx": "80",
                            },
                        ):
                            self.mili.rect(mili.style.outline((MODALB_CV[1],) * 3))
                            self.mili.text(
                                path.absolute(),
                                {
                                    "size": self.mult_fs(16),
                                    "growx": False,
                                    "slow_grow": True,
                                    "wraplen": "100",
                                    "align": "left",
                                    "font_align": "left",
                                },
                            )
                self.mili.element((0, 0, 0, self.mult(5)))

    def refresh(self):
        self.unused = []
        cover_paths = []
        music_cover_paths = []
        mp3_paths = []
        youtube_paths = []
        for playlist in self.app.playlists:
            cover_paths.append(pathlib.Path(f"{DATA_PATH}/covers/{playlist.name}.png"))
            for music in playlist.musiclist:
                music_cover_paths.append(
                    pathlib.Path(
                        f"{DATA_PATH}/music_covers/{playlist.name}_{music.realstem}.png"
                    )
                )
                mp3_paths.append(
                    pathlib.Path(
                        f"{DATA_PATH}/mp3_converted/{playlist.name}_{music.realstem}.mp3"
                    )
                )
                if playlist.is_yt:
                    youtube_paths.append(
                        pathlib.Path(
                            f"{DATA_PATH}/yt_playlists/{playlist.name}/{music.realname}"
                        )
                    )
        if os.path.exists(f"{DATA_PATH}/covers"):
            for file in os.listdir(f"{DATA_PATH}/covers"):
                file = pathlib.Path(os.path.join(f"{DATA_PATH}/covers", file))
                if file not in cover_paths:
                    self.unused.append(["Playlist Cover", file])
        if os.path.exists(f"{DATA_PATH}/music_covers"):
            for file in os.listdir(f"{DATA_PATH}/music_covers"):
                file = pathlib.Path(os.path.join(f"{DATA_PATH}/music_covers", file))
                if file not in music_cover_paths:
                    self.unused.append(["Track Cover", file])
        if os.path.exists(f"{DATA_PATH}/mp3_converted"):
            for file in os.listdir(f"{DATA_PATH}/mp3_converted"):
                file = pathlib.Path(os.path.join(f"{DATA_PATH}/mp3_converted", file))
                if file not in mp3_paths:
                    self.unused.append(["Track MP3", file])
        if os.path.exists(f"{DATA_PATH}/yt_playlists"):
            for file in os.listdir(f"{DATA_PATH}/yt_playlists"):
                if os.path.isdir(f"{DATA_PATH}/yt_playlists/{file}"):
                    for filefile in os.listdir(f"{DATA_PATH}/yt_playlists/{file}"):
                        filefile = pathlib.Path(
                            os.path.join(f"{DATA_PATH}/yt_playlists/{file}", filefile)
                        )
                        if filefile.suffix == ".json":
                            continue
                        if filefile not in youtube_paths:
                            self.unused.append(["YouTube Video", filefile])

    def action_delete(self):
        button = pygame.display.message_box(
            "Confirm deletion",
            "This operation will permanently delete the shown unused files in the data folders from disk. Proceed?",
            "warn",
            buttons=["Understood", "Cancel"],
        )
        if button == 1:
            return
        for ftype, path in self.unused:
            os.remove(path)
        self.app.notify(NOTIF.DELETE, "Unused files deleted succesfully.")
        self.refresh()

    def back(self):
        self.unused = []
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
