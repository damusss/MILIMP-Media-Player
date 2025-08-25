import os
import mili
import pygame
import threading
import pathlib
import shutil
import webbrowser
from ui.common import *
from ui.common.data import Playlist, Entryline
import tkinter.filedialog as filedialog
from ui.common.yt_actions import get_playlist_name_async, save_playlist_metadata


class NewPlaylistUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_create = animation(-3)
        self.anim_upload = animation(-3)
        self.entryline = Entryline(self.app, "Enter name...")
        self.yt_entry = Entryline(self.app, "Enter link...", target_files=False)
        self.cache = mili.ImageCache()
        self.create_type = "empty"
        self.selected_folder = None
        self.playlist_name = None
        self.playlist_url = None
        self.yt_searching = False
        self.error = None
        self.found_dependency = False
        self.playlist_meta = None

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 240000)
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
                self.anim_close, self.close, ICONS.close, tooltip="Close"
            )

    def ui_modal_content(self):
        self.mili.text_element(
            "New Playlist",
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
                (0, 0, row.data.rect.w / 3.01, 0),
                {"resizey": True, "padx": 0, "pady": 0},
            ) as left_cont:
                self.ui_section_btn(
                    left_cont, "empty", "Empty", "Create an empty playlist with a name"
                )

            with self.mili.begin(
                (0, 0, row.data.rect.w / 3.01, 0),
                {"resizey": True, "padx": 0, "pady": 0},
            ) as middle_cont:
                self.ui_section_btn(
                    middle_cont,
                    "folder",
                    "Load Folder",
                    "Create a playlist with all the tracks inside a folder",
                )

            with self.mili.begin(
                (0, 0, row.data.rect.w / 3.01, 0),
                {"resizey": True, "padx": 0, "pady": 0},
            ) as right_cont:
                self.ui_section_btn(
                    right_cont,
                    "youtube",
                    "YT Playlist",
                    "Create a playlist that can download and sync a youtube playlist",
                )

        if self.create_type == "empty":
            self.ui_empty_playlist_modal()
        elif self.create_type == "folder":
            self.ui_folder_playlist_modal()
        else:
            self.ui_youtube_playlist_modal()

    def ui_section_btn(self, cont, ctype, txt, tooltip):
        color = (255,) * 3 if self.create_type == ctype else (120,) * 3
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
                self.create_type = ctype
            if cont.hovered or cont.unhover_pressed:
                self.app.cursor_hover = True
            if cont.hovered:
                self.app.tick_tooltip(tooltip)

    def ui_empty_playlist_modal(self):
        self.entryline.ui(
            pygame.Rect(
                0, 0, mili.percentage(80, self.app.split_w / 1.35), self.mult(35)
            ),
            {"align": "center"},
        )
        self.ui_image_btn(
            ICONS.confirm,
            self.action_create_empty,
            self.anim_create,
            tooltip="Confirm and create the playlist",
        )

    def ui_folder_playlist_modal(self):
        self.mili.text_element(
            f"{self.selected_folder}"
            if self.selected_folder
            else "No folder selected (file drop supported)",
            {
                "color": "white" if self.selected_folder else (150,) * 3,
                "size": self.mult_fs(20) if self.selected_folder else self.mult_fs(18),
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
                ICONS.uploadf,
                self.action_folder_from_dialog,
                self.anim_upload,
                br="30",
                tooltip="Choose the folder for the playlist",
            )
            self.ui_image_btn(
                ICONS.confirm,
                self.action_create_from_folder,
                self.anim_create,
                tooltip="Confirm and create the playlist",
            )
        self.mili.text_element(
            "Creating might take some time if video files are present",
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

    def ui_youtube_playlist_modal(self):
        self.yt_entry.ui(
            pygame.Rect(
                0, 0, mili.percentage(80, self.app.split_w / 1.35), self.mult(35)
            ),
            {"align": "center"},
        )
        cur = self.yt_entry.text.strip()
        if cur != self.playlist_url:
            self.playlist_url = cur
            self.playlist_name = None
        if self.playlist_name is not None or self.error:
            self.mili.text_element(
                self.error
                if self.error
                else f"Selected playlist: {self.playlist_name}",
                {
                    "color": "red" if self.error else "white",
                    "size": self.mult_fs(22),
                    "wraplen": "100",
                    "growx": False,
                    "slow_grow": True,
                },
                (0, 0, mili.percentage(70, self.app.split_w), 0),
                {"align": "center", "blocking": None},
            )
        if self.yt_searching:
            self.mili.text_element(
                "Checking playlist...",
                {"size": self.mult_fs(20)},
                None,
                {"align": "center"},
            )
        else:
            self.ui_image_btn(
                ICONS.search_video if self.playlist_name is None else ICONS.confirm,
                self.action_yt_search
                if self.playlist_name is None
                else self.action_yt_create,
                self.anim_create,
                tooltip="Check the playlist"
                if self.playlist_name is None
                else "Create the youtube playlist",
            )

    def action_yt_search(self):
        self.error = None
        self.playlist_meta = None

        found = self.check_ytdlp_dependency()
        if not found:
            return True

        self.yt_searching = True
        thread = threading.Thread(target=get_playlist_name_async, args=(self,))
        thread.start()

    def check_ytdlp_dependency(self):
        if self.found_dependency:
            return True
        dep = shutil.which("yt-dlp")
        if dep is None:
            self.error = "Missing yt-dlp dependency"
            btn = pygame.display.message_box(
                "Missing Dependency 'yt-dlp'",
                "Searching playlists relies on the yt-dlp dependency that must be downloaded and possibly added to PATH. You can download the latest EXE from 'https://github.com/yt-dlp/yt-dlp/releases'.",
                "error",
                None,
                ("Understood", "Open Link"),
            )
            if btn == 1:
                webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases")
            return False
        else:
            self.found_dependency = True
        return True

    def action_yt_create(self):
        if self.playlist_name is None:
            return
        if "?list=" not in self.playlist_url:
            pygame.display.message_box(
                "Unexpected link layout",
                "The provided link is in an unexpected format (?list= expected). Contact the app developer if you think something is wrong.",
                "error",
                buttons=[
                    "Understood",
                ],
            )
            return
        name = self.playlist_url.split("?list=")[-1]
        if self.playlist_meta is not None:
            fname = f"{DATA_PATH}/yt_playlists/{name}"
            if not os.path.exists(fname):
                os.mkdir(fname)
            save_playlist_metadata(self.playlist_meta, f"{DATA_PATH}/yt_playlists/{name}/{name}.json")
        playlist = Playlist(
            name,
            [],
            None,
            yt_link=self.playlist_url,
            yt_name=self.playlist_name,
        )
        self.app.playlists.append(playlist)
        self.close()

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
            playlist = Playlist(name, paths, folder_path=path)
            self.app.playlists.append(playlist)
        else:
            realpaths = original.realpaths
            for newpath in paths:
                if newpath not in realpaths:
                    original.load_music(newpath, ICONS.loading)
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
                    if music is self.state.music:
                        self.state.end_music()
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
        if event.type == pygame.DROPFILE:
            folder = pathlib.Path(event.file)
            if folder.is_dir():
                self.selected_folder = folder.resolve()
        if Keybinds.check("confirm", event, ignore_input=True):
            if self.create_type == "empty":
                self.action_create_empty()
            elif self.create_type == "folder":
                self.action_create_from_folder()
            else:
                if self.playlist_name is None:
                    self.action_yt_search()
                else:
                    self.action_yt_create()
        if self.create_type == "empty":
            self.entryline.event(event)
        if self.create_type == "youtube":
            self.yt_entry.event(event)
