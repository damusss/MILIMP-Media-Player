import mili
import pygame
from ui.common import *
from ui.common.data import Notification


class NotificationsUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_show = animation(-3)
        self.cache = mili.ImageCache()
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, {"short_size": 7, "axis": "y"})
        self.sbar_size = self.scrollbar.style["short_size"]
        self.show_extra = False

    def ui(self):
        handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

        self.mili.id_checkpoint(ID_OFFSET + 260000)
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
                    "fillx": "50" if self.app.split_w > 1200 else "80",
                    "filly": "70",
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
                with self.mili.begin(
                    None, mili.RESIZE | mili.X | mili.CENTER | {"pady": 0}
                ):
                    self.mili.text_element(
                        "Notification Log",
                        {"size": self.mult_fs(26)},
                        None,
                        mili.CENTER | {"blocking": None},
                    )
                    self.ui_image_btn(
                        ICONS.shown if self.show_extra else ICONS.hidden,
                        self.action_show,
                        self.anim_show,
                        size=30,
                        tooltip="Show all errors"
                        if not self.show_extra
                        else "Hide some errors",
                    )

                with self.mili.begin(
                    None,
                    mili.CENTER
                    | {
                        "fillx": "100",
                        "filly": True,
                        "pad": 0,
                        "anchor": "first",
                    },
                ) as cont:
                    self.scroll.update(cont)
                    self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                    self.scrollbar.update(cont)
                    self.ui_scrollbar()

                    if len(self.app.notifications) <= 0:
                        self.mili.text_element(
                            "No notifications yet",
                            {
                                "size": self.mult_fs(16),
                                "color": (180,) * 3,
                            },
                        )

                    for notif in reversed(self.app.notifications):
                        self.ui_notif(notif)

                self.mili.element((0, 0, 0, self.mult(10)))

            self.ui_overlay_btn(self.anim_close, self.back, ICONS.close, tooltip="Back")

    def ui_notif(self, notif: Notification):
        if notif.hidden and not self.show_extra:
            return
        with self.mili.begin(
            None,
            mili.CENTER
            | {
                "fillx": "80",
                "resizey": True,
                "align": "first",
                "anchor": "first",
                "default_align": "center",
                "offset": self.scroll.get_offset(),
                "axis": "x",
            },
        ) as cont:
            imgsize = self.mult(22)
            self.mili.image_element(
                getattr(ICONS, notif.kind), None, (0, 0, imgsize, imgsize)
            )
            time = f'<color fg="white">[{notif.time.strftime("%H:%M:%S")}]</color> '
            self.mili.text_element(
                time + notif.message,
                {
                    "size": self.mult_fs(16),
                    "color": "red" if notif.error else (180,) * 3,
                    "rich": True,
                    "wraplen": cont.data.rect.w - imgsize,
                    "align": "left",
                    "font_align": "left",
                },
            )
        self.mili.hline_element(
            {"size": 1, "color": (80,) * 3}, (0, 0, 0, 1), {"fillx": "92", "offset": self.scroll.get_offset()}
        )

    def action_show(self):
        self.show_extra = not self.show_extra

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
