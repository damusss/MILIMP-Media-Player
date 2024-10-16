import mili
import pygame
import pathlib
import mili._core
from ui.common import *
import tkinter.filedialog as filedialog


class ChangeCoverUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anims = [animation(-3) for i in range(4)]
        self.cache = mili.ImageCache()

        self.upload_image = load_icon("uploadf")
        self.brush_image = load_icon("brush")

        self.selected_image = None
        self.is_reset = False
        self.message_type = "info"
        self.message = "No image selected"
        self.img_cache = mili.ImageCache()

    def ui(self):
        self.mili.id_checkpoint(3000 + 50)
        with self.mili.begin(
            ((0, 0), self.app.window.size), {"ignore_grid": True} | mili.CENTER
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
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.ui_modal_content()

            self.ui_overlay_btn(
                self.anim_close, self.close, self.app.close_image, tooltip="Close"
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
            self.ui_image_btn(
                self.app.reset_image,
                self.action_reset,
                self.anims[0],
                tooltip="Use the default playlist cover",
            )
            self.ui_image_btn(
                self.brush_image,
                self.action_generate_cover,
                self.anims[1],
                tooltip="Automatically generate the cover",
            )
            self.ui_image_btn(
                self.upload_image,
                self.action_file_from_dialog,
                self.anims[2],
                br="30",
                tooltip="Load the cover from an image",
            )
            self.ui_image_btn(
                self.app.confirm_image,
                self.action_confirm,
                self.anims[3],
                tooltip="Apply the cover",
            )
        self.ui_info()

    def ui_selected_image(self):
        if self.selected_image is not None:
            size = mili.percentage(
                50, min(self.app.window.size[0], self.app.window.size[1] / 1.5)
            )
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
        allmusics = playlist.get_group_sorted_musics()
        shift = pygame.key.get_pressed()[pygame.K_LSHIFT]
        if len(allmusics) <= 0:
            self.message = "Cannot generate from empty playlist"
            self.message_type = "error"
        elif len(allmusics) == 1 or len(allmusics) == 3:
            self.selected_image = allmusics[0].cover_or(self.app.music_cover_image)
        elif len(allmusics) == 2:
            self.generate_cover_2(allmusics)
        elif len(allmusics) < 9 or not shift:
            self.generate_cover_4(allmusics)
        elif shift:
            self.generate_cover_9(allmusics)

    def generate_cover_9(self, allmusics):
        covers = []
        for idx in [0, 1, 2, 3, 4, -4, -3, -2, -1]:
            covers.append(allmusics[idx].cover_or(self.app.music_cover_image))
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

    def generate_cover_4(self, allmusics):
        covers = []
        for idx in [0, 1, -2, -1]:
            covers.append(allmusics[idx].cover_or(self.app.music_cover_image))
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

    def generate_cover_2(self, allmusics):
        first = allmusics[0].cover_or(self.app.music_cover_image)
        second = allmusics[1].cover_or(self.app.music_cover_image)
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
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if Keybinds.check("confirm", event):
            self.action_confirm()
        return False
