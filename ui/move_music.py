import mili
import pygame
from ui.common import *
from ui.data import MusicData, Playlist


class MoveMusicUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.cache = mili.ImageCache()
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, 7, 0, 0, 0, "y")
        self.sbar_size = self.scrollbar.short_size
        self.music: MusicData = None

    def ui(self):
        handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

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
                    "filly": "65",
                    "align": "center",
                    "offset": (0, -self.app.tbarh),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.mili.text_element(
                    "Move Music",
                    {"size": self.mult(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                self.mili.text_element(
                    "Select the playlist you want to move the music to"
                    if len(self.app.playlists) > 1
                    else "Not enough playlists to move",
                    {
                        "color": (150,) * 3,
                        "size": self.mult(16),
                        "slow_grow": True,
                        "growx": False,
                        "wraplen": "100",
                    },
                    (0, 0, mili.percentage(80, self.app.split_w), 0),
                    {"align": "center", "fillx": True, "blocking": None},
                )
                self.ui_playlists()
                self.mili.element((0, 0, 0, self.mult(5)), {"blocking": None})

            self.ui_overlay_btn(
                self.anim_close, self.close, self.app.close_image, tooltip="Close"
            )

    def ui_playlists(self):
        with self.mili.begin(
            None,
            {"fillx": True, "filly": True},
        ) as cont:
            self.scroll.update(cont)
            self.scrollbar.short_size = self.mult(self.sbar_size)
            self.scrollbar.update(cont)
            for playlist in self.app.playlists:
                if playlist is self.app.playlist_viewer.playlist:
                    continue

                with self.mili.begin(
                    (0, 0, 0, self.mult(60)),
                    {
                        "fillx": "98" if self.scrollbar.needed else True,
                        "anchor": "first",
                        "axis": "x",
                        "offset": (
                            self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                            self.scroll.get_offset()[1],
                        ),
                        "align": "center",
                    },
                ) as it:
                    self.mili.rect({"color": (cond(self.app, it, *MENUB_CV),) * 3})
                    cover = self.app.playlist_cover
                    if playlist.cover is not None:
                        cover = playlist.cover
                    if cover is not None:
                        self.mili.image_element(
                            cover,
                            {"cache": mili.ImageCache.get_next_cache()},
                            (0, 0, self.mult(50), self.mult(50)),
                            {"align": "center", "blocking": False},
                        )
                    self.mili.text_element(
                        f"{playlist.name}",
                        {"align": "left", "size": self.mult(22)},
                        None,
                        {"align": "center", "blocking": False},
                    )
                    if self.app.can_interact():
                        if it.left_just_released:
                            self.move(playlist)
                        if it.hovered or it.unhover_pressed:
                            self.app.cursor_hover = True
                        if it.hovered:
                            self.app.tick_tooltip("Move the track to this playlist")
            self.ui_scrollbar()

    def ui_scrollbar(self):
        if self.scrollbar.needed:
            with self.mili.begin(
                self.scrollbar.bar_rect, self.scrollbar.bar_style | {"blocking": None}
            ):
                self.mili.rect({"color": (BSBAR_CV,) * 3})
                if handle := self.mili.element(
                    self.scrollbar.handle_rect, self.scrollbar.handle_style
                ):
                    self.mili.rect(
                        {"color": (cond(self.app, handle, *SHANDLE_CV) * 1.2,) * 3}
                    )
                    self.scrollbar.update_handle(handle)
                    if (
                        handle.hovered or handle.unhover_pressed
                    ) and self.app.can_interact():
                        self.app.cursor_hover = True
                        self.app.tick_tooltip(None)

    def move(self, playlist: Playlist):
        if self.music == self.app.music:
            self.app.end_music()
        self.app.remove_from_history(self.music)
        if self.music.group is not None:
            self.music.group.remove(self.music)

        mp3path = f"data/mp3_converted/{self.app.playlist_viewer.playlist.name}_{self.music.realstem}.mp3"
        newmp3path = f"data/mp3_converted/{playlist.name}_{self.music.realstem}.mp3"
        if os.path.exists(mp3path):
            if not os.path.exists(newmp3path):
                os.rename(mp3path, newmp3path)

        coverpath = f"data/music_covers/{self.app.playlist_viewer.playlist.name}_{self.music.realstem}.png"
        if os.path.exists(coverpath):
            newcoverpath = (
                f"data/music_covers/{playlist.name}_{self.music.realstem}.png"
            )
            if not os.path.exists(newcoverpath):
                os.rename(coverpath, newcoverpath)

        self.app.playlist_viewer.playlist.remove(self.music.audiopath)
        playlist.load_music(
            [self.music.realpath, "converted"]
            if self.music.converted
            else self.music.realpath,
            self.app.loading_image,
        )

        self.close()

    def close(self):
        self.app.playlist_viewer.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.MOUSEWHEEL:
            handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
