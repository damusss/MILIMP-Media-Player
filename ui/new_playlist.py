import os
import mili
import pygame
import pathlib
from ui.common import *
from ui.data import Playlist
from ui.entryline import UIEntryline
import tkinter.filedialog as filedialog


class NewPlaylistUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_create = animation(-3)
        self.anim_upload = animation(-3)
        self.entryline = UIEntryline("Enter name...")
        self.cache = mili.ImageCache()
        self.create_type = "empty"
        self.selected_folder = None
        self.upload_image = load_icon("upload")

    def ui(self):
        self.mili.id_checkpoint(3000 + 200)
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
            "New Playlist",
            {"size": self.mult(26)},
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
                self.ui_section_btn(left_cont, "empty", "Empty")

            with self.mili.begin(
                (0, 0, row.data.rect.w / 2.01, 0),
                {"resizey": True, "padx": 0, "pady": 0},
            ) as right_cont:
                self.ui_section_btn(right_cont, "folder", "Load Folder")

        if self.create_type == "empty":
            self.ui_empty_playlist_modal()
        else:
            self.ui_folder_playlist_modal()

    def ui_section_btn(self, cont, ctype, txt):
        color = (255,) * 3 if self.create_type == ctype else (120,) * 3
        if self.mili.element(None, mili.CENTER | {"blocking": False}):
            if cont.hovered and self.app.can_interact():
                self.mili.rect({"color": (MODALB_CV[0],) * 3, "border_radius": "10"})
            self.mili.text(
                txt,
                {"size": self.mult(21), "color": color},
            )

        self.mili.line_element(
            [("-48", 0), ("48", 0)],
            {"color": color},
            (0, 0, 0, self.mult(20)),
            {"fillx": True, "blocking": False},
        )
        if self.app.can_interact():
            if cont.left_just_released:
                self.create_type = ctype
            if cont.hovered or cont.unhover_pressed:
                self.app.cursor_hover = True
            if cont.hovered:
                self.app.tick_tooltip(
                    "Create an empty playlist with a name"
                    if ctype == "empty"
                    else "Create a playlist with all the tracks inside a folder"
                )

    def ui_empty_playlist_modal(self):
        self.entryline.update(self.app)
        self.entryline.ui(
            self.mili,
            pygame.Rect(
                0, 0, mili.percentage(80, self.app.split_w / 1.35), self.mult(35)
            ),
            {"align": "center"},
            self.mult,
        )
        self.ui_image_btn(
            self.app.confirm_image,
            self.action_create_empty,
            self.anim_create,
            tooltip="Confirm and create the playlist",
        )

    def ui_folder_playlist_modal(self):
        self.mili.text_element(
            f"{self.selected_folder}" if self.selected_folder else "No folder selected",
            {
                "color": "white" if self.selected_folder else (150,) * 3,
                "size": self.mult(20) if self.selected_folder else self.mult(18),
                "wraplen": "100",
                "growx": False,
                "slow_grow": True,
            },
            (0, 0, mili.percentage(70, self.app.split_w), 0),
            {"align": "center", "blocking": None},
        )
        with self.mili.begin(
            None,
            {
                "resizex": True,
                "resizey": True,
                "axis": "x",
                "align": "center",
                "clip_draw": False,
                "blocking": None,
            }
            | mili.PADLESS,
        ):
            self.ui_image_btn(
                self.upload_image,
                self.action_folder_from_dialog,
                self.anim_upload,
                br="30",
                tooltip="Choose the folder for the playlist",
            )
            self.ui_image_btn(
                self.app.confirm_image,
                self.action_create_from_folder,
                self.anim_create,
                tooltip="Confirm and create the playlist",
            )
        self.mili.text_element(
            "Creating might take some time if video files are present",
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

    def action_folder_from_dialog(self):
        result = filedialog.askdirectory(mustexist=True)
        if result:
            self.selected_folder = result

    def action_create_empty(self):
        name = self.entryline.text.strip()
        if not name or name[-1] == ".":
            pygame.display.message_box(
                "Invalid name",
                "Enter a valid name to create the playlist. The name must be a valid folder name (cannot end with '.', must be non empty).",
                "error",
                None,
                ("Understood",),
            )
            return
        for p in self.app.playlists.copy():
            if p.name == name:
                pygame.display.message_box(
                    "Invalid name",
                    "A playlist with the same name already exists, choose a different name or rename the other playlist.",
                    "error",
                    None,
                    ("Understood",),
                )
                return
        self.app.playlists.append(Playlist(name, []))
        self.close()

    def action_create_from_folder(self):
        if self.selected_folder is None:
            pygame.display.message_box(
                "No folder selected",
                "Select a valid folder to create the playlist.",
                "error",
                None,
                ("Understood",),
            )
            return
        if not os.path.exists(self.selected_folder):
            pygame.display.message_box(
                "Folder not found",
                "The selected folder doesn't exist.",
                "error",
                None,
                ("Understood",),
            )
            self.selected_folder = None
            return
        path = pathlib.Path(self.selected_folder)
        name = path.name
        paths = [
            (path / file).resolve()
            for file in os.listdir(path)
            if (path / file).suffix[1:].lower() in FORMATS
        ]
        original = None
        for p in self.app.playlists.copy():
            if p.name == name:
                original = p
                btn = pygame.display.message_box(
                    "Playlist refresh",
                    "A playlist with the same name already exists. If you continue, any new track found in the selected folder will be "
                    "added to the existing playlist.",
                    "warn",
                    None,
                    ("Continue", "Cancel"),
                )
                if btn == 1:
                    self.selected_folder = None
                    return
        if original is None:
            playlist = Playlist(name, paths)
            self.app.playlists.append(playlist)
        else:
            realpaths = original.realpaths
            for newpath in paths:
                if newpath not in realpaths:
                    original.load_music(newpath, self.app.loading_image)
        self.close()

    def remove_duplicates(self, name):
        for p in self.app.playlists.copy():
            if p.name == name:
                btn = pygame.display.message_box(
                    "Duplicate playlist",
                    "A playlist with the same name already exists. Proceeding will override the virtual contents of the previous playlist.",
                    "warn",
                    None,
                    ("Proceed", "Cancel"),
                )
                if btn == 1:
                    return False
                for music in p.musiclist:
                    if music is self.app.music:
                        self.app.end_music()
                self.app.playlists.remove(p)
        return True

    def close(self):
        self.app.list_viewer.modal_state = "none"
        self.selected_folder = None
        self.entryline.text = ""

    def event(self, event):
        if self.app.listening_key:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return
        if Keybinds.check("confirm", event, ignore_input=True):
            if self.create_type == "empty":
                self.action_create_empty()
            else:
                self.action_create_from_folder()
        if self.create_type == "empty":
            self.entryline.event(event)
