import mili
import pygame
from ui.common import *


class InfoUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.cache = mili.ImageCache()
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, {"short_size": 7, "axis": "y"})
        self.sbar_size = self.scrollbar.style["short_size"]

    def ui(self):
        handle_arrow_scroll(self.app, self.scroll, self.scrollbar)
        self.mili.id_checkpoint(ID_OFFSET + 220000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.close()
            self.mili.image(
                SURF, {"fill": True, "fill_color": MENU_BG_COL, "cache": self.cache}
            )
            perc = 95 if self.app.split_w < 1200 else 60
            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": str(perc),
                    "filly": "70",
                    "align": "center",
                    "offset": (
                        0,
                        (-self.app.music_controls.cont_height / 2)
                        * (not self.app.split_screen)
                        - self.app.tbarh / 2,
                    ),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})
                self.mili.text_element(
                    "Technical Information",
                    {"size": self.mult_fs(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                with self.mili.begin(
                    None, {"fillx": True, "filly": True} | mili.SPACELESS | mili.PADLESS
                ) as cont:
                    self.scroll.update(cont)
                    self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                    self.scrollbar.update(cont)
                    self.ui_scrollbar()
                    self.mili.text_element(
                        INFO,
                        {
                            "size": self.mult_fs(16),
                            "color": (180,) * 3,
                            "growx": False,
                            "wraplen": mili.percentage(perc - 10, self.app.split_w),
                            "slow_grow": True,
                            "rich": True,
                            "align": "center",
                            "cache": "auto",
                        },
                        None,
                        {
                            "fillx": True,
                            "blocking": None,
                            "offset": self.scroll.get_offset(),
                        },
                    )

            self.ui_overlay_btn(
                self.anim_close, self.close, ICONS.close, tooltip="Close"
            )

    def close(self):
        self.app.list_viewer.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return
        if event.type == pygame.MOUSEWHEEL:
            handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
