import mili
import pygame
import pathlib
import platform
import threading
import subprocess
from ui.common import *
import moviepy.editor as moviepy
from ui.data import convert_music_async
from ui.data import Playlist, MusicData, PlaylistGroup
from ui.playlist_add import PlaylistAddUI
from ui.entryline import UIEntryline
from ui.move_music import MoveMusicUI
from ui.add_to_group import AddToGroupUI
from ui.change_cover import ChangeCoverUI
from ui.rename_music import RenameMusicUI
from ui.rename_group import RenameGroupUI


class PlaylistViewerUI(UIComponent):
    def init(self):
        self.playlist: Playlist = None
        self.anim_add_music = animation(-5)
        self.anim_cover = animation(-5)
        self.anim_back = animation(-3)
        self.anim_search = animation(-5)
        self.menu_anims = [animation(-4) for i in range(9)]
        self.modal_state = "none"
        self.middle_selected: MusicData | PlaylistGroup = None
        self.search_active = False
        self.search_entryline = UIEntryline("Enter search...", False)
        self.big_cover = False
        self.big_cover_time = 0

        self.playlist_add = PlaylistAddUI(self.app)
        self.change_cover = ChangeCoverUI(self.app)
        self.rename_music = RenameMusicUI(self.app)
        self.rename_group = RenameGroupUI(self.app)
        self.move_music = MoveMusicUI(self.app)
        self.add_to_group = AddToGroupUI(self.app)

        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, 8, 3, 3, 0, "y")
        self.sbar_size = self.scrollbar.short_size
        self.cover_cache = mili.ImageCache()
        self.bigcover_cache = mili.ImageCache()
        self.black_cache = mili.ImageCache()

        self.change_cover_image = load_icon("cover")
        self.forward_image = load_icon("forward")
        self.search_image = load_icon("search")
        self.searchoff_image = load_icon("searchoff")
        self.backspace_image = load_icon("backspace")
        self.convert_image = load_icon("convert")
        self.up_image = load_icon("up")
        self.down_image = load_icon("down")
        self.remove_image = load_icon("playlist_remove")
        self.rows_image = load_icon("rows")
        self.columns_image = load_icon("columns")

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

    def ui_top_buttons(self):
        if self.app.modal_state != "none" or self.modal_state != "none":
            return
        self.ui_overlay_top_btn(
            self.anim_back, self.back, self.app.back_image, "left", tooltip="Back"
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

    def ui(self):
        self.ui_check()
        if self.modal_state == "none" and self.app.modal_state == "none":
            handle_arrow_scroll(self.app, self.scroll, self.scrollbar)

        if self.search_active:
            self.search_entryline.update(self.app)
        self.scrollbar.short_size = self.mult(8)
        if self.playlist is None:
            self.back()
        big_cover = self.ui_title()
        if big_cover and not self.big_cover:
            self.big_cover = True
            self.big_cover_time = pygame.time.get_ticks()
        if not big_cover:
            self.big_cover = False
        self.ui_container()

        if self.modal_state == "none" and self.app.modal_state == "none":
            self.ui_overlay_btn(
                self.anim_add_music,
                self.action_add_music,
                self.app.playlistadd_image,
                "top",
                tooltip="Add a track or a group",
            )
            self.ui_overlay_btn(
                self.anim_cover,
                self.action_cover,
                self.change_cover_image,
                "supertop",
                tooltip="Change the playlist cover",
            )
            self.ui_overlay_btn(
                self.anim_search,
                self.action_search,
                self.searchoff_image if self.search_active else self.search_image,
                "megatop",
                tooltip="Disable search" if self.search_active else "Enable search",
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

        if (
            big_cover
            and pygame.time.get_ticks() - self.big_cover_time >= BIG_COVER_COOLDOWN
        ):
            self.ui_big_cover()

    def ui_container(self):
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
                self.scrollbar.short_size = self.mult(self.sbar_size)
                self.scrollbar.update(scroll_cont)

                self.ui_scrollbar()
                self.mili.id_checkpoint(50)
                done_groups = []
                last_group = None
                off_screen = False

                for group in self.playlist.groups:
                    if len(group.musics) <= 0 and not self.search_active:
                        self.ui_group(group, empty=True)

                for path in paths:
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
                    off_screen = self.ui_music(music, off_screen)

                self.mili.text_element(
                    f"{len(self.playlist.musiclist)} track{
                        "s" if len(self.playlist.musiclist) > 1 else ""}",
                    {"size": self.mult(19), "color": (170,) * 3},
                    None,
                    {"offset": self.scroll.get_offset(), "blocking": None},
                )

            else:
                self.mili.text_element(
                    "No track matches your search"
                    if self.search_active
                    else "No tracks",
                    {"size": self.mult(20), "color": (200,) * 3},
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
                "resizey": {
                    "min": self.mult(40),
                },
                "spacing": -self.mult(3),
            },
        ) as cont:
            self.ui_group_bg(group, empty, cont)
            if empty:
                self.mili.element((0, 0, self.mult(35), 0), {"blocking": None})
            else:
                self.mili.image_element(
                    (
                        self.app.playbars_image
                        if self.app.music is not None and self.app.music.group is group
                        else self.down_image
                    )
                    if group.collapsed
                    else self.up_image,
                    {
                        "cache": mili.ImageCache.get_next_cache(),
                        "padx": self.mult(5)
                        if (
                            self.app.music is not None
                            and self.app.music.group is group
                            and group.collapsed
                        )
                        else 0,
                    },
                    (0, 0, self.mult(35), self.mult(35)),
                    {"blocking": False, "align": "center"},
                )
            self.mili.text_element(
                f"{group.name}{" (empty)" if empty else ""}",
                {
                    "size": self.mult(18.5),
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
                        (
                            self.app.rename_image,
                            self.action_rename_group,
                            self.menu_anims[-3],
                            "Rename group",
                        ),
                        (
                            self.columns_image
                            if group.mode == "v"
                            else self.rows_image,
                            self.action_group_mode,
                            self.menu_anims[-2],
                            "30",
                            "View group tracks in columns"
                            if group.mode == "v"
                            else "View group tracks in rows",
                        ),
                        (
                            self.app.delete_image,
                            self.action_delete_group,
                            self.menu_anims[-1],
                            "Delete group",
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
        if self.app.bg_effect:
            self.mili.image(
                SURF,
                {
                    "fill": True,
                    "fill_color": (
                        *(color),
                        ALPHA,
                    ),
                    "border_radius": "5",
                    "cache": mili.ImageCache.get_next_cache(),
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
            f"'{parse_music_stem(self.app, music.realstem)}' is being converted...",
            {
                "size": self.mult(16),
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
            if self.search_active:
                self.ui_search()
        self.mili.line_element(
            [("-49.5", 0), ("49.5", 0)],
            {"size": 1, "color": (100,) * 3},
            (0, 0, 0, self.mult(7)),
            {"fillx": True, "blocking": None},
        )
        return ret

    def ui_search(self):
        with self.mili.begin(
            (0, 0, self.app.split_w - self.mult(20), 0),
            {"resizey": True, "blocking": None} | mili.PADLESS | mili.X,
        ):
            size = self.mult(30)
            self.search_entryline.ui(
                self.mili,
                (0, 0, 0, size),
                {"fillx": True},
                self.mult,
                CONTROLS_CV[0] + 5,
                CONTROLS_CV[1],
            )
            if it := self.mili.element((0, 0, size, size)):
                self.mili.rect(
                    {
                        "color": (cond(self.app, it, *OVERLAY_CV),) * 3,
                        "border_radius": 0,
                    }
                )
                self.mili.image(
                    self.backspace_image, {"cache": mili.ImageCache.get_next_cache()}
                )
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
            {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.black_cache},
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
        w = self.mili.text_size(self.playlist.name, {"size": self.mult(32)}).x
        if w >= self.app.split_w / 1.08 - coversize:
            self.mili.text_element(
                self.playlist.name,
                {
                    "size": self.mult(32),
                    "slow_grow": True,
                    "wraplen": self.app.split_w / 1.08 - coversize,
                    "align": "left",
                },
                None,
                {"align": "center", "blocking": None},
            )
        else:
            self.mili.text_element(
                self.playlist.name,
                {
                    "size": self.mult(32),
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
                        self.ui_music_bg(mit, music)
                        is_current = False
                        cover = music.cover_or(self.app.music_cover_image)
                        if cover is None:
                            cover = self.app.music_cover_image
                        if (
                            music is self.app.music
                            and self.app.music_controls.music_videoclip_cover
                            is not None
                            and self.app.focused
                        ):
                            cover = self.app.music_controls.music_videoclip_cover
                            is_current = True
                        if cover is not None:
                            scaled = False
                            if (
                                is_current
                                and (av := self.app.music_controls.async_videoclip)
                                is not None
                            ):
                                if mit.data.rect.size in av.scaled_output:
                                    cover = av.scaled_output[mit.data.rect.size]
                                    scaled = True
                            self.mili.image(
                                cover,
                                {
                                    "cache": mili.ImageCache.get_next_cache(),
                                    "pad": self.mult(3),
                                    "ready": scaled,
                                },
                            )
                            if is_current:
                                self.app.music_controls.videoclip_rects.append(
                                    (self.mult(3), mit.data.rect)
                                )
                        if music is self.app.music:
                            self.mili.image(
                                self.app.playbars_image,
                                {
                                    "cache": mili.ImageCache.get_next_cache(),
                                    "pad": "30",
                                },
                            )
                        self.ui_music_interaction(music, mit)
                        if self.app.can_interact() and mit.hovered:
                            self.app.tick_tooltip(
                                f"{parse_music_stem(self.app, music.realstem)}"
                            )

    def ui_music(self, music: MusicData, offscreen=False):
        if offscreen:
            self.mili.element((0, 0, 0, self.mult(80)), {"blocking": False})
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
                "resizey": {"min": self.mult(80)},
            },
        ) as cont:
            if cont.data.absolute_rect.colliderect(((0, 0), self.app.split_size)):
                self.ui_music_bg(cont, music)
                imagesize = padsize = 0
                if (
                    music.group is not None and not self.search_active
                ) or music is self.app.music:
                    padsize = self.mult(30)
                    self.mili.element(
                        (0, 0, padsize, 0), {"filly": True, "blocking": False}
                    )
                    if music is self.app.music:
                        self.mili.image(
                            self.app.playbars_image,
                            {"cache": mili.ImageCache.get_next_cache()},
                        )
                cover = music.cover_or(self.app.music_cover_image)
                is_current = False
                if cover is None:
                    cover = self.app.music_cover_image
                if (
                    music is self.app.music
                    and self.app.music_controls.music_videoclip_cover is not None
                    and self.app.focused
                ):
                    cover = self.app.music_controls.music_videoclip_cover
                    is_current = True
                if cover is not None:
                    imagesize = self.mult(70)
                    cel = self.mili.element(
                        (0, 0, imagesize, imagesize),
                        {"align": "center", "blocking": False},
                    )
                    scaled = False
                    if is_current:
                        self.app.music_controls.videoclip_rects.append(
                            (0, cel.data.rect)
                        )

                        if (av := self.app.music_controls.async_videoclip) is not None:
                            if cel.data.rect.size in av.scaled_output:
                                cover = av.scaled_output[cel.data.rect.size]
                                scaled = True
                    self.mili.image(
                        cover,
                        {"cache": mili.ImageCache.get_next_cache(), "ready": scaled},
                    )
                self.mili.text_element(
                    parse_music_stem(self.app, music.realstem),
                    {
                        "size": self.mult(18),
                        "growx": False,
                        "growy": True,
                        "slow_grow": True,
                        "wraplen": "100",
                        "font_align": pygame.FONT_LEFT,
                        "align": "topleft",
                    },
                    (
                        0,
                        0,
                        self.app.split_w / 1.1 - imagesize - padsize,
                        self.mult(80) / 1.1,
                    ),
                    {"align": "first", "blocking": False},
                )
                self.ui_music_interaction(music, cont)
            else:
                self.mili.element((0, 0, 0, self.mult(70)), {"blocking": False})
                if cont.data.absolute_rect.top > self.app.window.size[1]:
                    offscreen = True
        return offscreen

    def ui_music_interaction(self, music: MusicData, cont: mili.Interaction):
        if self.app.can_interact():
            if cont.hovered or cont.unhover_pressed:
                self.app.cursor_hover = True
            if cont.left_just_released:
                self.action_start_playing(music)
            elif cont.just_released_button == pygame.BUTTON_RIGHT:
                self.open_menu(music)
            elif cont.just_pressed_button == pygame.BUTTON_MIDDLE:
                self.middle_selected = music

    def ui_music_bg(self, cont, music):
        forcehover = (
            self.app.music == music
            or (self.app.menu_data == music and self.app.menu_open)
            or self.middle_selected == music
        )
        color = MUSIC_CV[1] if forcehover else cond(self.app, cont, *MUSIC_CV)
        if self.app.bg_effect:
            self.mili.image(
                SURF,
                {
                    "fill": True,
                    "fill_color": (
                        *((color,) * 3),
                        ALPHA,
                    ),
                    "border_radius": 0,
                    "cache": mili.ImageCache.get_next_cache(),
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

    def open_menu(self, music: MusicData):
        buttons = [
            (
                self.app.rename_image,
                self.action_rename,
                self.menu_anims[1],
                "Rename track",
            ),
            (
                self.forward_image,
                self.action_forward,
                self.menu_anims[2],
                "Move track to playlist",
            ),
            (
                self.app.music_controls.minip_image,
                self.action_show_in_explorer,
                self.menu_anims[3],
                "30",
                "Show in explorer",
            ),
        ]
        if len(self.playlist.groups) > 0:
            buttons.insert(
                0,
                (
                    (
                        self.app.playlistadd_image
                        if music.group is None
                        else self.remove_image
                    ),
                    (
                        self.action_add_to_group
                        if music.group is None
                        else self.action_remove_from_group
                    ),
                    self.menu_anims[0],
                    "Add to group" if music.group is None else "Remove from group",
                ),
            )
        if (
            music.realpath.suffix != ".mp3"
            and not music.isvideo
            and not music.converted
            and not music.isconvertible
        ):
            buttons.append(
                (
                    self.convert_image,
                    self.action_convert,
                    self.menu_anims[4],
                    "30",
                    "Convert to MP3",
                )
            )
        buttons.append(
            (
                self.app.delete_image,
                self.action_delete,
                self.menu_anims[5],
                "Delete track",
            ),
        )
        self.app.open_menu(music, *buttons)

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

    def action_remove_from_group(self):
        self.app.menu_data.group.remove(self.app.menu_data)
        if self.app.menu_data is self.app.music:
            self.app.music_index = self.playlist.get_group_sorted_musics().index(
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
            f"data/mp3_converted/{self.playlist.name}_{music.realstem}.mp3"
        ).resolve()
        if os.path.exists(new_path):
            self.app.close_menu()
            if music is self.app.music:
                self.app.end_music()
            music.converted = True
            return

        try:
            audiofile = moviepy.AudioFileClip(str(music.realpath))
        except Exception as exc:
            pygame.display.message_box(
                "Could not convert music",
                f"Could not convert '{music.realpath}' to MP3 due to external exception: '{exc}'.",
                "error",
                None,
                ("Understood",),
            )
            return

        self.app.close_menu()
        if music is self.app.music:
            self.app.end_music()

        music.audiofile = audiofile
        music.pending = True
        music.audio_converting = True
        music.load_exc = None
        music.audiopath = new_path
        music.playlist.musictable.pop(music.realpath)
        music.playlist.musictable[music.audiopath] = music
        thread = threading.Thread(
            target=convert_music_async, args=(music, audiofile, new_path)
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

    def action_add_music(self):
        self.modal_state = "add"

    def back(self):
        self.app.change_state("list")
        self.scroll.set_scroll(0, 0)
        self.scrollbar.scroll_moved()

    def action_rename(self):
        self.modal_state = "rename"
        self.rename_music.music = self.app.menu_data
        self.rename_music.entryline.text = self.rename_music.music.realstem
        self.rename_music.entryline.cursor = len(self.rename_music.entryline.text)
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
            if self.app.menu_data == self.app.music:
                self.app.end_music()
            self.app.remove_from_history(self.app.menu_data)
            path = self.app.menu_data.audiopath
            self.playlist.remove(path)
            if btn == 1:
                mp3_path = f"data/mp3_converted/{self.playlist.name}_{self.app.menu_data.realstem}.mp3"
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
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
            if music is self.app.music:
                musictochangeindex = music
        if musictochangeindex is not None:
            self.app.music_index = self.playlist.get_group_sorted_musics().index(
                musictochangeindex
            )
        self.playlist.groups.remove(self.app.menu_data)
        self.app.close_menu()

    def action_start_playing(self, music: MusicData):
        self.app.play_music(
            music, music.playlist.get_group_sorted_musics().index(music)
        )

    def stop_searching(self):
        self.search_active = False
        self.search_entryline.text = ""

    def set_scroll_to_music(self, increase=False, incdir=1):
        if self.app.music.group is not None:
            self.app.music.group.collapsed = False
        if increase:
            self.scroll.scroll(0, (self.mult(80) + 6) * incdir)
            self.scrollbar.scroll_moved()
            return
        remove_amount = 0
        group_amount = 0
        line_amount = 0
        for group in self.app.music.playlist.groups:
            if len(group.musics) <= 0:
                group_amount += 1
            else:
                if group.idx <= self.app.music_index or group is self.app.music.group:
                    group_amount += 1
                    if group.collapsed:
                        remove_amount += len(group.musics)
                    elif group.mode == "h":
                        remove_amount += len(group.musics) - 1
                    elif group.idx < self.app.music_index:
                        line_amount += 1
        self.scroll.set_scroll(
            0,
            (
                ((self.app.music_index - 1) * (self.mult(80) + 3))
                - (remove_amount * (self.mult(80) + 3))
                + (group_amount * (self.mult(45) + 3))
                + (line_amount * (self.mult(7) + 3))
            ),
        )
        self.scrollbar.scroll_moved()

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

            if self.middle_selected is self.app.music:
                self.app.music_index = self.playlist.get_group_sorted_musics().index(
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
            if music is self.app.music:
                self.app.music_index = self.playlist.get_group_sorted_musics().index(
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
        if (
            self.search_active
            and self.app.can_interact()
            and self.modal_state == "none"
        ):
            self.search_entryline.event(event)
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

        self.shortcuts_event(event, modal_exit)

    def shortcuts_event(self, event, modal_exit):
        if self.app.listening_key or not self.app.can_interact():
            return
        if event.type == pygame.KEYDOWN:
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
            elif Keybinds.check("change_cover", event):
                if self.modal_state == "cover":
                    self.change_cover.close()
                else:
                    self.action_cover()
