import os
import mili
import pygame
from ui.common import *
from ui.data import PlaylistGroup
from ui.entryline import UIEntryline


class RenameGroupUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_create = animation(-3)
        self.entryline = UIEntryline("Enter name...", False)
        self.cache = mili.ImageCache()
        self.group: PlaylistGroup = None

    def ui(self):
        self.mili.id_checkpoint(3000 + 250)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": None} | mili.CENTER,
        ):
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

                self.ui_modal_content()

            self.ui_overlay_btn(
                self.anim_close, self.close, self.app.close_image, tooltip="Close"
            )

    def ui_modal_content(self):
        self.mili.text_element(
            "Rename Group",
            {"size": self.mult(26)},
            None,
            mili.CENTER | {"blocking": None},
        )
        self.entryline.update(self.app)
        self.mili.element(None, {"blocking": None})
        self.entryline.ui(
            self.mili,
            pygame.Rect(
                0,
                0,
                mili.percentage(80, self.app.split_w / 1.35),
                self.mult(35),
            ),
            {"align": "center"},
            self.mult,
        )
        self.ui_image_btn(
            self.app.confirm_image,
            self.action_confirm,
            self.anim_create,
            tooltip="Confirm and rename the group",
        )

    def action_confirm(self):
        new_name = self.entryline.text.strip()
        if not new_name:
            pygame.display.message_box(
                "Invalid name",
                "The new group name cannot be empty.",
                "error",
                None,
                ("Understood",),
            )
            return
        if new_name == self.group.name:
            self.close()
            return
        self.group.name = new_name
        self.close()

    def close(self):
        self.entryline.text = ""
        self.entryline.cursor = 0
        self.app.playlist_viewer.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
        if Keybinds.check("confirm", event, ignore_input=True):
            self.action_confirm()
        self.entryline.event(event)
