import mili
import pygame
import threading
from ui.common import *
from ui.common.data import MusicData, NotCached, create_backup_async
from functools import partial
import tkinter.filedialog as filedialog


class BackupSaveUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.cache = mili.ImageCache()
        self.reset()
        self.anims = [animation(-3) for i in range(len(self.categories) + 1)]
        self.size_str = "0 B"
        self.backing_up = False

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
                    "Create Backup",
                    {"size": self.mult(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                self.mili.text_element(
                    "Select the components to add to a ZIP backup. When loading the backup, only those parts will be updated. When you are done, choose the backup location. Backing up might take some seconds. The ZIP's size will be lower than the size of the contents (up to ~70% less). A normal backup usually consists of playlists, settings and history.",
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
                for i, (name, value) in enumerate(list(self.categories.items())):
                    self.ui_category(name, value, i)
                self.mili.text_element(
                    f"Contents size: {self.size_str}",
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
                self.ui_image_btn(
                    ICONS.loading if self.backing_up else ICONS.confirm,
                    (lambda: ...) if self.backing_up else self.action_confirm,
                    self.anims[-1],
                    tooltip="Wait for the current backup to finish..."
                    if self.backing_up
                    else "Save the ZIP to disk",
                )

            self.ui_overlay_btn(
                self.anim_close, self.back, ICONS.close, tooltip="Close"
            )

    def ui_category(self, name, value, i):
        with self.mili.begin(
            None,
            {
                "axis": "x",
                "pad": 0,
                "fillx": "70",
                "resizey": True,
                "anchor": "max_spacing",
            },
        ):
            self.mili.text_element(name, {"size": self.mult(20)})
            self.ui_image_btn(
                ICONS.checkbox_on if value else ICONS.checkbox_off,
                partial(self.action_category, name, value),
                self.anims[i],
                30,
                "15",
                "Add category to backup"
                if not value
                else "Remove category from backup",
            )

    def action_category(self, name, curvalue):
        self.categories[name] = not curvalue
        self.refresh_size()

    def refresh_size(self):
        self.size_str = "0 B"
        size = 0
        get = os.path.getsize
        for category, value in self.categories.items():
            category = category.lower()
            if not value:
                continue
            if category == "settings":
                size += get("data/gpu.json") + get("data/settings.json")
            elif category == "playlists":
                size += get("data/playlists.json")
            elif category == "history":
                size += get("data/history.json") + get("data/search_results.json")
            elif category == "playlist covers":
                for file in os.listdir("data/covers"):
                    size += get(f"data/covers/{file}")
            elif category == "yt downloads":
                for file in os.listdir("data/yt_downloads"):
                    size += get(f"data/yt_downloads/{file}")
            elif category == "music covers":
                for file in os.listdir("data/music_covers"):
                    size += get(f"data/music_covers/{file}")
            elif category == "mp3 converted":
                for file in os.listdir("data/mp3_converted"):
                    size += get(f"data/mp3_converted/{file}")
        if size < 1024:
            self.size_str = f"{size} B"
        units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
        size = float(size)
        idx = 0
        while size >= 1024 and idx < len(units) - 1:
            size /= 1024
            idx += 1
        self.size_str = f"{size:.{3}f} {units[idx]}"

    def action_confirm(self):
        if self.backing_up:
            pygame.display.message_box(
                "Already creating a backup",
                "Wait for the current backup to complete before creating a new one",
                "warn",
                buttons=["Understood"],
            )
            return
        if all([not value for value in list(self.categories.values())]):
            pygame.display.message_box(
                "Cannot create empty backup",
                "Select at least one category to create a backup",
                "warn",
                buttons=["Understood"],
            )
            return
        path = filedialog.asksaveasfilename(
            defaultextension="zip",
            title="Save the backup ZIP as...",
            filetypes=[(".zip", "ZIP")],
        )
        if not path:
            return
        self.backing_up = True
        thread = threading.Thread(
            target=create_backup_async, args=(self.categories, path, self)
        )
        thread.start()

    def reset(self):
        self.categories = dict.fromkeys(
            [
                "Playlists",
                "Settings",
                "History",
                "Playlist Covers",
                "Music Covers",
                "MP3 Converted",
                "YT Downloads",
            ],
            False,
        )
        self.categories["Playlists"] = self.categories["Settings"] = self.categories[
            "History"
        ] = True

    def back(self):
        self.reset()
        self.app.modal_state = "settings"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return True
        if Keybinds.check("confirm", event):
            self.action_confirm()
            return True
        return False
