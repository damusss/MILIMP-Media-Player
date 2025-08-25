import os
import mili
import pygame
from ui.common import *
from ui.common.data import MusicData, Entryline


class RenameMusicUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_create = animation(-3)
        self.disk_entry = Entryline(self.app, "Enter name (no filetype)...")
        self.alias_entry = Entryline(self.app, "Enter alias...", False)
        self.cache = mili.ImageCache()
        self.music: MusicData = None
        self.rename_mode = "alias"

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 180000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.close()
            self.mili.image(
                SURF, {"fill": True, "fill_color": MENU_BG_COL, "cache": self.cache}
            )

            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": "60" if self.app.split_w > 1200 else "80",
                    "resizey": True,
                    "align": "center",
                    "offset": (0, -self.app.tbarh),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.ui_modal_content()

            self.ui_overlay_btn(
                self.anim_close, self.close, ICONS.close, tooltip="Close"
            )

    def ui_modal_content(self):
        self.mili.text_element(
            "Rename Music",
            {"size": self.mult_fs(26)},
            None,
            mili.CENTER | {"blocking": None},
        )
        with self.mili.begin(
            None,
            {"fillx": True, "resizey": True, "axis": "x", "anchor": "max_spacing"}
            | mili.PADLESS,
        ) as row:
            with self.mili.begin(
                (0, 0, row.data.rect.w / 2.01, 0),
                {"resizey": True, "padx": 0, "pady": 0},
            ) as left_cont:
                self.ui_section_btn(
                    left_cont,
                    "alias",
                    "Rename Alias",
                    "Rename the alias that the track will use while keeping the same name on disk",
                )
            with self.mili.begin(
                (0, 0, row.data.rect.w / 2.01, 0),
                {"resizey": True, "padx": 0, "pady": 0},
            ) as left_cont:
                self.ui_section_btn(
                    left_cont, "disk", "Rename Locally", "Rename the track on disk"
                )

        if self.rename_mode == "disk":
            self.ui_disk()
        else:
            self.ui_alias()

    def ui_disk(self):
        self.disk_entry.ui(
            pygame.Rect(
                0,
                0,
                0,
                self.mult(35),
            ),
            {"align": "center", "fillx": "90"},
        )
        self.ui_image_btn(
            ICONS.confirm,
            self.action_confirm,
            self.anim_create,
            tooltip="Confirm and rename the track",
        )
        self.mili.text_element(
            "Renaming will modify the file on disk. Do not include the file type.",
            {
                "size": self.mult_fs(16),
                "color": (150,) * 3,
                "growx": False,
                "wraplen": mili.percentage(70, self.app.split_w),
                "slow_grow": True,
            },
            None,
            {"fillx": True, "blocking": None},
        )

    def ui_alias(self):
        self.alias_entry.ui(
            pygame.Rect(
                0,
                0,
                0,
                self.mult(35),
            ),
            {"align": "center", "fillx": "90"},
        )
        self.ui_image_btn(
            ICONS.confirm,
            self.action_confirm,
            self.anim_create,
            tooltip="Rename the track alias",
        )
        self.mili.text_element(
            "Does not modify the name on disk. Leave empty to remove the current alias.",
            {
                "size": self.mult_fs(16),
                "color": (150,) * 3,
                "growx": False,
                "wraplen": mili.percentage(70, self.app.split_w),
                "slow_grow": True,
            },
            None,
            {"fillx": True, "blocking": None},
        )

    def ui_section_btn(self, cont, ctype, txt, tooltip):
        color = (255,) * 3 if self.rename_mode == ctype else (120,) * 3
        if self.mili.element(None, mili.CENTER | {"blocking": False}):
            if cont.hovered and self.app.can_interact():
                self.mili.rect({"color": (MODALB_CV[0],) * 3, "border_radius": "10"})
            self.mili.text(
                txt,
                {"size": self.mult_fs(21), "color": color},
            )
        self.mili.line_element(
            [("-48", 0), ("48", 0)],
            {"color": color},
            (0, 0, 0, self.mult(20)),
            {"fillx": True, "blocking": False},
        )
        if self.app.can_interact():
            if cont.left_just_released:
                self.rename_mode = ctype
            if cont.hovered or cont.unhover_pressed:
                self.app.cursor_hover = True
            if cont.hovered:
                self.app.tick_tooltip(tooltip)

    def action_confirm(self):
        if self.rename_mode == "disk":
            self.action_confirm_disk()
        else:
            self.action_confirm_alias()

    def action_confirm_alias(self):
        new_alias = self.alias_entry.text.strip()
        if new_alias == "":
            if self.music.realpath in self.music.playlist.aliases:
                self.music.playlist.aliases.pop(self.music.realpath)
        else:
            self.music.playlist.aliases[self.music.realpath] = new_alias
        self.close()

    def action_confirm_disk(self):
        new_name = self.disk_entry.text.strip()
        if not new_name or self.disk_entry.text[-1] == ".":
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
        if self.music == self.state.music:
            self.state.end_music()
        self.app.remove_from_history(self.music)
        cur_alias = self.music.alias

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

        if cur_alias is not None:
            self.music.playlist.aliases.pop(self.music.realpath)

        mp3path = f"{DATA_PATH}/mp3_converted/{self.app.playlist_viewer.playlist.name}_{self.music.realstem}.mp3"
        newmp3path = f"{DATA_PATH}/mp3_converted/{self.app.playlist_viewer.playlist.name}_{new_stem}.mp3"
        if os.path.exists(mp3path):
            if not os.path.exists(newmp3path):
                os.rename(mp3path, newmp3path)

        coverpath = f"{DATA_PATH}/music_covers/{self.app.playlist_viewer.playlist.name}_{self.music.realstem}.png"
        if os.path.exists(coverpath):
            newcoverpath = f"{DATA_PATH}/music_covers/{self.app.playlist_viewer.playlist.name}_{new_stem}.png"
            if not os.path.exists(newcoverpath):
                os.rename(coverpath, newcoverpath)

        idx = self.app.playlist_viewer.playlist.musiclist.index(self.music)
        self.app.playlist_viewer.playlist.remove(self.music.audiopath)
        self.app.playlist_viewer.playlist.load_music(
            [new_path, "converted"] if self.music.converted else new_path,
            ICONS.loading,
            idx,
        )

        if cur_alias is not None:
            self.app.playlist_viewer.playlist.aliases[new_path] = cur_alias

    def close(self):
        self.disk_entry.text = ""
        self.disk_entry.cursor = 0
        self.app.playlist_viewer.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
        if Keybinds.check("confirm", event, ignore_input=True):
            self.action_confirm()
        if self.rename_mode == "disk":
            self.disk_entry.event(event)
        else:
            self.alias_entry.event(event)
