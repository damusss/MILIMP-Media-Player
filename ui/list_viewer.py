import mili
import pygame
from ui.common import *
from ui.common.data import Playlist
from ui.list_menus.new_playlist import NewPlaylistUI
from ui.list_menus.rename_playlist import RenamePlaylistUI


class ListViewerUI(UIComponent):
    def init(self):
        self.new_playlist = NewPlaylistUI(self.app)
        self.rename_playlist = RenamePlaylistUI(self.app)
        self.modal_state = "none"
        self.middle_selected = None

        self.anim_add_playlist = animation(-5)
        self.anim_search = animation(-5)
        self.anim_toggle = animation(-3)
        self.menu_anims = [animation(-4) for i in range(2)]

        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(
            self.scroll, {"short_size": 7, "padding": 3, "border_dist": 3, "axis": "y"}
        )
        self.sbar_size = self.scrollbar.style["short_size"]

    def ui_top_buttons(self):
        if self.app.custom_title or self.app.modal_state == "fullscreen":
            return
        self.ui_overlay_top_btn(
            self.anim_toggle,
            self.app.toggle_custom_title,
            ICONS.resize,
            "left",
            tooltip="Enable custom borders",
        )

    def ui_check(self):
        if self.app.modal_state != "none" and self.modal_state != "none":
            if self.modal_state == "new_playlist":
                self.new_playlist.close()
            elif self.modal_state == "rename_playlist":
                self.rename_playlist.close()

    def ui(self):
        self.ui_check()

        if self.modal_state == "none" and self.app.modal_state == "none":
            handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

        self.scrollbar.style["short_size"] = self.mult(8)
        self.mili.text_element(
            "Media Player",
            {"size": self.mult(35)},
            None,
            {"align": "center", "blocking": None},
        )
        self.mili.line_element(
            [("-49.5", 0), ("49.5", 0)],
            {"size": 1, "color": (100,) * 3},
            (0, 0, 0, self.mult(10)),
            {"fillx": True, "blocking": False},
        )

        self.mili.id_checkpoint(45)
        with self.mili.begin(
            (0, 0, self.app.split_w, 0),
            {"filly": True},
        ) as scroll_cont:
            if len(self.app.playlists) > 0:
                self.scroll.update(scroll_cont)
                self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                self.scrollbar.update(scroll_cont)
                self.ui_scrollbar()
                self.mili.id_checkpoint(50)

                for playlist in self.app.playlists:
                    self.ui_playlist(playlist)

                self.mili.text_element(
                    f"{len(self.app.playlists)} playlist{'s' if len(self.app.playlists) > 1 else ''}",
                    {"size": self.mult(19), "color": (170,) * 3},
                    None,
                    {"offset": self.scroll.get_offset(), "blocking": None},
                )

            else:
                self.mili.text_element(
                    "No playlists",
                    {"size": self.mult(20), "color": (200,) * 3},
                    None,
                    {"align": "center", "blocking": None},
                )

        if self.modal_state == "none" and self.app.modal_state == "none":
            self.ui_overlay_btn(
                self.anim_add_playlist,
                self.action_new,
                ICONS.playlistadd,
                1,
                tooltip="Create a playlist",
            )
            self.ui_overlay_btn(
                self.anim_search,
                self.app.yt_search.enter,
                ICONS.search_video,
                2,
                tooltip="Search from YT Music",
            )
        elif self.modal_state == "new_playlist":
            self.new_playlist.ui()
        elif self.modal_state == "rename_playlist":
            self.rename_playlist.ui()

    def ui_scrollbar(self):
        if self.scrollbar.needed:
            with self.mili.begin(
                self.scrollbar.bar_rect, self.scrollbar.bar_style | {"blocking": None}
            ):
                self.mili.rect({"color": (SBAR_CV,) * 3})
                if handle := self.mili.element(
                    self.scrollbar.handle_rect, self.scrollbar.handle_style
                ):
                    self.mili.rect(
                        {"color": (cond(self.app, handle, *SHANDLE_CV),) * 3}
                    )
                    self.scrollbar.update_handle(handle)
                    if (
                        handle.hovered or handle.unhover_pressed
                    ) and self.app.can_interact():
                        self.app.cursor_hover = True
                        self.app.tick_tooltip(None)

    def ui_playlist(self, playlist: Playlist):
        with self.mili.begin(
            None,
            {
                "fillx": "100" if not self.scrollbar.needed else "98",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "padx": self.mult(10),
                "axis": "x",
                "align": "center",
                "resizey": True,
            },
        ) as cont:
            self.ui_playlist_bg(playlist, cont)

            imagesize = self.mult(70)
            padsize = 0
            cover = playlist.cover
            if cover is None:
                cover = ICONS.playlist_cover
            if cover is not None:
                self.mili.image_element(
                    cover,
                    {"cache": mili.ImageCache.get_next_cache()},
                    (0, 0, imagesize, imagesize),
                    {"align": "center", "blocking": False},
                )
            if self.app.music is not None and self.app.music.playlist is playlist:
                padsize = self.mult(30)
                self.mili.image_element(
                    ICONS.playbars,
                    {"cache": mili.ImageCache.get_next_cache()},
                    (0, 0, padsize, padsize),
                    {"align": "center", "blocking": False},
                )
            self.mili.text_element(
                playlist.name,
                {
                    "size": self.mult(25),
                    "wraplen": "100",
                    "growx": False,
                    "growy": True,
                    "slow_grow": True,
                    "align": "left",
                    "font_align": pygame.FONT_LEFT,
                },
                (0, 0, self.app.split_w / 1.1 - imagesize - padsize, 0),
                {
                    "align": "center",
                    "blocking": False,
                },
            )

            if self.app.can_interact():
                if cont.hovered or cont.unhover_pressed:
                    self.app.cursor_hover = True
                if cont.left_just_released:
                    self.app.playlist_viewer.enter(playlist)
                elif (
                    cont.just_released_button == pygame.BUTTON_RIGHT
                    and self.app.can_interact()
                ):
                    self.app.open_menu(
                        playlist,
                        (
                            ICONS.rename,
                            self.action_rename,
                            self.menu_anims[0],
                            "Rename playlist",
                        ),
                        (
                            ICONS.delete,
                            self.action_delete,
                            self.menu_anims[1],
                            "Delete playlist",
                        ),
                    )
                elif cont.just_pressed_button == pygame.BUTTON_MIDDLE:
                    self.middle_selected = playlist

    def ui_playlist_bg(self, playlist, cont):
        forcehover = (
            self.app.menu_data is playlist and self.app.menu_open
        ) or self.middle_selected is playlist
        if self.app.bg_effect:
            self.mili.image(
                SURF,
                {
                    "fill": True,
                    "fill_color": (
                        *(LIST_CV[1] if forcehover else cond(self.app, cont, *LIST_CV),)
                        * 3,
                        ALPHA,
                    ),
                    "border_radius": 0,
                    "cache": mili.ImageCache.get_next_cache(),
                },
            )
        else:
            self.mili.rect(
                {
                    "color": (
                        LIST_CV[1] if forcehover else cond(self.app, cont, *LIST_CV),
                    )
                    * 3,
                    "border_radius": 0,
                }
            )
        if forcehover:
            self.mili.rect(
                {"color": (LIST_CV[1] + 15,) * 3, "border_radius": 0, "outline": 1}
            )

    def action_new(self):
        self.modal_state = "new_playlist"

    def action_rename(self):
        self.modal_state = "rename_playlist"
        self.rename_playlist.entryline.text = self.app.menu_data.name
        self.rename_playlist.entryline.cursor = len(self.app.menu_data.name)
        self.app.close_menu()

    def action_delete(self):
        btn = pygame.display.message_box(
            "Confirm deletion",
            "Are you sure you want to delete the playlist? The tracks won't be deleted from disk. This action cannot be undone.",
            "warn",
            None,
            ("Proceed", "Cancel"),
        )
        if btn == 1:
            self.app.close_menu()
            return
        try:
            for music in self.app.menu_data.musiclist:
                if music is self.app.music:
                    self.app.end_music()
                self.app.remove_from_history(music)
            self.app.playlists.remove(self.app.menu_data)
        except Exception:
            pass
        self.app.close_menu()

    def event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_MIDDLE:
            self.middle_selected = None
        if (
            event.type == pygame.MOUSEWHEEL
            and self.modal_state == "none"
            and self.app.modal_state == "none"
        ):
            if self.middle_selected is not None:
                idx = self.app.playlists.index(self.middle_selected)
                inc = -int(event.y)
                new_idx = idx + inc
                if new_idx < 0:
                    new_idx = 0
                if new_idx >= len(self.app.playlists):
                    new_idx = len(self.app.playlists) - 1
                self.app.playlists.remove(self.middle_selected)
                self.app.playlists.insert(new_idx, self.middle_selected)
            else:
                handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)

        if self.modal_state == "new_playlist":
            self.new_playlist.event(event)
        elif self.modal_state == "rename_playlist":
            self.rename_playlist.event(event)
