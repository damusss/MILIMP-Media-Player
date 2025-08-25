import mili
import pygame
import threading
from ui.common.yt_actions import (
    get_playlist_name_async,
    download_playlist_async,
)
from ui.common import *


class YTPlaylistUI(UIComponent):
    def init(self):
        self.extra_anim = animation(-3)
        self.anims = [animation(-5) for i in range(3)]
        self.cache = mili.ImageCache()
        self.getting_formats = False
        self.parent = None
        self.playlist_name = None
        self.playlist_url = ""
        self.error = None

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 210000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.PADLESS | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.close()
                return
            self.mili.image(
                SURF, {"fill": True, "fill_color": MENU_BG_COL, "cache": self.cache}
            )
            perc = 40 if self.app.split_w > 1200 else 80
            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": f"{perc}",
                    "resizey": True,
                    "align": "center",
                    "offset": (
                        0,
                        -self.app.tbarh
                        - (self.app.music_controls.cont_height / 2.7)
                        * (not self.app.split_screen),
                    ),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.mili.text_element(
                    "Download All Videos",
                    {"size": self.mult_fs(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                can_download = True
                if self.error:
                    text = f'<color fg="red">An error occurred: {self.error}</color>'
                    can_download = False
                elif self.parent.downloading_playlist is not None:
                    can_download = False
                    text = "A playlist is already being downloaded. Wait for that one to finish before downloading another one."
                elif self.playlist_name is None:
                    can_download = False
                    text = "Waiting for the playlist name..."
                else:
                    text = f'This will download every video from the <color fg="red">{self.playlist_name}</color> playlist to its folder. yt-dlp default download format will be used.'
                self.mili.text_element(
                    text,
                    {
                        "size": self.mult_fs(17),
                        "slow_grow": True,
                        "growx": False,
                        "wraplen": "100",
                        "rich": True,
                        "cache": "auto",
                    },
                    (0, 0, mili.percentage(perc, self.app.split_w), 0),
                    {
                        "align": "center",
                        "fillx": True,
                        "blocking": None,
                    },
                )
                if can_download:
                    self.ui_image_btn(
                        ICONS.download,
                        self.action_start_download,
                        self.anims[1],
                        size=40,
                        tooltip="Download All Videos",
                    )

            self.ui_overlay_btn(
                self.anims[0],
                self.close,
                ICONS.close,
                tooltip="Close",
            )

    def enter(self):
        self.parent = self.app.yt_search
        self.playlist_url = self.parent.search_entryline.text
        if self.parent.downloading_playlist is None:
            thread = threading.Thread(
                target=get_playlist_name_async, args=(self,), daemon=True
            )
            thread.start()

    def close(self):
        self.app.yt_search.modal_state = "none"
        self.playlist_name = None
        self.error = None

    def action_start_download(self):
        self.parent.downloading_playlist = self.playlist_name
        thread = threading.Thread(
            target=download_playlist_async, args=(self,), daemon=True
        )
        thread.start()
        self.close()

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
