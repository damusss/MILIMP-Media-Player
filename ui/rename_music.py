import os
import mili
import pygame
from ui.common import *
from ui.data import MusicData
from ui.entryline import UIEntryline


class RenameMusicUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_create = animation(-3)
        self.entryline = UIEntryline("Enter name (no filetype)...")
        self.cache = mili.ImageCache()
        self.music: MusicData = None

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
            "Rename Music",
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
            tooltip="Confirm and rename the track",
        )
        self.mili.text_element(
            "Renaming will modify the file on disk. Do not include the file type.",
            {
                "size": self.mult(16),
                "color": (150,) * 3,
                "growx": False,
                "wraplen": mili.percentage(70, self.app.split_w),
                "slow_grow": True,
            },
            None,
            {"fillx": True, "blocking": None},
        )

    def action_confirm(self):
        new_name = self.entryline.text.strip()
        if not new_name or self.entryline.text[-1] == ".":
            pygame.display.message_box(
                "Invalid name",
                "Enter a valid name to rename the music. A name must be a valid file name (cannot end with '.', must be non empty).",
                "error",
                None,
                ("Understood",),
            )
            return
        if new_name == self.music.realstem:
            self.close()
            return
        new_path = self.music.realpath.parent / f"{new_name}{self.music.realextension}"
        if os.path.exists(new_path):
            pygame.display.message_box(
                "File already exists",
                f"A file with the same name already exists in '{self.music.realpath.parent}'.",
                "error",
                None,
                ("Understood",),
            )
            return
        self.final_rename(new_path, new_name)
        self.close()

    def final_rename(self, new_path, new_stem):
        if self.music == self.app.music:
            self.app.end_music()

        try:
            os.rename(self.music.realpath, new_path)
        except Exception as e:
            pygame.display.message_box(
                "Operation failed",
                f"Failed to rename file due to OS error: '{e}'.",
                "error",
                None,
                ("Understood",),
            )
            self.close()
            return

        mp3path = f"data/mp3_converted/{self.app.playlist_viewer.playlist.name}_{self.music.realstem}.mp3"
        newmp3path = f"data/mp3_converted/{self.app.playlist_viewer.playlist.name}_{new_stem}.mp3"
        if os.path.exists(mp3path):
            if not os.path.exists(newmp3path):
                os.rename(mp3path, newmp3path)

        coverpath = f"data/music_covers/{self.app.playlist_viewer.playlist.name}_{self.music.realstem}.png"
        if os.path.exists(coverpath):
            newcoverpath = f"data/music_covers/{self.app.playlist_viewer.playlist.name}_{new_stem}.png"
            if not os.path.exists(newcoverpath):
                os.rename(coverpath, newcoverpath)

        idx = self.app.playlist_viewer.playlist.musiclist.index(self.music)
        self.app.playlist_viewer.playlist.remove(self.music.audiopath)
        self.app.playlist_viewer.playlist.load_music(
            [new_path, "converted"] if self.music.converted else new_path,
            self.app.loading_image,
            idx,
        )

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
