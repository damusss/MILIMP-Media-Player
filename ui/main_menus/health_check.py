import mili
import pygame
import threading
from ui.common import *
from ui.common.data import MusicData, NotCached, create_backup_async
from functools import partial
import tkinter.filedialog as filedialog


class HealthCheckUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_delete = animation(-3)
        self.cache = mili.ImageCache()
        self.unused = []

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
            perc = 50 if self.app.split_w > 1500 else 90
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
                    {"size": self.mult(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                self.mili.text_element(
                    "Unused files are files in the data folders that the playlists are not using (for example outdated covers or converted MP3s)",
                    {
                        "color": (150,) * 3,
                        "size": self.mult(15),
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
                            "size": self.mult(22),
                            "slow_grow": True,
                            "growx": mili.percentage(perc - 5, self.app.split_w),
                            "wraplen": "100",
                        },
                        (0, 0, mili.percentage(perc - 5, self.app.split_w), 0),
                        {"align": "center", "fillx": True, "blocking": None},
                    )
                else:
                    self.ui_image_btn(
                        ICONS.delete,
                        self.action_delete,
                        self.anim_delete,
                        tooltip="Delete unused files",
                    )

            self.ui_overlay_btn(
                self.anim_close, self.back, ICONS.close, tooltip="Close"
            )

    def refresh(self):
        self.unused = []

    def action_delete(self): ...

    def back(self):
        self.unused = []
        self.app.modal_state = "settings"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return True
        return False
