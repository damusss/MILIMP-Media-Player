import mili
import pygame
import pathlib
import mili._core
import tkinter.filedialog as filedialog
from ui.common import *


class ChangeCoverUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anims = [animation(-3) for i in range(4)]

        self.upload_image = load_icon("uploadf")
        self.confirm_image = load_icon("confirm")
        self.brush_image = load_icon("brush")
        self.reset_image = load_icon("reset")
        self.cache = mili.ImageCache()

        self.selected_image = None
        self.is_reset = False
        self.message_type = "info"
        self.message = "No image selected"
        self.img_cache = mili.ImageCache()

    def ui(self):
        with self.mili.begin(
            ((0, 0), self.app.window.size), {"ignore_grid": True} | mili.CENTER
        ):
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.cache}
            )

            with self.mili.begin(
                (0, 0, 0, 0), {"fillx": "80", "resizey": True, "align": "center"}
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.ui_modal_content()

            self.app.ui_overlay_btn(
                self.anim_close,
                self.close,
                self.app.close_image,  # ([("-20", "-20"), ("20", "20")], [("-20", "20"), ("20", "-20")]),
            )

    def ui_modal_content(self):
        self.mili.text_element(
            "Change Cover", {"size": self.mult(26)}, None, mili.CENTER
        )
        self.ui_selected_image()
        with self.mili.begin(
            None,
            {
                "resizex": True,
                "resizey": True,
                "axis": "x",
                "clip_draw": False,
                "align": "center",
            },
        ):
            self.app.ui_image_btn(self.reset_image, self.action_reset, self.anims[0])
            self.app.ui_image_btn(
                self.brush_image, self.action_generate_cover, self.anims[1]
            )
            self.app.ui_image_btn(
                self.upload_image, self.action_file_from_dialog, self.anims[2], br="30"
            )
            self.app.ui_image_btn(
                self.confirm_image, self.action_confirm, self.anims[3]
            )
        self.ui_info()

    def ui_selected_image(self):
        if self.selected_image is not None:
            size = mili.percentage(50, self.app.window.size[0])
            self.mili.image_element(
                self.selected_image,
                {"cache": self.img_cache},
                (0, 0, size, size),
                {"align": "center"},
            )
        else:
            self.mili.text_element(
                f"{self.message}",
                {
                    "size": self.mult(20),
                    "color": ((170,) * 3)
                    if self.message_type == "info"
                    else (200, 40, 40),
                    "growx": False,
                },
                None,
                {"fillx": True},
            )

    def ui_info(self):
        self.mili.text_element(
            "Hold shift to generate up to 9 cells",
            {
                "size": self.mult(16),
                "color": (150,) * 3,
                "growx": False,
                "wraplen": mili.percentage(70, self.app.window.size[0]),
                "slow_grow": True,
            },
            None,
            {"fillx": True},
        )

    def action_confirm(self):
        if self.selected_image is None and not self.is_reset:
            pygame.display.message_box(
                "No image selected",
                "Upload or generate an image to change cover.",
                "error",
                None,
                ("Understood",),
            )
            return
        if self.is_reset:
            self.app.playlist_viewer.playlist.cover = None
            self.is_reset = False
        else:
            self.app.playlist_viewer.playlist.cover = self.selected_image
            pygame.image.save(
                self.selected_image,
                f"data/covers/{self.app.playlist_viewer.playlist.name}.png",
            )
        self.close()

    def action_reset(self):
        self.message_type = "info"
        self.message = "No image selected"
        self.is_reset = True
        self.selected_image = self.app.playlist_cover

    def action_generate_cover(self):
        self.message = "No image selected"
        self.message_type = "info"
        self.selected_image = None
        self.is_reset = False

        playlist = self.app.playlist_viewer.playlist
        shift = pygame.key.get_pressed()[pygame.K_LSHIFT]
        if len(playlist.filepaths) <= 0:
            self.message = "Cannot generate from empty playlist"
            self.message_type = "error"
        elif len(playlist.filepaths) == 1 or len(playlist.filepaths) == 3:
            self.selected_image = playlist.music_covers.get(
                playlist.filepaths[0], self.app.music_cover_image
            )
        elif len(playlist.filepaths) == 2:
            self.generate_cover_2(playlist)
        elif len(playlist.filepaths) < 9 or not shift:
            self.generate_cover_4(playlist)
        elif shift:
            self.generate_cover_9(playlist)

    def generate_cover_9(self, playlist):
        covers = []
        for idx in [0, 1, 2, 3, 4, -4, -3, -2, -1]:
            covers.append(
                playlist.music_covers.get(
                    playlist.filepaths[idx], self.app.music_cover_image
                )
            )
        size = covers[0].get_width()
        sz2 = size / 2
        new_surf = pygame.Surface((size * 3, size * 3))
        covers = [
            mili.fit_image(pygame.Rect(0, 0, size, size), cover, smoothscale=True)
            for cover in covers
        ]
        for i, pos in enumerate(
            [
                (sz2, sz2),
                (size + sz2, sz2),
                (size * 2 + sz2, sz2),
                (sz2, size + sz2),
                (size + sz2, size + sz2),
                (size * 2 + sz2, size + sz2),
                (sz2, size * 2 + sz2),
                (size + sz2, size * 2 + sz2),
                (size * 2 + sz2, size * 2 + sz2),
            ]
        ):
            new_surf.blit(covers[i], covers[i].get_rect(center=pos))
        self.selected_image = new_surf

    def generate_cover_4(self, playlist):
        covers = []
        for idx in [0, 1, -2, -1]:
            covers.append(
                playlist.music_covers.get(
                    playlist.filepaths[idx], self.app.music_cover_image
                )
            )
        size = covers[0].get_width()
        sz2 = size / 2
        new_surf = pygame.Surface((size * 2, size * 2))
        covers = [
            mili.fit_image(pygame.Rect(0, 0, size, size), cover, smoothscale=True)
            for cover in covers
        ]
        for i, pos in enumerate(
            [
                (sz2, sz2),
                (size + sz2, sz2),
                (sz2, size + sz2),
                (size + sz2, size + sz2),
            ]
        ):
            new_surf.blit(covers[i], covers[i].get_rect(center=pos))
        self.selected_image = new_surf

    def generate_cover_2(self, playlist):
        first = playlist.music_covers.get(
            playlist.filepaths[0], self.app.music_cover_image
        )
        second = playlist.music_covers.get(
            playlist.filepaths[1], self.app.music_cover_image
        )
        size = first.get_width()
        new_surf = pygame.Surface((size * 2, size * 2))
        first = mili.fit_image(pygame.Rect(0, 0, size, size), first, smoothscale=True)
        second = mili.fit_image(pygame.Rect(0, 0, size, size), second, smoothscale=True)
        new_surf.blit(first, first.get_rect(center=(size / 2, size / 2)))
        new_surf.blit(
            first,
            first.get_rect(center=(size + size / 2, size + size / 2)),
        )
        new_surf.blit(second, second.get_rect(center=(size + size / 2, size / 2)))
        new_surf.blit(second, second.get_rect(center=(size / 2, size + size / 2)))
        self.selected_image = new_surf

    def action_file_from_dialog(self):
        path = filedialog.askopenfilename()
        self.message = "No image selected"
        self.message_type = "info"
        self.is_reset = False
        if path:
            try:
                self.selected_image = pygame.image.load(
                    pathlib.Path(path).resolve()
                ).convert_alpha()
            except Exception:
                self.selected_image = None
                self.message = "Error while loading image"
                self.message_type = "error"

    def close(self):
        self.selected_image = None
        self.app.playlist_viewer.modal_state = "none"

    def event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
