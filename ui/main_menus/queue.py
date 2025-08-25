import mili
import pygame
from functools import partial
from ui.common import *
from ui.common.data import MusicData


class QueueUI(UIComponent):
    def init(self):
        self.anim_back = animation(-5)
        self.anim_clear = animation(-2)
        self.anims = [animation(-3) for i in range(4)]
        self.cache = mili.ImageCache()
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, {"short_size": 7, "axis": "y"})
        self.sbar_size = self.scrollbar.style["short_size"]

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 110000)
        handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.back()
            self.mili.image(
                SURF, {"fill": True, "fill_color": MENU_BG_COL, "cache": self.cache}
            )

            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": "70" if self.app.split_w > 1200 else "90",
                    "filly": "75",
                    "align": "center",
                    "spacing": self.mult(13),
                    "offset": (
                        0,
                        -self.mult(50)
                        * (self.state.music is not None and not self.app.split_screen)
                        - self.app.tbarh / 2,
                    ),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.ui_modal_content()

            self.ui_overlay_btn(
                self.anim_back,
                self.back,
                ICONS.back,
                tooltip="Back to settings",
            )

    def ui_modal_content(self):
        with self.mili.begin(
            None,
            mili.RESIZE
            | mili.PADLESS
            | mili.CENTER
            | mili.X
            | {"clip_draw": False, "blocking": None},
        ):
            self.mili.text_element(
                "Queue",
                {"size": self.mult_fs(26)},
                None,
                mili.CENTER | {"blocking": None},
            )
            self.ui_image_btn(
                ICONS.delete,
                self.action_clear,
                self.anim_clear,
                30,
                tooltip="Clear the queue",
            )
        with self.mili.begin(
            None,
            {"fillx": True, "filly": True, "blocking": None} | mili.PADLESS,
        ) as cont:
            self.scroll.update(cont)
            self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
            self.scrollbar.update(cont)
            self.ui_scrollbar()
            for history in self.state.queue:
                self.ui_music(history, cont.data.absolute_rect)
            if len(self.state.queue) <= 0:
                self.mili.text_element(
                    "No music in the queue",
                    {"size": self.mult_fs(20), "color": (200,) * 3},
                    None,
                    {"align": "center", "blocking": None},
                )

        self.mili.element((0, 0, 0, self.mult(4)), {"blocking": None})

    def ui_music(self, music: MusicData, parent_rect):
        with self.mili.begin(
            (0, 0, 0, 0),
            {
                "fillx": "97" if self.scrollbar.needed else "99",
                "resizey": True,
                "anchor": "first",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "pady": 2,
                "spacing": 0,
                "align": "center",
            },
        ) as it:
            if it.data.absolute_rect.colliderect(parent_rect):
                self.mili.rect({"color": (MENUB_CV[0],) * 3})
                self.ui_music_title(music)
                self.ui_music_buttons(music, it)
            else:
                self.mili.element((0, 0, 0, self.mult(60)), {"blocking": False})

    def ui_music_buttons(self, music, parent: mili.Interaction):
        btnsize = 38
        rect = pygame.Rect(0, 0, self.mult(btnsize) * 4 * 1.1, self.mult(btnsize) * 1.1)
        with self.mili.begin(
            rect.move_to(midright=(parent.data.rect.w, parent.data.rect.h / 2)),
            {
                "ignore_grid": True,
                "default_align": "center",
                "anchor": "center",
                "axis": "x",
            },
        ):
            if self.app.can_interact() and parent.absolute_hover:
                self.ui_image_btn(
                    ICONS.up,
                    partial(self.action_up, music),
                    self.anims[0],
                    btnsize,
                    tooltip="Move up",
                )
                self.ui_image_btn(
                    ICONS.down,
                    partial(self.action_down, music),
                    self.anims[1],
                    btnsize,
                    tooltip="Move down",
                )
                self.ui_image_btn(
                    ICONS.play,
                    partial(self.action_play, music),
                    self.anims[2],
                    btnsize,
                    tooltip="Play now",
                )
                self.ui_image_btn(
                    ICONS.delete,
                    partial(self.action_remove, music),
                    self.anims[3],
                    btnsize,
                    tooltip="Remove from queue",
                    colors=RED_COLS,
                )
            else:
                for i in range(4):
                    self.mili.element(None)

    def ui_music_title(self, music: MusicData):
        if not music.loaded_cover and music.cover_path is not None:
            music.load_cover_async(music.cover_path, ICONS.loading)
        cover = music.cover
        if cover is None:
            cover = ICONS.music_cover
        with self.mili.begin(
            None,
            {
                "resizey": True,
                "fillx": True,
                "blocking": False,
            }
            | mili.PADLESS
            | mili.X,
        ):
            if cover is not None:
                self.mili.image_element(
                    cover,
                    {"cache": get_img_cache()},
                    (0, 0, self.mult(50), self.mult(50)),
                    {"align": "center", "blocking": False},
                )
            self.mili.text_element(
                music.name_or_alias(self.app),
                {
                    "size": self.mult_fs(16),
                    "growx": False,
                    "growy": False,
                    "wraplen": "100",
                    "font_align": pygame.FONT_LEFT,
                    "align": "topleft",
                },
                (0, 0, 0, self.mult(60)),
                {"align": "first", "blocking": False, "fillx": True},
            )

    def action_remove(self, music: MusicData):
        self.state.queue.remove(music)

    def action_play(self, music: MusicData):
        self.state.play_music(
            music,
            music.playlist.get_group_sorted_musics().index(music),
        )
        self.app.playlist_viewer.set_scroll_to_music()

    def action_up(self, music: MusicData):
        idx = self.state.queue.index(music)
        if idx > 0:
            self.state.queue.remove(music)
            self.state.queue.insert(idx - 1, music)

    def action_down(self, music: MusicData):
        idx = self.state.queue.index(music)
        if idx < len(self.state.queue) - 1:
            self.state.queue.remove(music)
            self.state.queue.insert(idx + 1, music)

    """
    def ui_history_title(self, history: HistoryData):
        if not history.music.loaded_cover and history.music.cover_path is not None:
            history.music.load_cover_async(history.music.cover_path, ICONS.loading)
        cover = history.music.cover
        if cover is None:
            cover = ICONS.music_cover
        with self.mili.begin(
            None,
            {
                "resizey": True,
                "fillx": True,
                "blocking": False,
            }
            | mili.PADLESS
            | mili.X,
        ):
            if cover is not None:
                self.mili.image_element(
                    cover,
                    {"cache": get_img_cache()},
                    (0, 0, self.mult(50), self.mult(50)),
                    {"align": "center", "blocking": False},
                )
            self.mili.text_element(
                history.music.name_or_alias(self.app),
                {
                    "size": self.mult_fs(16),
                    "growx": False,
                    "growy": False,
                    "wraplen": "100",
                    "font_align": pygame.FONT_LEFT,
                    "align": "topleft",
                },
                (0, 0, 0, self.mult(60)),
                {"align": "first", "blocking": False, "fillx": True},
            )

    def restore_history(self, history: HistoryData):
        self.app.playlist_viewer.enter(history.music.playlist)
        self.state.play_music(
            history.music,
            history.music.playlist.get_group_sorted_musics().index(history.music),
        )
        self.state.set_music_pos(history.position)
        self.app.playlist_viewer.set_scroll_to_music()
        self.app.modal_state = "none"
    """

    def queue_play(self, music: MusicData): ...

    def action_clear(self):
        self.state.queue = []

    def back(self):
        self.app.modal_state = "settings"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.MOUSEWHEEL:
            handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return True
        return False
