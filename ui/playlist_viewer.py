import mili
import shutil
import pygame
import pathlib
import platform
import threading
import subprocess
import webbrowser
from ui.common import *
import moviepy
import tkinter.filedialog as filedialog
from ui.playlist_menus.playlist_add import PlaylistAddUI
from ui.playlist_menus.move_music import MoveMusicUI
from ui.playlist_menus.add_to_group import AddToGroupUI
from ui.playlist_menus.change_cover import ChangeCoverUI
from ui.playlist_menus.rename_music import RenameMusicUI
from ui.playlist_menus.rename_group import RenameGroupUI
from ui.playlist_menus.music_metadata import MusicMetadataUI
from ui.common.data import (
    Playlist,
    MusicData,
    PlaylistGroup,
    NotCached,
    MenuButton,
    Entryline,
    convert_music_async,
)
from ui.common.yt_actions import YTPlaylistSyncAsync


class PlaylistViewerUI(UIComponent):
    def init(self):
        self.playlist: Playlist = None
        self.anim_add_music = animation(-5)
        self.anim_cover = animation(-5)
        self.anim_back = animation(-3)
        self.anim_search = animation(-5)
        self.anim_details = animation(-5)
        self.menu_anims = [animation(-4) for i in range(13)]
        self.modal_state = "none"
        self.middle_selected: MusicData | PlaylistGroup = None
        self.search_active = False
        self.search_entryline = Entryline(
            self.app, "Enter search...", False, CONTROLS_CV[0] + 5, CONTROLS_CV[1]
        )
        self.link_entryline = Entryline(
            self.app,
            "Enter playlist link...",
            False,
            CONTROLS_CV[0] + 5,
            CONTROLS_CV[1],
            (150,) * 3,
        )
        self.big_cover = False
        self.big_cover_time = 0

        self.playlist_add = PlaylistAddUI(self.app)
        self.change_cover = ChangeCoverUI(self.app)
        self.rename_music = RenameMusicUI(self.app)
        self.rename_group = RenameGroupUI(self.app)
        self.move_music = MoveMusicUI(self.app)
        self.add_to_group = AddToGroupUI(self.app)
        self.music_metadata = MusicMetadataUI(self.app)

        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(
            self.scroll, {"short_size": 8, "padding": 3, "border_dist": 3, "axis": "y"}
        )
        self.sbar_size = self.scrollbar.style["short_size"]
        self.cover_cache = mili.ImageCache()
        self.bigcover_cache = mili.ImageCache()
        self.black_cache = mili.ImageCache()
        self.yt_syncer = YTPlaylistSyncAsync(self, None)
        self.yt_need_refresh = False
        self.yt_show_details = True
        self.next_cursor_data = None
        self.deferred_scroll = None
        self.deferred_scroll_time = pygame.time.get_ticks()

    def sort_searched_songs(self):
        scores = {}
        rawsearch = self.search_entryline.text.strip()
        search = rawsearch.lower()
        for apath in [music.audiopath for music in self.playlist.musiclist]:
            path = self.playlist.musictable[apath].realpath
            score = 0
            rawname = str(path.stem)
            name = rawname.lower()
            if rawsearch in rawname:
                score += 100
            if search in name:
                score += 80
            words = rawsearch.split(" ")
            for rawword in words:
                if rawword in rawname:
                    score += 20
                if rawword.lower() in name:
                    score += 10
                if rawword.lower() in name.replace(" ", ""):
                    score += 5
            scores[apath] = score
        return [
            v[0] for v in sorted(list(scores.items()), key=lambda x: x[1], reverse=True)
        ]

    def enter(self, playlist):
        self.playlist = playlist
        self.app.change_state("playlist")
        if self.playlist.is_folder:
            self.action_refresh_folder()
        if self.playlist.is_yt:
            self.link_entryline.set_text(self.playlist.yt_link)
            self.yt_sync_refresh_files(self.playlist)

    def ui_top_buttons(self):
        if self.app.modal_state != "none" or self.modal_state != "none":
            return
        self.ui_overlay_top_btn(
            self.anim_back, self.back, ICONS.back, "left", tooltip="Back"
        )

    def ui_check(self):
        if self.app.modal_state != "none" and self.modal_state != "none":
            if self.modal_state == "add":
                self.playlist_add.close()
            elif self.modal_state == "move":
                self.move_music.close()
            elif self.modal_state == "add_group":
                self.add_to_group.close()
            elif self.modal_state == "cover":
                self.change_cover.close()
            elif self.modal_state == "rename":
                self.rename_music.close()
            elif self.modal_state == "rename_group":
                self.rename_group.close()
            elif self.modal_state == "metadata":
                self.music_metadata.close()

    def ui(self):
        self.ui_check()
        if self.next_cursor_data is not None:
            self.app.cursor_hover = True
            self.app.tick_tooltip(self.next_cursor_data)
            self.next_cursor_data = None

        if self.yt_need_refresh:
            self.yt_sync_refresh_files()

        if self.modal_state == "none" and self.app.modal_state == "none":
            handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

        if self.playlist is None:
            self.back()
        big_cover = self.ui_title()
        if big_cover and not self.big_cover:
            self.big_cover = True
            self.big_cover_time = pygame.time.get_ticks()
        if not big_cover:
            self.big_cover = False

        if self.yt_syncer.alive:
            extra = "..."
            if (
                self.yt_syncer.downloading
                and self.yt_syncer.downloading_video is not None
            ):
                extra = f": Downloading '{self.yt_syncer.downloading_video['title']}'"
            self.mili.text_element(
                f"Syncing '{self.yt_syncer.playlist.yt_name}'{extra}"
                if self.yt_syncer.playlist.yt_name != self.playlist.yt_name
                else f"Syncing{extra}",
                {"size": self.mult_fs(19), "color": (230,) * 3, "padx": self.mult(10)},
                None,
                {"align": "first", "blocking": None},
            )
        self.ui_container()

        if self.modal_state == "none" and self.app.modal_state == "none":
            self.ui_overlay_btn(
                self.anim_add_music,
                self.action_add_music,
                ICONS.playlistadd,
                1,
                tooltip="Add a track or a group",
            )
            self.ui_overlay_btn(
                self.anim_cover,
                self.action_cover,
                ICONS.change_cover,
                2,
                tooltip="Change the playlist cover",
            )
            self.ui_overlay_btn(
                self.anim_search,
                self.action_search,
                ICONS.searchoff if self.search_active else ICONS.search,
                3,
                tooltip="Disable search" if self.search_active else "Enable search",
            )
            if self.playlist.is_yt:
                self.ui_overlay_btn(
                    self.anim_details,
                    self.action_yt_show_details,
                    ICONS.shown if self.yt_show_details else ICONS.hidden,
                    4,
                    "Hide playlist details"
                    if self.yt_show_details
                    else "Show playlist details",
                )
        elif self.modal_state == "add":
            self.playlist_add.ui()
        elif self.modal_state == "move":
            self.move_music.ui()
        elif self.modal_state == "add_group":
            self.add_to_group.ui()
        elif self.modal_state == "cover":
            self.change_cover.ui()
        elif self.modal_state == "rename":
            self.rename_music.ui()
        elif self.modal_state == "rename_group":
            self.rename_group.ui()
        elif self.modal_state == "metadata":
            self.music_metadata.ui()

        if (
            big_cover
            and pygame.time.get_ticks() - self.big_cover_time >= BIG_COVER_COOLDOWN
        ):
            self.ui_big_cover()

        if (
            self.deferred_scroll is not None
            and pygame.time.get_ticks() - self.deferred_scroll_time >= 100
        ):
            type_, amount = self.deferred_scroll
            self.deferred_scroll = None
            if type_ == "increase":
                self.scroll.scroll(0, amount)
            else:
                self.scroll.set_scroll(0, amount)

    def ui_container(self):
        if self.state.async_videoclip is not None:
            self.state.async_videoclip.preview_rect.active = False
        with self.mili.begin(
            (0, 0, self.app.split_w, 0),
            {"filly": True},
        ) as scroll_cont:
            if self.search_active:
                paths = self.sort_searched_songs()
            else:
                paths = self.playlist.get_group_sorted_musics(paths=True)
            if len(paths) > 0:
                self.scroll.update(scroll_cont)
                self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                self.scrollbar.update(scroll_cont)

                self.ui_scrollbar()
                self.mili.id_checkpoint(ID_OFFSET + 15000)
                done_groups = []
                last_group = None
                off_screen = False

                for group in self.playlist.groups:
                    if len(group.musics) <= 0 and not self.search_active:
                        self.ui_group(group, empty=True)

                for i, path in enumerate(paths):
                    music = self.playlist.musictable[path]
                    if music.check():
                        continue
                    if last_group is not None and music.group != last_group:
                        self.ui_group_line()
                        last_group = None
                    if not self.search_active:
                        if music.group is not None:
                            if music.group not in done_groups:
                                self.ui_group(music.group)
                                if (
                                    music.group.mode == "h"
                                    and not music.group.collapsed
                                ):
                                    self.ui_group_musics(music.group)
                                last_group = music.group
                                done_groups.append(music.group)
                            if music.group.collapsed or music.group.mode == "h":
                                last_group = None
                                continue
                    if music.pending:
                        self.ui_pending(music)
                        continue
                    off_screen = self.ui_music(music, off_screen, i)

                self.mili.text_element(
                    f"{len(self.playlist.musiclist)} track{
                        's' if len(self.playlist.musiclist) > 1 else ''
                    }",
                    {"size": self.mult_fs(19), "color": (170,) * 3},
                    None,
                    {"offset": self.scroll.get_offset(), "blocking": None},
                )

            else:
                self.mili.text_element(
                    "No track matches your search"
                    if self.search_active
                    else "No tracks",
                    {"size": self.mult_fs(20), "color": (200,) * 3},
                    None,
                    {"align": "center", "blocking": None},
                )

    def ui_group(self, group: PlaylistGroup, empty=False):
        with self.mili.begin(
            None,
            {
                "fillx": "100" if not self.scrollbar.needed else "98",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "padx": self.mult(2),
                "axis": "x",
                "align": "center",
                "anchor": "center",
                "size_clamp": {"min": (None, self.mult(40))},
                "spacing": -self.mult(3),
            },
        ) as cont:
            self.ui_group_bg(group, empty, cont)
            if empty:
                self.mili.element((0, 0, self.mult(35), 0), {"blocking": None})
            else:
                self.mili.image_element(
                    (
                        ICONS.playbars
                        if self.state.music is not None
                        and self.state.music.group is group
                        else ICONS.down
                    )
                    if group.collapsed
                    else ICONS.up,
                    {
                        "cache": get_img_cache(),
                        "padx": self.mult(5)
                        if (
                            self.state.music is not None
                            and self.state.music.group is group
                            and group.collapsed
                        )
                        else 0,
                    },
                    (0, 0, self.mult(35), self.mult(35)),
                    {"blocking": False, "align": "center"},
                )
            self.mili.text_element(
                f"{group.name}{' (empty)' if empty else ''}",
                {
                    "size": self.mult_fs(18.5),
                    "growx": False,
                    "growy": True,
                    "slow_grow": True,
                    "wraplen": "100",
                    "font_align": pygame.FONT_LEFT,
                    "align": "left",
                },
                (
                    0,
                    0,
                    self.app.split_w / 1.01 - self.mult(50),
                    0,
                ),
                {"align": "center", "blocking": False},
            )
            if self.app.can_interact():
                if (cont.hovered or cont.unhover_pressed) and not empty:
                    self.app.cursor_hover = True
                if cont.hovered and empty:
                    self.app.tick_tooltip(
                        "Add at least on track to the group to interact with it"
                    )
                if not empty and cont.just_pressed_button == pygame.BUTTON_MIDDLE:
                    self.middle_selected = group
                elif cont.just_released_button == pygame.BUTTON_RIGHT:
                    self.app.open_menu(
                        group,
                        MenuButton(
                            ICONS.rename,
                            self.action_rename_group,
                            self.menu_anims[-3],
                            tooltip="Rename group",
                        ),
                        MenuButton(
                            ICONS.columns if group.mode == "v" else ICONS.rows,
                            self.action_group_mode,
                            self.menu_anims[-2],
                            "30",
                            "View group tracks in columns"
                            if group.mode == "v"
                            else "View group tracks in rows",
                        ),
                        MenuButton(
                            ICONS.delete,
                            self.action_delete_group,
                            self.menu_anims[-1],
                            tooltip="Delete group",
                        ),
                    )
                elif cont.left_just_released and not empty:
                    group.collapsed = not group.collapsed

    def ui_group_bg(self, group, empty, cont):
        color = (
            GROUP_CV[0]
            if empty
            else (
                GROUP_CV[1]
                if group is self.middle_selected
                else cond(self.app, cont, *GROUP_CV)
            ),
        ) * 3
        if self.state.bg_effect:
            self.mili.image(
                SURF,
                {
                    "fill": True,
                    "fill_color": (
                        *(color),
                        ALPHA,
                    ),
                    "border_radius": "5",
                    "cache": get_img_cache(),
                },
            )
        else:
            self.mili.rect(
                {
                    "color": color,
                    "border_radius": "5",
                }
            )

    def ui_group_line(self):
        self.mili.line_element(
            [(-self.app.split_w / 2 + self.mult(45), 0), ("49.5", 0)],
            {"size": 1, "color": (80,) * 3},
            (0, 0, 0, self.mult(7)),
            {"fillx": True, "offset": self.scroll.get_offset(), "blocking": None},
        )

    def ui_pending(self, music: MusicData):
        self.mili.text_element(
            f"'{music.name_or_alias(self.app)}' is being converted...",
            {
                "size": self.mult_fs(16),
                "color": (170,) * 3,
                "growx": False,
                "slow_grow": True,
                "wraplen": self.app.split_w * 0.95,
            },
            None,
            {"offset": self.scroll.get_offset(), "fillx": True, "blocking": None},
        )

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

    def ui_title(self):
        ret = False
        with self.mili.begin(
            None, mili.RESIZE | mili.PADLESS | mili.CENTER | {"blocking": None}
        ):
            coversize = 0
            if self.playlist.cover is not None:
                coversize = self.mult(80)
                with self.mili.begin(
                    (0, 0, 0, 0),
                    {
                        "resizex": True,
                        "resizey": True,
                        "align": "center",
                        "axis": "x",
                        "blocking": None,
                    },
                ):
                    it = self.mili.image_element(
                        self.playlist.cover,
                        {"cache": self.cover_cache, "smoothscale": True},
                        (0, 0, coversize, coversize),
                        {"align": "center"},
                    )
                    if (
                        it.absolute_hover
                        and self.modal_state == "none"
                        and self.app.modal_state == "none"
                        and self.app.can_interact()
                    ):
                        ret = True
                        self.app.cursor_hover = True
                    self.ui_title_txt(coversize)
            else:
                self.ui_title_txt(coversize)
            if self.playlist.is_yt and self.yt_show_details:
                self.ui_yt_link()
                if self.search_active:
                    self.ui_line("50")
            if self.playlist.is_folder:
                self.ui_folder_path()
                if self.search_active:
                    self.ui_line("50")
            if self.search_active:
                self.ui_search()
        self.ui_line("49.5")
        return ret

    def ui_line(self, perc):
        self.mili.line_element(
            [(f"-{perc}", 0), (f"{perc}", 0)],
            {"size": 1, "color": (100,) * 3},
            (0, 0, 0, self.mult(7)),
            {"fillx": True, "blocking": None},
        )

    def ui_yt_link(self):
        with self.mili.begin(
            (0, 0, self.app.split_w - self.mult(20), 0),
            {"resizey": True, "blocking": None} | mili.PADLESS | mili.X,
        ):
            size = self.mult(30)
            self.link_entryline.ui(
                (0, 0, 0, size),
                {"fillx": True},
            )
            self.ui_yt_btn(
                size,
                ICONS.minip,
                self.action_yt_open_link,
                "Open the playlist on YouTube",
            )
            self.ui_yt_btn(
                size,
                ICONS.close if self.yt_syncer.alive else ICONS.refresh,
                self.action_yt_stop_sync
                if self.yt_syncer.alive
                else self.action_yt_sync,
                "Stop syncing playlist" if self.yt_syncer.alive else "Sync playlist",
            )
        meta = self.playlist.yt_metadata
        if meta is None:
            return
        with self.mili.begin(
            (0, 0, self.app.split_w - self.mult(20), 0),
            {"resizey": True, "blocking": None} | mili.PADLESS | mili.X,
        ):
            if meta["channel_name"] is not None:
                with self.mili.element(None) as cit:
                    u, nu = "", ""
                    if cit.hovered:
                        u, nu = "<u>", "</u>"
                    self.mili.text(
                        f'Channel: <color fg="red">{u}{meta["channel_name"]}{nu}</color>',
                        {"size": self.mult_fs(19), "color": (180,) * 3, "rich": True},
                    )
                    if self.app.can_interact():
                        if cit.hovered:
                            self.app.cursor_hover = True
                            self.app.tick_tooltip(f"{meta['channel_url']}")
                        if cit.left_clicked:
                            webbrowser.open(str(meta["channel_url"]))
            infos = []
            if meta["count"] is not None:
                infos.append(
                    f'Tracks: <color fg="white">{len(self.playlist.musiclist)}/{meta["count"]}</color>'
                )
            if meta["sync_date"] is not None:
                infos.append(
                    f'Last Synced: <color fg="white">{meta["sync_date"]}</color>'
                )
            if len(infos) > 0:
                text = " ".join(infos)
                self.mili.text_element(
                    text,
                    {
                        "size": self.mult_fs(19),
                        "growx": False,
                        "rich": True,
                        "align": "left",
                        "font_align": "left",
                        "color": (150,) * 3,
                    },
                    None,
                    {"fillx": True},
                )

    def ui_yt_btn(self, size, icon, action, tooltip):
        if it := self.mili.element((0, 0, size, size)):
            self.mili.rect(
                {
                    "color": (cond(self.app, it, *OVERLAY_CV),) * 3,
                    "border_radius": 0,
                }
            )
            self.mili.image(
                icon,
                {"cache": get_img_cache()},
            )
            if self.app.can_interact():
                if it.left_just_released:
                    action()
                if it.hovered or it.unhover_pressed:
                    self.app.cursor_hover = True
                if it.hovered:
                    self.app.tick_tooltip(tooltip)

    def ui_folder_path(self):
        with self.mili.begin(
            (0, 0, self.app.split_w - self.mult(20), 0),
            {"resizey": True, "blocking": None, "default_align": "center"}
            | mili.PADLESS
            | mili.X,
        ) as parent:
            size = self.mult(30)
            self.mili.text_element(
                self.playlist.folder_path,
                {
                    "size": self.mult_fs(18),
                    "color": (180,) * 3,
                    "slow_grow": True,
                    "wraplen": parent.data.rect.w - self.mult(30) * 2,
                    "growx": False,
                },
                None,
                {"fillx": True},
            )
            if it := self.mili.element((0, 0, size, size)):
                self.mili.rect(
                    {
                        "color": (cond(self.app, it, *OVERLAY_CV),) * 3,
                        "border_radius": 0,
                    }
                )
                self.mili.image(
                    ICONS.refresh,
                    {"cache": get_img_cache()},
                )
                if self.app.can_interact():
                    if it.left_just_released:
                        self.action_refresh_folder()
                    if it.hovered or it.unhover_pressed:
                        self.app.cursor_hover = True
                    if it.hovered:
                        self.app.tick_tooltip("Refresh folder")

    def ui_search(self):
        with self.mili.begin(
            (0, 0, self.app.split_w - self.mult(20), 0),
            {"resizey": True, "blocking": None} | mili.PADLESS | mili.X,
        ):
            size = self.mult(30)
            self.search_entryline.ui(
                (0, 0, 0, size),
                {"fillx": True},
            )
            if it := self.mili.element((0, 0, size, size)):
                self.mili.rect(
                    {
                        "color": (cond(self.app, it, *OVERLAY_CV),) * 3,
                        "border_radius": 0,
                    }
                )
                self.mili.image(ICONS.backspace, {"cache": get_img_cache()})
                if self.app.can_interact():
                    if it.left_just_released:
                        self.search_entryline.text = ""
                        self.search_entryline.cursor = 0
                    if it.hovered or it.unhover_pressed:
                        self.app.cursor_hover = True
                    if it.hovered:
                        self.app.tick_tooltip("Erase the search entry")

    def ui_big_cover(self):
        self.mili.image_element(
            SURF,
            {"fill": True, "fill_color": MENU_BG_COL, "cache": self.black_cache},
            ((0, 0), (self.app.split_w, self.app.window.size[1])),
            {"ignore_grid": True, "parent_id": 0, "z": 99999, "blocking": False},
        )
        size = mili.percentage(90, min((self.app.split_w, self.app.window.size[1])))
        self.mili.image_element(
            self.playlist.cover,
            {"cache": self.bigcover_cache, "smoothscale": True},
            pygame.Rect(0, 0, size, size).move_to(
                center=(
                    self.app.split_w / 2,
                    self.app.window.size[1] / 2,
                )
            ),
            {
                "ignore_grid": True,
                "blocking": False,
                "z": 999999,
                "parent_id": self.mili.stack_id,
            },
        )

    def ui_title_txt(self, coversize):
        w = self.mili.text_size(
            self.playlist.display_name, {"size": self.mult_fs(32)}
        ).x
        if w >= self.app.split_w / 1.08 - coversize:
            self.mili.text_element(
                self.playlist.display_name,
                {
                    "size": self.mult_fs(32),
                    "slow_grow": True,
                    "wraplen": self.app.split_w / 1.08 - coversize,
                    "align": "left",
                },
                None,
                {"align": "center", "blocking": None},
            )
        else:
            self.mili.text_element(
                self.playlist.display_name,
                {
                    "size": self.mult_fs(32),
                    "align": "left",
                },
                None,
                {"align": "center", "blocking": None},
            )

    def ui_group_musics(self, group: PlaylistGroup):
        with self.mili.begin(
            (0, 0, 0, self.mult(80)),
            {
                "fillx": "100" if not self.scrollbar.needed else "98",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "axis": "x",
                "align": "center",
            }
            | mili.PADLESS,
        ) as cont:
            if cont.data.absolute_rect.colliderect(((0, 0), self.app.split_size)):
                for music in group.musics:
                    if mit := self.mili.element(None, {"fillx": True, "filly": True}):
                        if music.source_exists:
                            self.ui_music_bg(mit, music)
                        else:
                            self.mili.rect({"color": (100, 0, 0), "border_radius": 0})
                        if not music.loaded_cover and music.cover_path is not None:
                            music.load_cover_async(music.cover_path, ICONS.loading)
                        cover = music.cover_or(ICONS.music_cover)
                        if cover is not None:
                            ready = False
                            if not music.source_exists:
                                cover = ICONS.error
                            elif (
                                music is self.state.music
                                and self.state.async_videoclip is not None
                            ):
                                self.state.async_videoclip.preview_rect.set_rect(
                                    mit.data.rect
                                )
                                self.state.async_videoclip.preview_rect.active = True
                                cover, ready = (
                                    self.state.async_videoclip.preview_rect.get_or(
                                        cover
                                    )
                                )
                            self.mili.image(
                                cover,
                                {
                                    "cache": get_img_cache(),
                                    "pad": self.mult(3),
                                    "ready": ready,
                                },
                            )
                        if music is self.state.music:
                            self.mili.image(
                                ICONS.playbars,
                                {
                                    "cache": get_img_cache(),
                                    "pad": "30",
                                },
                            )
                        self.ui_music_interaction(music, mit)
                        if self.app.can_interact() and mit.hovered:
                            self.app.tick_tooltip(f"{music.name_or_alias(self.app)}")

    def ui_music(self, music: MusicData, offscreen=False, i=-1):
        if offscreen:
            self.mili.element((0, 0, 0, self.mult(ITEM_H)), {"blocking": False})
            return offscreen
        with self.mili.begin(
            None,
            {
                "fillx": "100" if not self.scrollbar.needed else "98",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "padx": self.mult(8),
                "axis": "x",
                "align": "center",
                "anchor": "first",
                "size_clamp": {"min": (None, self.mult(ITEM_H))},
            },
        ) as cont:
            if cont.data.absolute_rect.colliderect(((0, 0), self.app.split_size)):
                if music.source_exists:
                    self.ui_music_bg(cont, music)
                else:
                    self.mili.rect({"color": (100, 0, 0), "border_radius": 0})
                imagesize = padsize = 0
                if (
                    music.group is not None and not self.search_active
                ) or music is self.state.music:
                    padsize = self.mult(30)
                    self.mili.element(
                        (0, 0, padsize, 0), {"filly": True, "blocking": False}
                    )
                    if music is self.state.music:
                        self.mili.image(
                            ICONS.playbars,
                            {"cache": get_img_cache()},
                        )
                if not music.loaded_cover and music.cover_path is not None:
                    music.load_cover_async(music.cover_path, ICONS.loading)
                cover = music.cover_or(ICONS.music_cover)
                if cover is not None:
                    imagesize = self.mult(ITEM_H - 10)
                    cel = self.mili.element(
                        (0, 0, imagesize, imagesize),
                        {"align": "center", "blocking": False, "clip_draw": False},
                    )
                    ready = False
                    if not music.source_exists:
                        cover = ICONS.error
                    elif (
                        music is self.state.music
                        and self.state.async_videoclip is not None
                    ):
                        self.state.async_videoclip.preview_rect.set_rect(cel.data.rect)
                        self.state.async_videoclip.preview_rect.active = True
                        cover, ready = self.state.async_videoclip.preview_rect.get_or(
                            cover
                        )
                    self.mili.image(
                        cover,
                        {"cache": get_img_cache(), "ready": ready},
                    )
                self.mili.text_element(
                    music.name_or_alias(self.app),
                    {
                        "size": self.mult_fs(18),
                        "growx": False,
                        "growy": True,
                        "slow_grow": True,
                        "wraplen": "100",
                        "font_align": pygame.FONT_LEFT,
                        "align": "topleft",
                        "color": "gold" if music.favorite else "white",
                    },
                    (
                        0,
                        0,
                        self.app.split_w / 1.1 - imagesize - padsize,
                        self.mult(ITEM_H) / 1.1,
                    ),
                    {"align": "first", "blocking": False},
                )
                self.ui_music_interaction(music, cont, i)
                if self.playlist.is_yt and self.yt_show_details and cont.absolute_hover:
                    self.ui_yt_music(music, cont)
                elif self.playlist.is_yt and self.yt_show_details:
                    with self.mili.begin((0, 0, -3, 0)):
                        for i in range(1):
                            self.mili.element(None)
            else:
                self.mili.element(
                    (0, 0, 0, self.mult(ITEM_H - 10)), {"blocking": False}
                )
                if cont.data.absolute_rect.top > self.app.window.size[1] * 1.2:
                    offscreen = True
        return offscreen

    def ui_yt_music(self, music: MusicData, cont: mili.Interaction):
        if music.yt_metadata is None:
            return
        height = cont.data.rect.h / 3
        with self.mili.begin(
            (1, cont.data.rect.h - height, cont.data.rect.w - 2, height),
            {
                "ignore_grid": True,
                "axis": "x",
                "blocking": False,
                "default_align": "center",
            },
        ):
            self.mili.transparet_rect(
                {"color": (MUSIC_CV[1] + 10,) * 3, "border_radius": 0, "alpha": 200}
            )
            tsize = self.mult_fs(15)
            with self.mili.element(None) as it:
                url = f"{music.yt_metadata['url']}&list={self.playlist.name}"
                try:
                    views, suffix = format_views(int(music.yt_metadata["views"]))
                except Exception:
                    views, suffix = music.yt_metadata["views"], ""
                self.mili.text(
                    f'<a href="copy${url}">Copy Link</a> | <a href="open${url}">Watch on YouTube</a> | Channel: <a href="channel${music.yt_metadata["channel_url"]}">{music.yt_metadata["channel_name"]}</a> | Views: {views}{suffix}',
                    {
                        "size": tsize,
                        "rich": True,
                        "rich_actions": {
                            "link_click": self.action_yt_link_click,
                            "link_hover": self.action_yt_link_hover,
                        },
                        "rich_link_color": "red",
                    },
                )

                if it.left_clicked and self.app.can_interact():
                    pygame.scrap.put_text(url)

    def ui_music_interaction(self, music: MusicData, cont: mili.Interaction, i=-1):
        if self.app.can_interact():
            if cont.hovered or cont.unhover_pressed:
                self.app.cursor_hover = True
            if cont.left_just_released:
                music.check_exists()
                if music.source_exists:
                    self.action_start_playing(music)
                else:
                    self.action_restore_music(music, i)
            elif cont.just_released_button == pygame.BUTTON_RIGHT:
                music.check_exists()
                if music.source_exists:
                    self.open_menu(music)
            elif cont.just_pressed_button == pygame.BUTTON_MIDDLE:
                self.middle_selected = music

    def ui_music_bg(self, cont, music):
        forcehover = (
            self.state.music == music
            or (self.app.menu_data == music and self.app.menu_open)
            or self.middle_selected == music
        )
        color = MUSIC_CV[1] if forcehover else cond(self.app, cont, *MUSIC_CV)
        if self.state.bg_effect:
            self.mili.image(
                SURF,
                {
                    "fill": True,
                    "fill_color": (
                        *((color,) * 3),
                        ALPHA,
                    ),
                    "border_radius": 0,
                    "cache": get_img_cache(),
                },
            )

        else:
            self.mili.rect(
                {
                    "color": (color,) * 3,
                    "border_radius": 0,
                }
            )
        if forcehover:
            self.mili.rect(
                {"color": (MUSIC_CV[1] + 15,) * 3, "border_radius": 0, "outline": 1}
            )

    def action_yt_link_click(self, data: str):
        if not self.app.can_interact():
            return
        action, url = data.split("$", 1)
        if action == "copy":
            pygame.scrap.put_text(url)
        elif action == "open":
            webbrowser.open(url)
        elif action == "channel":
            webbrowser.open(url)

    def action_yt_link_hover(self, data: str):
        action, url = data.split("$", 1)
        self.next_cursor_data = url

    def open_menu(self, music: MusicData):
        before = []
        if music not in self.state.queue or self.state.music is None:
            before.append(
                MenuButton(
                    ICONS.queue,
                    self.action_add_to_queue,
                    self.menu_anims[12],
                    "50",
                    "Play"
                    if self.state.music is None
                    else (
                        "Play next" if len(self.state.queue) == 0 else "Add to queue"
                    ),
                )
            )
        buttons = before + [
            MenuButton(
                ICONS.rename,
                self.action_rename,
                self.menu_anims[1],
                tooltip="Rename track",
            ),
            MenuButton(
                ICONS.favorite
                if music.realpath in self.playlist.favorites
                else ICONS.not_favorite,
                self.action_favorite,
                self.menu_anims[11],
                tooltip="Remove from favorites"
                if music.realpath in self.playlist.favorites
                else "Add to favorites",
            ),
            MenuButton(
                ICONS.forward,
                self.action_forward,
                self.menu_anims[2],
                tooltip="Move track to playlist",
            ),
            MenuButton(
                ICONS.minip,
                self.action_show_in_explorer,
                self.menu_anims[3],
                "50",
                "Show in explorer",
            ),
        ]
        if len(self.playlist.groups) > 0:
            buttons.insert(
                0,
                MenuButton(
                    (ICONS.playlistadd if music.group is None else ICONS.remove),
                    (
                        self.action_add_to_group
                        if music.group is None
                        else self.action_remove_from_group
                    ),
                    self.menu_anims[0],
                    tooltip="Add to group"
                    if music.group is None
                    else "Remove from group",
                ),
            )
        if (
            music.realpath.suffix != ".mp3"
            and not music.isvideo
            and not music.converted
            and not music.isconvertible
        ):
            buttons.append(
                MenuButton(
                    ICONS.convert,
                    self.action_convert,
                    self.menu_anims[4],
                    "50",
                    "Convert to MP3",
                )
            )
        buttons.extend(
            [
                MenuButton(
                    ICONS.change_cover,
                    self.action_change_cover,
                    self.menu_anims[6],
                    "50",
                    "Change track cover",
                ),
                MenuButton(
                    ICONS.folder_move,
                    self.action_folder_move,
                    self.menu_anims[10],
                    "50",
                    "Move the track to a different disk location",
                ),
                MenuButton(
                    ICONS.infoon,
                    self.action_metadata,
                    self.menu_anims[7],
                    tooltip="View track metadata",
                ),
                MenuButton(
                    ICONS.delete,
                    self.action_delete,
                    self.menu_anims[8],
                    tooltip="Delete track",
                    red=True,
                ),
            ]
        )
        self.app.open_menu(music, *buttons)

    def action_add_to_queue(self):
        if self.state.music is None:
            self.action_start_playing(self.app.menu_data)
        else:
            self.state.queue.append(self.app.menu_data)
        self.app.close_menu()

    def action_yt_stop_sync(self):
        if not self.yt_syncer.alive or self.yt_syncer.thread is None:
            return
        self.yt_syncer.alive = False
        self.yt_syncer.thread.join()
        self.yt_syncer.playlist = None

    def action_yt_sync(self):
        if self.yt_syncer.alive:
            return
        self.yt_syncer.alive = True
        self.yt_syncer.playlist = self.playlist
        self.yt_syncer.video_covers = {}
        thread = threading.Thread(target=self.yt_syncer.sync_async, daemon=True)
        self.yt_syncer.thread = thread
        thread.start()

    def yt_sync_refresh_files(self, playlist=None):
        playlist: Playlist = self.yt_syncer.playlist if playlist is None else playlist
        realpaths = [pathlib.Path(path).absolute() for path in playlist.realpaths]
        for file in os.listdir(f"{DATA_PATH}/yt_playlists/{playlist.name}"):
            full = pathlib.Path(
                f"{DATA_PATH}/yt_playlists/{playlist.name}/{file}"
            ).absolute()
            suffixes = [
                suffix
                for suffix in full.suffixes
                if len(suffix) <= 5 and len(suffix) >= 2
            ]
            if full.suffix[1:] not in FORMATS or "part" in file or len(suffixes) > 1:
                continue
            if pathlib.Path(file) not in realpaths:
                music = playlist.load_music(full, ICONS.loading)
                if music is not None and music.yt_id in self.yt_syncer.video_covers:
                    music.cover = self.yt_syncer.video_covers[music.yt_id]
                    music.loaded_cover = True
        self.yt_need_refresh = False

    def action_yt_show_details(self):
        self.yt_show_details = not self.yt_show_details

    def action_yt_open_link(self):
        webbrowser.open(self.playlist.yt_link)

    def action_refresh_folder(self):
        realpaths = self.playlist.realpaths
        for file in os.listdir(self.playlist.folder_path):
            full = pathlib.Path(os.path.join(self.playlist.folder_path, file))
            if full.suffix[1:] in FORMATS and full not in realpaths:
                self.playlist.load_music(full, ICONS.loading)

    def action_folder_move(self):
        if self.app.menu_data is self.state.music:
            self.state.end_music()
        self.app.close_menu()
        folder = filedialog.askdirectory()
        if not folder:
            return
        music: MusicData = self.app.menu_data
        audiopath_same_realpath = music.audiopath == music.realpath
        new_path = os.path.join(folder, music.realpath.name)
        if os.path.exists(new_path):
            return
        new_path = pathlib.Path(shutil.move(music.realpath, folder))
        music.realpath = new_path
        if audiopath_same_realpath:
            old_path = music.audiopath
            music.audiopath = new_path
            music.playlist.musictable.pop(old_path)
            music.playlist.musictable[new_path] = music
        self.app.notify(
            NOTIF.CONFIRM,
            f"'{music.realpath}' succesfully moved to the new destination '{folder}'",
        )

    def action_restore_music(self, music: MusicData, index=-1):
        button = pygame.display.message_box(
            "Track renamed, deleted or moved",
            "The track was renamed or deleted outside of the app or moved to a new location. You can choose to remove it from the playlist or specify its new location.",
            "error",
            buttons=["Specify Location", "Remove", "Resolve Later"],
        )
        if button == 2:
            return
        if button == 1:
            music.playlist.remove(music.audiopath)
            return
        path = filedialog.askopenfilename()
        if not path:
            return
        group = music.group
        if group:
            gidx = group.musics.index(music)
        new_music = music.playlist.load_music(pathlib.Path(path), ICONS.loading, index)
        music.playlist.remove(music.audiopath)
        if group is not None:
            group.musics.insert(gidx, new_music)
            new_music.group = group
        self.app.notify(
            NOTIF.CONFIRM, f"Track's location was updated succesfully to '{path}'"
        )

    def action_favorite(self):
        if self.app.menu_data.realpath in self.playlist.favorites:
            self.playlist.favorites.remove(self.app.menu_data.realpath)
            self.app.favorites.remove(self.app.menu_data)
            self.app.menu_data.favorite = False
        else:
            self.playlist.favorites.append(self.app.menu_data.realpath)
            self.app.favorites.append(self.app.menu_data)
            self.app.menu_data.favorite = True
        self.app.close_menu()

    def unfavorite(self, music: MusicData):
        music.playlist.favorites.remove(music.realpath)
        self.app.favorites.remove(music)
        music.favorite = False

    def action_change_cover(self):
        music: MusicData = self.app.menu_data
        path = filedialog.askopenfilename()
        if path:
            try:
                img = pygame.image.load(pathlib.Path(path).resolve()).convert_alpha()
                music.cover = img
                music.loaded_cover = True
                pygame.image.save(
                    img,
                    f"{DATA_PATH}/music_covers/{self.playlist.name}_{music.realstem}.png",
                )
            except Exception as e:
                messagebox_notify(
                    self.app,
                    NOTIF.ERROR,
                    "Error loading cover image",
                    f"The cover could not be loaded for an unexpected error: '{e}'",
                    "error",
                    None,
                    ("Understood",),
                )
        self.app.close_menu()

    def action_group_mode(self):
        if self.app.menu_data.mode == "v":
            self.app.menu_data.mode = "h"
        else:
            self.app.menu_data.mode = "v"
        self.app.close_menu()

    def action_add_to_group(self):
        self.modal_state = "add_group"
        self.add_to_group.music = self.app.menu_data
        self.app.close_menu()

    def action_metadata(self):
        self.modal_state = "metadata"
        self.music_metadata.music = self.app.menu_data
        if self.music_metadata.music.duration is NotCached:
            self.music_metadata.music.cache_duration()
        self.app.close_menu()

    def action_remove_from_group(self):
        self.app.menu_data.group.remove(self.app.menu_data)
        if self.app.menu_data is self.state.music:
            self.state.music_index = self.playlist.get_group_sorted_musics().index(
                self.app.menu_data
            )
        self.app.close_menu()

    def action_convert(self):
        btn = pygame.display.message_box(
            "Confirm conversion",
            "Are you sure you want to convert this audio file to an MP3 file? "
            "The original file will not be modified. MP3 files allow track positioning. "
            f"You can find the converted file at 'data/mp3_converted/{self.playlist.name}_{self.app.menu_data.realstem}.mp3' "
            "which will be played automatically.",
            "warn",
            None,
            ("Proceed", "Cancel"),
        )
        if btn == 1:
            return
        music = self.app.menu_data
        new_path = pathlib.Path(
            f"{DATA_PATH}/mp3_converted/{self.playlist.name}_{music.realstem}.mp3"
        ).resolve()
        if os.path.exists(new_path):
            self.app.close_menu()
            if music is self.state.music:
                self.state.end_music()
            music.converted = True
            return

        try:
            audiofile = moviepy.AudioFileClip(str(music.realpath))
        except Exception as exc:
            messagebox_notify(
                self.app,
                NOTIF.ERROR,
                "Could not convert music",
                f"Could not convert '{music.realpath}' to MP3 due to external exception: '{exc}'.",
                "error",
                None,
                ("Understood",),
            )
            return

        self.app.close_menu()
        if music is self.state.music:
            self.state.end_music()

        music.audiofile = audiofile
        music.pending = True
        music.audio_converting = True
        music.load_exc = None
        music.audiopath = new_path
        music.playlist.musictable.pop(music.realpath)
        music.playlist.musictable[music.audiopath] = music
        thread = threading.Thread(
            target=convert_music_async,
            args=(music, audiofile, new_path, self.app),
            daemon=True,
        )
        thread.start()

    def action_search(self):
        if self.search_active:
            self.stop_searching()
        else:
            self.search_active = True

    def action_cover(self):
        self.modal_state = "cover"
        self.change_cover.selected_image = self.playlist.cover
        for music in self.playlist.musiclist:
            if not music.loaded_cover and music.cover_path is not None:
                music.load_cover_async(music.cover_path, ICONS.loading)

    def action_add_music(self):
        self.modal_state = "add"

    def back(self):
        for music in self.playlist.musiclist:
            if music is self.state.music or music.favorite:
                continue
            music.loading_cover = False
            music.loaded_cover = False
            music.cover = None
        self.app.change_state("list")
        self.scroll.set_scroll(0, 0)

    def action_rename(self):
        self.modal_state = "rename"
        self.rename_music.music = self.app.menu_data
        self.rename_music.disk_entry.set_text(self.rename_music.music.realstem)
        alias = self.rename_music.music.alias
        if alias is None:
            alias = ""
        self.rename_music.alias_entry.set_text(alias)
        # ADD CURRENT ALIAS TO IT
        self.app.close_menu()

    def action_rename_group(self):
        self.modal_state = "rename_group"
        self.rename_group.group = self.app.menu_data
        self.rename_group.entryline.text = self.rename_group.group.name
        self.rename_group.entryline.cursor = len(self.rename_group.group.name)
        self.app.close_menu()

    def action_forward(self):
        self.modal_state = "move"
        self.move_music.music = self.app.menu_data
        self.app.close_menu()

    def action_show_in_explorer(self):
        system = platform.system()
        path = self.app.menu_data.realpath.parent
        self.app.close_menu()

        if system == "Windows":
            subprocess.Popen(
                ["explorer", path],
                creationflags=subprocess.CREATE_NO_WINDOW
                | subprocess.CREATE_NEW_CONSOLE,
            )
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        elif system == "Linux":
            subprocess.Popen(["xdg-open", path])
        else:
            pygame.display.message_box(
                "Operation failed",
                "Could not show file in explorer due to unsupported OS.",
                "error",
                None,
                ("Understood"),
            )

    def action_delete(self):
        btn = pygame.display.message_box(
            "Confirm deletion",
            "Are you sure you want to remove the music? The track won't be deleted from disk. This action cannot be undone. "
            "If you proceed and delete the conversion, eventual MP3 generated files will be deleted aswell. "
            "Not deleting the conversion will make adding the track back faster.",
            "warn",
            None,
            ("Proceed", "Proceed & Delete Conversion", "Cancel"),
        )
        if btn == 2:
            self.app.close_menu()
            return
        try:
            if self.app.menu_data == self.state.music:
                self.state.end_music()
            self.app.remove_from_history(self.app.menu_data)
            path = self.app.menu_data.audiopath
            self.playlist.remove(path)
            if btn == 1:
                mp3_path = f"{DATA_PATH}/mp3_converted/{self.playlist.name}_{self.app.menu_data.realstem}.mp3"
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
            self.app.notify(
                NOTIF.INFO,
                f"Track {self.app.menu_data.realpath} removed from the playlist",
            )
        except Exception:
            pass
        self.app.close_menu()

    def action_delete_group(self):
        if len(self.app.menu_data.musics) > 0:
            btn = pygame.display.message_box(
                "Confirm deletion",
                "Are you sure you want to delete the group? The tracks inside will be added back to the playlist. This action cannot be undone.",
                "warn",
                None,
                ("Proceed", "Cancel"),
            )
            if btn == 1:
                self.app.close_menu()
                return
        musictochangeindex = None
        for music in self.app.menu_data.musics.copy():
            self.app.menu_data.remove(music)
            if music is self.state.music:
                musictochangeindex = music
        if musictochangeindex is not None:
            self.state.music_index = self.playlist.get_group_sorted_musics().index(
                musictochangeindex
            )
        self.playlist.groups.remove(self.app.menu_data)
        self.app.notify(
            NOTIF.INFO, f"Playlist group {self.app.menu_data.name} removed successfully"
        )
        self.app.close_menu()

    def action_start_playing(self, music: MusicData):
        self.state.play_music(
            music, music.playlist.get_group_sorted_musics().index(music)
        )

    def stop_searching(self):
        self.search_active = False
        self.search_entryline.text = ""

    def set_scroll_to_music(self, increase=False, incdir=1):
        if self.state.music.require_ffplay:
            return
        if self.state.music.group is not None:
            self.state.music.group.collapsed = False
        if increase:
            self.deferred_scroll = "increase", (self.mult(80) + 6) * incdir
            self.deferred_scroll_time = pygame.time.get_ticks()
            return
        self.enter(self.state.music.playlist)
        remove_amount = 0
        group_amount = 0
        line_amount = 0
        for group in self.state.music.playlist.groups:
            if len(group.musics) <= 0:
                group_amount += 1
            else:
                if (
                    group.idx <= self.state.music_index
                    or group is self.state.music.group
                ):
                    group_amount += 1
                    if group.collapsed:
                        remove_amount += len(group.musics)
                    elif group.mode == "h":
                        remove_amount += len(group.musics) - 1
                    elif group.idx < self.state.music_index:
                        line_amount += 1
        self.deferred_scroll = (
            "set",
            (
                ((self.state.music_index - 1) * (self.mult(80) + 3))
                - (remove_amount * (self.mult(80) + 3))
                + (group_amount * (self.mult(45) + 3))
                + (line_amount * (self.mult(7) + 3))
            ),
        )
        self.deferred_scroll_time = pygame.time.get_ticks()

    def reorder_musics_groups(self, event):
        mult = 1
        if pygame.key.get_pressed()[pygame.K_LSHIFT]:
            mult = 5
        inc = -int(event.y) * mult
        if isinstance(self.middle_selected, MusicData):
            if self.middle_selected.group is None:
                self.reorder_music_nogroup(inc)
            else:
                self.reorder_music_group(inc)

            if self.middle_selected is self.state.music:
                self.state.music_index = self.playlist.get_group_sorted_musics().index(
                    self.middle_selected
                )
        else:
            self.reorder_group(inc)

    def reorder_group(self, inc):
        sel_group = self.middle_selected  # get the list of sorted musics and groups
        ref_list = self.playlist.get_group_sorted_musics(groups=True)

        idx = ref_list.index(
            sel_group
        )  # get the current group index in that list and change it
        old_idxs = {grp: i for i, grp in enumerate(ref_list)}
        new_idx = pygame.math.clamp(idx + inc, 0, len(self.playlist.musiclist) - 1)
        if new_idx == idx:
            return

        ref_list.remove(sel_group)
        ref_list.insert(new_idx, sel_group)  # move the group to that index

        for group in sel_group.playlist.groups:  # move the index of each group to the delta that was created while moving sel_group around
            group.idx += ref_list.index(group) - old_idxs[group]

        for music in (
            sel_group.musics
        ):  # if any music inside the group was playing, reset its index
            if music is self.state.music:
                self.state.music_index = self.playlist.get_group_sorted_musics().index(
                    music
                )
                break

    def reorder_music_nogroup(self, inc):
        music = self.middle_selected  # get the list of sorted musics and groups
        ref_list = self.playlist.get_group_sorted_musics(groups=True)

        r_idx = self.playlist.musiclist.index(
            music
        )  # remember the old index in the music list
        idx = ref_list.index(
            music
        )  # this is the index in the sorted music and group list
        new_idx = pygame.math.clamp(idx + inc, 0, len(ref_list) - 1)
        r_newidx = r_idx + inc  # change both indexes
        if new_idx == idx:
            return

        ref_list.remove(music)  # move the music in the sorted list
        ref_list.insert(new_idx, music)
        changed = False

        for group in self.playlist.groups:  # for each group, check if it moved around while the music was moving, in that case modify its index
            if len(group.musics) <= 0:
                continue
            prev = group.idx
            group.idx = ref_list.index(group)
            if prev != group.idx:
                changed = True
                break

        if not changed:
            self.playlist.musiclist.remove(
                music
            )  # if no group moved modify its index in the original list
            self.playlist.musiclist.insert(r_newidx, music)

    def reorder_music_group(self, inc):
        music = self.middle_selected
        idx = music.group.musics.index(music)
        new_idx = pygame.math.clamp(idx + inc, 0, len(music.group.musics) - 1)
        if new_idx == idx:
            return

        music.group.musics.remove(music)
        music.group.musics.insert(new_idx, music)

    def event(self, event):
        modal_exit = False
        if self.modal_state == "add":
            modal_exit = self.playlist_add.event(event)
        elif self.modal_state == "move":
            modal_exit = self.move_music.event(event)
        elif self.modal_state == "add_group":
            modal_exit = self.add_to_group.event(event)
        elif self.modal_state == "cover":
            modal_exit = self.change_cover.event(event)
        elif self.modal_state == "rename":
            modal_exit = self.rename_music.event(event)
        elif self.modal_state == "rename_group":
            modal_exit = self.rename_group.event(event)
        elif self.modal_state == "metadata":
            modal_exit = self.music_metadata.event(event)
        if (
            self.search_active
            and self.app.can_interact()
            and self.modal_state == "none"
            and self.app.modal_state == "none"
        ):
            self.search_entryline.event(event)
        if (
            self.playlist.is_yt
            and self.app.can_interact()
            and self.modal_state == "none"
            and self.app.modal_state == "none"
        ):
            self.link_entryline.event(event)
        if event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_MIDDLE:
            self.middle_selected = None
        if (
            event.type == pygame.MOUSEWHEEL
            and self.modal_state == "none"
            and self.app.modal_state == "none"
        ):
            if self.middle_selected is not None:
                self.reorder_musics_groups(event)
            else:
                handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)

        if self.app.listening_key or not self.app.can_interact():
            return
        if event.type == pygame.KEYDOWN:
            self.shortcuts_event(event, modal_exit)

    def shortcuts_event(self, event, modal_exit):
        if not modal_exit and event.key == pygame.K_ESCAPE:
            if self.search_active:
                self.stop_searching()
            else:
                self.back()
        elif Keybinds.check("toggle_search", event):
            if self.search_active:
                self.stop_searching()
            else:
                self.action_search()
