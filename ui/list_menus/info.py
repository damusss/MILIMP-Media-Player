import mili
import pygame
from ui.common import *


class InfoUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.cache = mili.ImageCache()

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 220000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.close()
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.cache}
            )

            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": "80",
                    "resizey": True,
                    "align": "center",
                    "offset": (0, -self.app.tbarh),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})
                self.mili.text_element(
                    "Technical Information",
                    {"size": self.mult(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                self.mili.text_element(
                    INFO,
                    {
                        "size": self.mult(16),
                        "color": (180,) * 3,
                        "growx": False,
                        "wraplen": mili.percentage(70, self.app.split_w),
                        "slow_grow": True,
                        "rich": True,
                        "align": "center",
                        "cache": "auto",
                    },
                    None,
                    {"fillx": True, "blocking": None},
                )

            self.ui_overlay_btn(
                self.anim_close, self.close, ICONS.close, tooltip="Close"
            )

    def close(self):
        self.app.list_viewer.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
