import mili
import pygame
from ui.common import *
from ui.common.data import Playlist, MenuButton, MusicData
from ui.list_menus.new_playlist import NewPlaylistUI
from ui.list_menus.rename_playlist import RenamePlaylistUI
from ui.list_menus.info import InfoUI


class ListViewerUI(UIComponent):
    def init(self):
        self.new_playlist = NewPlaylistUI(self.app)
        self.rename_playlist = RenamePlaylistUI(self.app)
        self.info = InfoUI(self.app)
        self.modal_state = "none"
        self.middle_selected = None

        self.overlay_anims = [animation(-5) for i in range(5)]
        self.top_anims = [animation(-3) for i in range(2)]
        self.menu_anims = [animation(-4) for i in range(2)]

        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(
            self.scroll, {"short_size": 7, "padding": 3, "border_dist": 3, "axis": "y"}
        )
        self.sbar_size = self.scrollbar.style["short_size"]
        self.show_favorites = True
        self.search_active = False

        self.maybe_holding_playlist = None
        self.holding_playlist = None
        self.sort_indicator_rect = None
        self.sort_release_playlist = None
        self.can_enter_playlist = True

    def ui_top_buttons(self):
        if self.app.modal_state != "none":
            return
        if self.app.custom_title:
            self.ui_overlay_top_btn(
                self.top_anims[0],
                self.action_info,
                ICONS.infooff,
                "left",
                tooltip="Read technical information",
            )
        else:
            self.ui_overlay_top_btn(
                self.top_anims[1],
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
            elif self.modal_state == "info":
                self.info.close()

    def ui(self):
        self.ui_check()

        if self.modal_state == "none" and self.app.modal_state == "none":
            handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

        self.scrollbar.style["short_size"] = self.mult(8)
        self.mili.text_element(
            "Media Player",
            {"size": self.mult_fs(35)},
            None,
            {"align": "center", "blocking": None},
        )
        self.ui_line((0, 0))

        self.mili.id_checkpoint(ID_OFFSET + 50000)
        with self.mili.begin(
            (0, 0, self.app.split_w, 0),
            {"filly": True},
        ) as scroll_cont:
            if len(self.app.playlists) > 0:
                self.scroll.update(scroll_cont)
                self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                self.scrollbar.update(scroll_cont)
                self.ui_scrollbar()
                self.mili.id_checkpoint(ID_OFFSET + 51000)

                if self.show_favorites:
                    for favorite in self.app.favorites:
                        if (
                            not favorite.loaded_cover
                            and favorite.cover_path is not None
                        ):
                            favorite.load_cover_async(
                                favorite.cover_path, ICONS.loading
                            )
                        cover = favorite.cover_or(ICONS.music_cover)
                        self.ui_favorite(
                            cover,
                            favorite.name_or_alias(self.app),
                            self.action_favorite_music,
                            favorite,
                            self.app.playlist_viewer.unfavorite,
                        )
                    for path in self.app.explorer.favorites:
                        self.ui_favorite(
                            ICONS.folder,
                            path,
                            self.action_favorite_explorer,
                            path,
                            self.app.explorer.unfavorite,
                        )
                    if (
                        len(self.app.favorites) > 0
                        or len(self.app.explorer.favorites) > 0
                    ):
                        self.ui_line(self.scroll.get_offset())
                for playlist in self.app.playlists:
                    self.ui_playlist(playlist)

                self.mili.text_element(
                    f"{len(self.app.playlists)} playlist{'s' if len(self.app.playlists) > 1 else ''}",
                    {"size": self.mult_fs(19), "color": (170,) * 3},
                    None,
                    {"offset": self.scroll.get_offset(), "blocking": None},
                )

                if (
                    self.holding_playlist is not None
                    and self.sort_indicator_rect is not None
                ):
                    self.mili.hline_element(
                        {
                            "size": SORT_INDICATOR_SIZE,
                            "color": "white",
                            "dash_size": (self.mult(10), self.mult(5)),
                        },
                        pygame.Rect(self.sort_indicator_rect).move(
                            self.scroll.get_offset()
                        ),
                        {"ignore_grid": True, "blocking": False},
                    )

                if self.holding_playlist is not None and not scroll_cont.absolute_hover:
                    mousey = pygame.mouse.get_pos(True)[1]
                    recty = (
                        scroll_cont.data.absolute_rect.y + self.app.window.position[1]
                    )
                    if mousey > recty:
                        recty += scroll_cont.data.rect.h
                    self.scroll.scroll(0, -(recty - mousey) / SORT_SCROLL_DIVIDER)

            else:
                self.mili.text_element(
                    "No playlists",
                    {"size": self.mult_fs(20), "color": (200,) * 3},
                    None,
                    {"align": "center", "blocking": None},
                )

        if self.modal_state == "none" and self.app.modal_state == "none":
            self.ui_overlay_buttons()
        elif self.modal_state == "new_playlist":
            self.new_playlist.ui()
        elif self.modal_state == "rename_playlist":
            self.rename_playlist.ui()
        elif self.modal_state == "info":
            self.info.ui()

    def ui_overlay_buttons(self):
        self.ui_overlay_btn(
            self.overlay_anims[0],
            self.action_new,
            ICONS.playlistadd,
            1,
            tooltip="Create a playlist",
        )
        self.ui_overlay_btn(
            self.overlay_anims[1],
            self.app.yt_search.enter,
            ICONS.search_video,
            2,
            tooltip="Search from YT Music",
        )
        self.ui_overlay_btn(
            self.overlay_anims[2],
            self.action_explore,
            ICONS.explore,
            3,
            tooltip="Explore Local Folders",
        )
        self.ui_overlay_btn(
            self.overlay_anims[3],
            self.action_toggle_search,
            ICONS.searchoff if self.search_active else ICONS.search,
            4,
            tooltip="Stop searching" if self.search_active else "Search anything",
        )
        self.ui_overlay_btn(
            self.overlay_anims[4],
            self.action_show_favorites,
            ICONS.favorite if self.show_favorites else ICONS.not_favorite,
            5,
            tooltip="Hide favorites" if self.show_favorites else "Show favorites",
        )

    def ui_line(self, offset):
        self.mili.line_element(
            [("-49.5", 0), ("49.5", 0)],
            {"size": 1, "color": (100,) * 3},
            (0, 0, 0, self.mult(10)),
            {"fillx": True, "blocking": False, "offset": offset},
        )

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

            imagesize = self.mult(ITEM_H - 10)
            padsize = 0
            cover = playlist.cover
            if cover is None:
                cover = ICONS.playlist_cover
                if playlist.is_yt:
                    cover = ICONS.yt_playlist
            if cover is not None:
                self.mili.image_element(
                    cover,
                    {"cache": get_img_cache()},
                    (0, 0, imagesize, imagesize),
                    {"align": "center", "blocking": False},
                )
            if self.state.music is not None and self.state.music.playlist is playlist:
                padsize = self.mult(30)
                self.mili.image_element(
                    ICONS.playbars,
                    {"cache": get_img_cache()},
                    (0, 0, padsize, padsize),
                    {"align": "center", "blocking": False},
                )
            self.mili.text_element(
                playlist.display_name,
                {
                    "size": self.mult_fs(25),
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
                if (
                    self.holding_playlist is not None
                    and self.holding_playlist is not playlist
                    and cont.absolute_hover
                ):
                    relative = (
                        pygame.Vector2(pygame.mouse.get_pos())
                        - cont.data.absolute_rect.topleft
                    )
                    if relative.y < cont.data.rect.h / 2:
                        self.sort_indicator_rect = (
                            cont.data.rect.left,
                            cont.data.rect.top - 3,
                            cont.data.rect.w,
                            SORT_INDICATOR_SIZE,
                        )
                        self.sort_release_playlist = (playlist, "top")
                    else:
                        self.sort_indicator_rect = (
                            cont.data.rect.bottomleft,
                            (cont.data.rect.w, SORT_INDICATOR_SIZE),
                        )
                        self.sort_release_playlist = (playlist, "bottom")
                if cont.unhover_pressed and self.maybe_holding_playlist is playlist:
                    self.maybe_holding_playlist = None
                    self.holding_playlist = playlist
                if cont.hovered or cont.unhover_pressed:
                    self.app.cursor_hover = True
                if cont.left_just_pressed:
                    self.maybe_holding_playlist = playlist
                if cont.left_just_released and self.can_enter_playlist:
                    self.app.playlist_viewer.enter(playlist)
                elif (
                    cont.just_released_button == pygame.BUTTON_RIGHT
                    and self.app.can_interact()
                ):
                    self.app.open_menu(
                        playlist,
                        MenuButton(
                            ICONS.rename,
                            self.action_rename,
                            self.menu_anims[0],
                            tooltip="Rename playlist",
                        ),
                        MenuButton(
                            ICONS.delete,
                            self.action_delete,
                            self.menu_anims[1],
                            tooltip="Delete playlist",red=True
                        ),
                    )
                elif cont.just_pressed_button == pygame.BUTTON_MIDDLE:
                    self.middle_selected = playlist

    def ui_favorite(self, cover, name, action, data, remove_action):
        with self.mili.begin(
            None,
            {
                "fillx": "100" if not self.scrollbar.needed else "98",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "padx": self.mult(3),
                "axis": "x",
                "align": "center",
                "resizey": True,
                "pady": 3,
            },
        ) as cont:
            self.ui_favorite_bg(cont)
            imagesize = self.mult(FAV_ITEM_H - 6)
            padsize = self.mult(30)
            with self.mili.element(
                (0, 0, padsize, padsize),
                {"align": "center"},
            ) as favel:
                self.mili.image(
                    ICONS.favorite,
                    {
                        "cache": get_img_cache(),
                        "alpha": cond(self.app, favel, 255, 180, 150),
                    },
                )
                if self.app.can_interact():
                    if favel.hovered:
                        self.app.cursor_hover = True
                        self.app.tick_tooltip("Remove from favorites")
                    if favel.left_clicked:
                        remove_action(data)

            self.mili.image_element(
                cover,
                {"cache": get_img_cache()},
                (0, 0, imagesize, imagesize),
                {"align": "center", "blocking": False},
            )
            self.mili.text_element(
                name,
                {
                    "size": self.mult_fs(18),
                    "wraplen": "100",
                    "growx": False,
                    "font_align": pygame.FONT_LEFT,
                    "align": "left",
                    "color": "gold",
                },
                (
                    0,
                    0,
                    self.app.split_w / 1.1 - imagesize - padsize,
                    self.mult(FAV_ITEM_H) / 1.1,
                ),
                {
                    "align": "center",
                    "blocking": False,
                },
            )
            if self.app.can_interact():
                if cont.hovered:
                    self.app.cursor_hover = True
                if cont.left_clicked:
                    action(data)

    def ui_favorite_bg(self, cont: mili.Interaction):
        if self.state.bg_effect:
            self.mili.image(
                SURF,
                {
                    "fill": True,
                    "fill_color": (
                        *(cond(self.app, cont, *LIST_CV),) * 3,
                        ALPHA,
                    ),
                    "border_radius": 0,
                    "cache": get_img_cache(),
                },
            )
        else:
            self.mili.rect(
                {
                    "color": (cond(self.app, cont, *LIST_CV),) * 3,
                    "border_radius": 0,
                }
            )

    def ui_playlist_bg(self, playlist, cont):
        forcehover = (
            (self.app.menu_data is playlist and self.app.menu_open)
            or self.middle_selected is playlist
            or self.holding_playlist is playlist
        )
        if self.state.bg_effect:
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
                    "cache": get_img_cache(),
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
                {
                    "color": (LIST_CV[1] + 15,) * 3,
                    "border_radius": 0,
                    "outline": (2 if self.holding_playlist is playlist else 1),
                }
                | (
                    {"dash_size": (self.mult(10), self.mult(5))}
                    if self.holding_playlist is playlist
                    else {}
                )
            )

    def action_favorite_music(self, music: MusicData):
        self.app.playlist_viewer.enter(music.playlist)
        if self.state.music is not music:
            self.state.play_music(
                music, music.playlist.get_group_sorted_musics().index(music)
            )
        self.app.playlist_viewer.set_scroll_to_music()

    def action_favorite_explorer(self, path):
        self.app.explorer.enter_folder(path)

    def action_toggle_search(self):
        self.search_active = not self.search_active

    def action_show_favorites(self):
        self.show_favorites = not self.show_favorites

    def action_explore(self):
        self.app.explorer.enter_folder(history=False)

    def action_new(self):
        self.modal_state = "new_playlist"

    def action_info(self):
        self.modal_state = "info"

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
                if music is self.state.music:
                    self.state.end_music()
                self.app.remove_from_history(music)
            self.app.playlists.remove(self.app.menu_data)
            self.app.notify(
                NOTIF.INFO, f"Playlist {self.app.menu_data.name} deleted succesfully"
            )
        except Exception:
            pass
        self.app.close_menu()

    def event(self, event):
        self.can_enter_playlist = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_MIDDLE:
            self.middle_selected = None
        if event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_LEFT:
            if (
                self.sort_release_playlist is not None
                and self.holding_playlist is not None
            ):
                release_playlist, side = self.sort_release_playlist
                index = self.app.playlists.index(release_playlist)
                if side == "bottom":
                    index += 1
                if index > self.app.playlists.index(self.holding_playlist):
                    index -= 1
                self.app.playlists.remove(self.holding_playlist)
                self.app.playlists.insert(index, self.holding_playlist)
                self.can_enter_playlist = False
            self.maybe_holding_playlist = None
            self.holding_playlist = None
            self.sort_release_playlist = None
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
        elif self.modal_state == "info":
            self.info.event(event)
