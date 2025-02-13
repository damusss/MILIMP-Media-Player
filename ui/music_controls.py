import mili
import pygame
import random
import pathlib
from ui.common import *

from ui.common.data import NotCached, AsyncVideoclipGetter
from ui.extra.miniplayer import MiniplayerUI


class MusicControlsUI(UIComponent):
    def init(self):
        self.minip = MiniplayerUI(self.app)
        self.img_cache = mili.ImageCache()
        self.main_cont = None
        self.offset = 0
        self.offset_restart_time = pygame.time.get_ticks()
        self.cont_height = 0
        self.small_cont = True
        self.anims = [animation(-3) for i in range(11)]
        self.overlay_anims = [animation(-3) for i in range(5)]
        self.handle_anim = animation(-10)
        self.slider = mili.Slider({"lock_y": True, "handle_size": 30})
        self.bigcover_cache = mili.ImageCache()
        self.black_cache = mili.ImageCache()
        self.split_screen_cache = mili.ImageCache()
        self.cover_cache = mili.ImageCache()
        self.music_videoclip_cover = None
        self.last_videoclip_cover = None
        self.timebar_controlled = False
        self.timebar_pos = None
        self.handle_percentage = None
        self.big_cover = False
        self.bigcover_time = 0
        self.dots_rect = None
        self.super_fullscreen = False
        self.width = 0
        self.track_hover_pos = None
        self.async_videoclip: AsyncVideoclipGetter = None
        self.videoclip_rects = []
        self.clean_ui = False
        self.slider_hovered = False

    def ui(self):
        if self.app.split_screen:
            self.width = (
                1 - (self.app.split_w / self.app.window.size[0])
            ) * self.app.window.size[0]
        else:
            self.width = self.app.split_w
        if self.app.modal_state != "fullscreen" and self.super_fullscreen:
            self.super_fullscreen = False
        self.cont_height = 0
        if self.app.music is None:
            return

        if (
            self.app.menu_open
            and self.app.menu_data == "controls"
            and self.dots_rect is not None
        ):
            self.app.menu_pos = self.get_menu_pos(self.app.menu_buttons)

        self.get_videoclip_cover()
        self.get_bg_effect()

        if (
            self.app.custom_borders.resizing
            or self.super_fullscreen
            or (
                self.clean_ui
                and (self.app.split_screen or self.app.modal_state == "fullscreen")
            )
        ):
            self.minip.run()
            return

        if self.app.music_paused:
            self.app.music_play_time += self.app.delta_time * 1000
        self.small_cont = (
            self.main_cont is None
            or (not self.main_cont.data.absolute_rect.collidepoint(
                pygame.mouse.get_pos()
            ) and not self.slider_hovered)
        )
        self.slider_hovered = False
        contheight = self.mult(100 if self.small_cont else 116)
        bigcover = False

        self.cont_height = contheight
        with self.mili.begin(
            (0, 0, self.width, contheight),
            {"axis": "x", "pady": 0},
        ) as self.main_cont:
            self.mili.rect({"color": (MUSICC_CV,) * 3})
            if self.app.modal_state != "fullscreen" and not self.app.split_screen:
                bigcover = self.ui_cover()
            self.ui_controls_cont()

        self.ui_track_control()

        if bigcover:
            if not self.big_cover:
                self.big_cover = True
                self.bigcover_time = pygame.time.get_ticks()
        else:
            self.big_cover = False

        if (
            bigcover
            and pygame.time.get_ticks() - self.bigcover_time >= BIG_COVER_COOLDOWN
        ):
            self.ui_big_cover()

        if self.app.split_screen:
            self.ui_split_screen_btns()

        self.minip.run()

    def ui_split_screen(self):
        if self.app.music is None:
            return
        with self.mili.begin(
            None,
            mili.PADLESS | {"filly": True, "fillx": True, "blocking": None},
        ):
            cover = ICONS.music_cover
            if self.app.music.cover is not None:
                cover = self.app.music.cover
            if (
                self.music_videoclip_cover is not None
                and self.app.focused
            ):
                cover = self.music_videoclip_cover
            if cover is None:
                return
            else:
                it = self.mili.element(
                    (
                        0,
                        0,
                        0,
                        self.app.window.size[1]
                        - self.cont_height
                        - self.app.tbarh,
                    ),
                    {"fillx": True},
                )
                current = (
                    self.app.focused
                    and not self.app.music_paused
                    and self.music_videoclip_cover is not None
                )
                if current:
                    self.videoclip_rects.append((0, it.data.rect))
                scaled = False
                if self.async_videoclip is not None and current:
                    if it.data.rect.size in self.async_videoclip.scaled_output:
                        cover = self.async_videoclip.scaled_output[it.data.rect.size]
                        scaled = True
                self.mili.image(
                    cover,
                    {"cache": self.cover_cache, "ready": scaled} | mili.PADLESS,
                )
                if it.left_just_released:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        if (
                            self.app.view_state != "playlist"
                            or self.app.playlist_viewer.playlist
                            is not self.app.music.playlist
                        ):
                            self.app.playlist_viewer.enter(self.app.music.playlist)
                        self.app.playlist_viewer.set_scroll_to_music()
                    else:
                        self.clean_ui = False
                elif (
                    it.just_released_button == pygame.BUTTON_MIDDLE
                    and self.music_videoclip_cover is not None
                    and pygame.key.get_mods() & pygame.KMOD_CTRL
                ):
                    self.app.music.cover = self.music_videoclip_cover.copy()
                    pygame.image.save(
                        self.app.music.cover,
                        f"data/music_covers/{self.app.music.playlist.name}_{self.app.music.realstem}.png",
                    )

    def ui_cover(self):
        bigcover = False
        imgsize = 0
        cover = self.app.music.cover
        if self.music_videoclip_cover is not None and self.app.focused:
            cover = self.music_videoclip_cover
        if cover is not None:
            imgsize = self.mult(90)
            it = self.mili.image_element(
                cover,
                {
                    "cache": self.img_cache,
                    "pady": self.mult(5),
                    "smoothscale": True,
                },
                (0, 0, imgsize, imgsize),
                {"align": "first", "blocking": True},
            )
            if self.app.can_interact():
                if it.left_just_released:
                    if (
                        self.app.view_state != "playlist"
                        or self.app.playlist_viewer.playlist
                        is not self.app.music.playlist
                    ):
                        self.app.playlist_viewer.enter(self.app.music.playlist)
                    self.app.playlist_viewer.set_scroll_to_music()
                elif (
                    it.just_released_button == pygame.BUTTON_MIDDLE
                    and self.music_videoclip_cover is not None
                ):
                    self.app.music.cover = self.music_videoclip_cover.copy()
                    pygame.image.save(
                        self.app.music.cover,
                        f"data/music_covers/{self.app.music.playlist.name}_{self.app.music.realstem}.png",
                    )
                if it.absolute_hover:
                    bigcover = True
                    self.app.cursor_hover = True
                    self.app.tick_tooltip("Jump to the track in the playlist")
        else:
            self.mili.element(None, {"blocking": None})
        return bigcover

    def ui_track_control(self):
        if self.app.music.pos_supported and self.app.music.duration not in [
            None,
            NotCached,
        ]:
            if self.small_cont:
                self.ui_small_slider()
            else:
                self.ui_slider()
                self.ui_time()
        elif not self.small_cont:
            self.mili.text_element(
                "Audio format does not support track positioning",
                {"color": (150,) * 3, "size": self.mult(18)},
                pygame.Rect(0, 0, self.width, 0).move_to(
                    bottomleft=(
                        0,
                        self.app.window.size[1] - self.mult(32),
                    )
                ),
                {"ignore_grid": True, "parent_id": 0, "z": 9999, "blocking": None},
            )

    def ui_time(self):
        pos = self.app.get_music_pos()
        txt, txtstyle = (
            format_music_time(pos, self.app.music.duration),
            {"color": (120,) * 3, "size": self.mult(20)},
        )
        size = self.mili.text_size(txt, txtstyle)
        xoffset = self.app.split_w if self.app.split_screen else 0
        self.mili.text_element(
            txt,
            txtstyle,
            pygame.Rect(0, 0, size.x, size.y).move_to(
                bottomright=(
                    self.width - self.mult(8) + xoffset,
                    self.app.window.size[1] - self.mult(17),
                )
            ),
            {"ignore_grid": True, "z": 9999, "parent_id": 0, "blocking": None},
        )

    def ui_small_slider(self):
        xoffset = self.app.split_w if self.app.split_screen else 0
        totalw = self.width - self.mult(15)
        pos = self.app.get_music_pos()
        percentage = (pos) / self.app.music.duration

        if percentage > 1.01:
            self.music_auto_finish()
            return

        self.slider.valuex = percentage
        sizeperc = totalw * percentage
        self.mili.line_element(
            [(-totalw / 2, 0), (totalw / 2, 0)],
            {"color": (50,) * 3, "size": self.mult(3)},
            pygame.Rect(0, 0, totalw, 2).move_to(
                midbottom=(
                    xoffset + self.width / 2,
                    self.app.window.size[1] - self.mult(6),
                )
            ),
            {"ignore_grid": True, "parent_id": 0, "z": 99999, "blocking": None},
        )
        self.mili.line_element(
            [(-totalw / 2, 0), (-totalw / 2 + sizeperc, 0)],
            {"color": (255, 0, 0), "size": self.mult(3)},
            pygame.Rect(0, 0, totalw, 2).move_to(
                midbottom=(
                    xoffset + self.width / 2,
                    self.app.window.size[1] - self.mult(6),
                )
            ),
            {"ignore_grid": True, "parent_id": 0, "z": 99999, "blocking": None},
        )

    def ui_slider(self):
        xoffset = self.app.split_w if self.app.split_screen else 0
        self.slider.style["handle_size"] = (self.mult(48), self.mult(48))
        totalw = self.width - self.mult(15)
        pos = self.app.get_music_pos()
        percentage = (pos) / self.app.music.duration
        if self.timebar_pos is not None:
            percentage = self.timebar_pos

        if percentage > 1.01 and self.timebar_pos is None:
            self.music_auto_finish()
            return

        sizeperc = totalw * min(1, self.slider.valuex)
        with self.mili.begin(
            pygame.Rect(0, 0, totalw, self.mult(5)).move_to(
                midbottom=(
                    xoffset + self.width / 2,
                    self.app.window.size[1] - self.mult(10),
                )
            ),
            self.slider.area_style | {"ignore_grid": True, "parent_id": 0, "z": 9999},
        ) as sbar:
            self.slider.update_area(sbar)
            self.mili.rect({"color": (30,) * 3})

            redbar = self.mili.rect_element(
                {"color": (255, 0, 0)},
                (0, 0, sizeperc, self.mult(5)),
                {"ignore_grid": True},
            )

            handle = self.ui_slider_handle(percentage)
            mpressed = pygame.mouse.get_pressed()[0]
            if not self.timebar_controlled:
                if (
                    not handle.absolute_hover
                    and self.app.can_interact()
                    and sbar.absolute_hover
                    and mpressed
                ):
                    self.timebar_controlled = True
                    self.handle_anim.goto_b()
            else:
                if not mpressed:
                    self.timebar_controlled = False
                    if self.timebar_pos is not None:
                        self.app.set_music_pos(
                            self.timebar_pos * self.app.music.duration
                        )
                    self.timebar_pos = None

            if self.timebar_controlled:
                mposx = pygame.mouse.get_pos()[0]
                relmpos = mposx - sbar.data.absolute_rect.x
                newpos = pygame.math.clamp(relmpos / sbar.data.absolute_rect.w, 0, 1)
                self.timebar_pos = newpos
                self.slider.valuex = newpos
                self.app.cursor_hover = True
            elif sbar.absolute_hover:
                self.app.cursor_hover = True

            if (
                sbar.hovered
                or handle.hovered
                or sbar.unhover_pressed
                or handle.unhover_pressed
                or self.timebar_controlled
                or redbar.hovered
            ):
                self.ui_slider_hovered_time(sbar, handle)
            else:
                self.track_hover_pos = None

    def ui_slider_hovered_time(self, sbar: mili.Interaction, handle: mili.Interaction):
        hperc = (
            pygame.mouse.get_pos()[0] - sbar.data.absolute_rect.x
        ) / sbar.data.rect.w
        music_pos = self.app.music.duration * hperc
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            self.track_hover_pos = music_pos
        else:
            self.track_hover_pos = None
        hpostxt = format_music_time(self.app.music.duration * hperc, None)
        txtstyle = {"size": self.mult(18), "color": (120,) * 3, "pady": 2}
        txtsize = self.mili.text_size(hpostxt, txtstyle) + pygame.Vector2(6, 4)
        if self.mili.element(
            pygame.Rect((0, 0), txtsize).move_to(
                midbottom=(
                    pygame.mouse.get_pos()[0],
                    sbar.data.absolute_rect.top
                    - self.mult(8.5 if handle.hovered else 2),
                )
            ),
            mili.FLOATING | {"blocking": None, "z": 999999},
        ):
            self.mili.rect({"color": (10,) * 3, "border_radius": 0})
            self.mili.text(
                hpostxt,
                txtstyle,
            )
            self.mili.rect({"color": (30,) * 3, "outline": 1, "border_radius": 0})

    def ui_slider_handle(self, percentage):
        if handle := self.mili.element(
            self.slider.handle_rect,
            self.slider.handle_style | {"z": 99999},
        ):
            self.slider.update_handle(handle)
            self.slider_hovered = handle.hovered or handle.left_pressed
            self.mili.circle(
                {
                    "color": (255,) * 3,
                    "pad": str((75 + self.handle_anim.value) / 2),
                }
            )
            if not self.timebar_controlled:
                if handle.left_just_released and self.app.can_interact():
                    self.app.set_music_pos(self.slider.valuex * self.app.music.duration)
                if not handle.left_pressed:
                    self.slider.valuex = percentage
                    self.handle_percentage = None
                else:
                    self.handle_percentage = self.slider.valuex
                if handle.just_hovered and self.app.can_interact():
                    self.handle_anim.goto_b()
                if handle.just_unhovered:
                    self.handle_anim.goto_a()
                if handle.hovered or handle.unhover_pressed:
                    self.app.cursor_hover = True
                    self.app.tick_tooltip(None)
        return handle

    def ui_controls_cont(self):
        with self.mili.begin(
            (0, 0, 0, self.cont_height),
            {"fillx": True, "pady": 0, "spacing": 0},
        ) as cont:
            txt, txtstyle = (
                f"{parse_music_stem(self.app, self.app.music.realstem)}",
                {"size": self.mult(22), "align": "left"},
            )
            size = self.mili.text_size(txt, txtstyle).x
            diff = size - cont.data.rect.w
            if not self.app.focused:
                self.offset = 0
                self.offset_restart_time = pygame.time.get_ticks()
            else:
                if diff > 0:
                    if pygame.time.get_ticks() - self.offset_restart_time >= 2500:
                        self.offset += self.app.delta_time * 30
                    if self.offset > diff + self.width / 3:
                        self.offset = 0
                        self.offset_restart_time = pygame.time.get_ticks()
                else:
                    self.offset = 0
            self.mili.text_element(
                txt,
                txtstyle,
                None,
                {
                    "align": "center"
                    if (self.app.modal_state == "fullscreen" or self.app.split_screen)
                    and diff <= 0
                    else "first",
                    "offset": (-self.offset, 0),
                    "blocking": None,
                },
            )
            self.ui_main_controls()

    def ui_big_cover(self):
        if self.app.split_screen:
            return
        cover = self.app.music.cover
        if self.music_videoclip_cover is not None:
            cover = self.music_videoclip_cover
        if cover is None or cover is ICONS.music_cover:
            return
        self.mili.image_element(
            SURF,
            {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.black_cache},
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "parent_id": 0, "z": 99999, "blocking": False},
        )
        size = mili.percentage(90, min(self.app.window.size))
        self.mili.image_element(
            cover,
            {"cache": self.bigcover_cache, "smoothscale": True},
            pygame.Rect(0, 0, size, size).move_to(
                center=(
                    self.width / 2,
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

    def ui_main_controls(self):
        with self.mili.begin(
            None,
            {
                "resizex": True,
                "resizey": True,
                "align": "center",
                "axis": "x",
                "clip_draw": False,
                "offset": (0, -self.mult(5)),
                "blocking": None,
            },
        ):
            if not self.app.split_screen:
                self.ui_control_btn(
                    ICONS.dots,
                    self.action_dots,
                    40,
                    0,
                    dots=True,
                    tooltip="Options",
                )
            if self.app.music_index > 0:
                self.ui_control_btn(
                    ICONS.skip_previous,
                    self.action_skip_previous,
                    40,
                    1,
                    tooltip="Skip to previous track",
                )
            self.ui_control_btn(
                ICONS.back5,
                self.action_backwards_5,
                40,
                2,
                True,
                tooltip="Back 5 seconds",
            )
            self.ui_control_btn(
                ICONS.play if self.app.music_paused else ICONS.pause,
                self.action_play,
                50,
                3,
                tooltip="Resume music" if self.app.music_paused else "Pause music",
            )
            self.ui_control_btn(
                ICONS.skip5,
                self.action_forward_5,
                40,
                4,
                True,
                tooltip="Forward 5 seconds",
            )
            if self.app.music_index < len(self.app.music.playlist.musiclist) - 1:
                self.ui_control_btn(
                    ICONS.skip_next,
                    self.action_skip_next,
                    40,
                    5,
                    tooltip="Skip to next track",
                )

    def ui_control_btn(
        self, image, action, size, animi, special=False, dots=False, tooltip=None
    ):
        anim: mili.animation.ABAnimation = self.anims[animi]
        if it := self.mili.element(
            (0, 0, self.mult(size), self.mult(size)),
            {"align": "center", "clip_draw": False},
        ):
            if dots:
                self.dots_rect = it.data.absolute_rect
            if (it.hovered or it.unhover_pressed) and self.app.can_interact():
                (self.mili.rect if special else self.mili.circle)(
                    {
                        "color": (cond(self.app, it, *CONTROLS_CV),) * 3,
                        "border_radius": "20",
                        "pad": anim.value / 2,
                    }
                )
                self.app.cursor_hover = True
            if it.hovered and self.app.can_interact():
                self.app.tick_tooltip(tooltip)
            self.mili.image(
                image,
                {
                    "cache": mili.ImageCache.get_next_cache(),
                    "pad": self.mult(1) + anim.value,
                },
            )
            if self.app.can_interact():
                if it.left_just_released:
                    action()
                if it.just_hovered:
                    anim.goto_b()
            if it.just_unhovered:
                anim.goto_a()
            if not it.absolute_hover and not anim.active and anim.value != anim.a:
                anim.goto_a()

    def get_videoclip_cover(self, pos_override=None):
        self.music_videoclip_cover = None
        if self.async_videoclip is None:
            return
        if self.track_hover_pos is not None:
            pos_override = self.track_hover_pos
        if not self.app.focused and self.minip.window is None:
            return
        if self.app.music.duration in [None, NotCached]:
            return
        if self.app.music_paused and not pos_override:
            self.music_videoclip_cover = self.last_videoclip_cover
            return
        if self.app.music_videoclip is not None:
            pos = pos_override if pos_override else self.app.get_music_pos()
            if pos >= self.app.music.duration:
                self.music_videoclip_cover = SURF
                return
            try:
                self.async_videoclip.active = True
                self.async_videoclip.time = pos
                self.async_videoclip.framerate = self.app.target_framerate
                if not self.app.videoclip_threaded:
                    self.async_videoclip.update()
                self.music_videoclip_cover = self.async_videoclip.output
            except Exception:
                return
            self.last_videoclip_cover = self.music_videoclip_cover

    def get_bg_effect(self):
        self.app.bg_effect = False
        if self.app.modal_state == "fullscreen" or self.super_fullscreen:
            return
        if not self.app.focused:
            return
        image = self.app.music.cover
        if self.music_videoclip_cover is not None:
            image = self.music_videoclip_cover
            if self.async_videoclip.small_output is not None:
                image = self.async_videoclip.small_output
        if image is None:
            return
        if self.app.music_paused:
            self.app.bg_effect = True
            return
        color = pygame.Color(pygame.transform.average_color(image))
        color.a = 40
        self.app.bg_effect = True
        self.app.bg_effect_image.fill(color)

    def action_dots(self):
        if self.dots_rect is None:
            return
        if self.app.menu_open:
            self.app.close_menu()
            return
        buttons = [
            (
                ICONS.close,
                self.app.end_music,
                self.anims[6],
                "End music playback",
            ),
            (ICONS.reset, self.action_rewind, self.anims[7], "Rewind track"),
            (
                ICONS.loopon if self.app.music_loops else ICONS.loopoff,
                self.action_loop,
                self.anims[8],
                "15" if self.app.music_loops else "30",
                "Disable track looping"
                if self.app.music_loops
                else "Enable track looping",
            ),
            (
                ICONS.fullscreen,
                self.action_fullscreen
                if self.app.modal_state != "fullscreen"
                else self.action_superfullscreen,
                self.anims[9],
                "30",
                "Enable fullscreen"
                if self.app.modal_state == "fullscreen"
                else "Maximize track",
            ),
            (
                ICONS.minip if self.minip.window is None else ICONS.maxip,
                self.action_miniplayer,
                self.anims[10],
                "35",
                "Open miniplayer" if self.minip.window is None else "Close miniplayer",
            ),
        ]
        self.app.open_menu(
            "controls",
            *buttons,
            pos=self.get_menu_pos(buttons),
        )

    def ui_split_screen_btns(self):
        self.mili.id_checkpoint(10000)
        self.ui_overlay_btn(
            self.overlay_anims[0],
            self.app.end_music,
            ICONS.close,
            0,
            "End music playback",
            True,
        )
        self.ui_overlay_btn(
            self.overlay_anims[1],
            self.action_rewind,
            ICONS.reset,
            1,
            "Rewind track",
            True,
        )
        self.ui_overlay_btn(
            self.overlay_anims[2],
            self.action_loop,
            ICONS.loopon if self.app.music_loops else ICONS.loopoff,
            2,
            "Disable track looping" if self.app.music_loops else "Enable track looping",
            True,
        )
        self.ui_overlay_btn(
            self.overlay_anims[3],
            self.action_fullscreen
            if self.app.modal_state != "fullscreen"
            else self.action_superfullscreen,
            ICONS.fullscreen,
            0,
            "Enable fullscreen"
            if self.app.modal_state == "fullscreen"
            else "Maximize track",
            2,
        )
        self.ui_overlay_btn(
            self.overlay_anims[4],
            self.action_miniplayer,
            ICONS.minip if self.minip.window is None else ICONS.maxip,
            1,
            "Open miniplayer" if self.minip.window is None else "Close miniplayer",
            2,
        )

    def get_menu_pos(self, buttons):
        return (
            min(
                self.dots_rect.right,
                self.app.window.size[0]
                - ((self.mult(40) + 3) * len(buttons) + self.mult(7) * 2),
            ),
            self.dots_rect.centery - (self.mult(40) / 2 + self.mult(7)),
        )

    def action_fullscreen(self):
        self.app.modal_state = "fullscreen"
        self.app.close_menu()

    def action_superfullscreen(self):
        self.super_fullscreen = True
        self.app.close_menu()

    def action_loop(self):
        self.app.music_loops = not self.app.music_loops
        self.app.close_menu()
        if not self.app.split_screen:
            self.action_dots()

    def action_miniplayer(self):
        self.app.close_menu()
        if self.minip.window is None:
            self.minip.open()
        else:
            self.minip.close()

    def action_play(self):
        if self.app.music_paused:
            pygame.mixer.music.unpause()
            self.app.music_paused = False
        else:
            pygame.mixer.music.pause()
            self.app.music_paused = True
        self.app.discord_presence.update()

    def move_pos_5(self, amount):
        if not self.app.music.pos_supported and self.app.music.duration in [
            None,
            NotCached,
        ]:
            return
        pos = self.app.get_music_pos()
        new_pos = pygame.math.clamp(pos + amount, 0, self.app.music.duration)
        if new_pos >= self.app.music.duration:
            self.action_skip_next()
            return
        self.slider.valuex = new_pos / self.app.music.duration
        self.app.set_music_pos(new_pos)
        self.get_videoclip_cover(new_pos)
        self.get_bg_effect()

    def action_forward_5(self):
        self.move_pos_5(5)

    def action_backwards_5(self):
        self.move_pos_5(-5)

    def action_skip_next(self, stop_if_end=False, consider_loop=False):
        if len(self.app.music.playlist.musiclist) <= 0:
            if stop_if_end:
                self.app.end_music()
            return
        new_idx = self.app.music_index + 1
        if new_idx >= len(self.app.music.playlist.musiclist):
            if consider_loop and self.app.loops:
                new_idx = 0
            else:
                if stop_if_end:
                    self.app.end_music()
                return
        allmusics = self.app.music.playlist.get_group_sorted_musics()
        new_music = allmusics[new_idx]
        doscroll = (
            new_music.group is not self.app.music.group
            or new_music.group is None
            or new_music.group.mode == "v"
        )
        self.app.play_music(new_music, new_idx)
        if doscroll:
            self.app.playlist_viewer.set_scroll_to_music(True)

    def action_skip_previous(self):
        if len(self.app.music.playlist.musiclist) <= 0:
            return
        new_idx = self.app.music_index - 1
        if new_idx < 0:
            return
        allmusics = self.app.music.playlist.get_group_sorted_musics()
        new_music = allmusics[new_idx]
        doscroll = (
            new_music.group is not self.app.music.group
            or new_music.group is None
            or new_music.group.mode == "v"
        )
        self.app.play_music(new_music, new_idx)
        if doscroll:
            self.app.playlist_viewer.set_scroll_to_music(True, -1)

    def action_rewind(self):
        self.app.close_menu()
        self.app.play_music(self.app.music, self.app.music_index)

    def music_auto_finish(self):
        if self.app.music_loops:
            self.app.play_music(self.app.music, self.app.music_index)
            return
        if self.app.shuffle:
            music_available = self.app.music.playlist.musiclist.copy()
            music_available.remove(self.app.music)
            new_music = random.choice(music_available)
            doscroll = (
                new_music.group is not self.app.music.group
                or new_music.group is None
                or new_music.group.mode == "v"
            )
            self.app.play_music(
                new_music,
                self.app.music.playlist.musiclist.index(new_music),
            )
            if doscroll:
                self.app.playlist_viewer.set_scroll_to_music(True)
            return
        self.action_skip_next(True, True)

    def event(self, event):
        if event.type == MUSIC_ENDEVENT:
            if self.app.music is None:
                return
            self.music_auto_finish()
        if event.type == pygame.WINDOWFOCUSGAINED:
            if event.window == self.minip.window:
                self.minip.focused = True
            else:
                self.minip.focused = False
        if event.type == pygame.WINDOWFOCUSLOST and event.window == self.minip.window:
            self.minip.focused = False
        if event.type == pygame.WINDOWCLOSE and event.window == self.minip.window:
            self.minip.close()
        if event.type == pygame.KEYDOWN:
            self.key_controls(event)

    def key_controls(self, event):
        if self.app.input_stolen or self.app.listening_key:
            return
        if self.app.music is not None:
            if Keybinds.check("pause_music", event, 1073742085):
                self.action_play()
            if (
                event.mod & pygame.KMOD_META
                and event.mod & pygame.KMOD_SHIFT
                and event.mod & pygame.KMOD_CTRL
            ):
                self.action_play()
            if event.scancode == pygame.KSCAN_PAUSE:
                self.action_play()
            if Keybinds.check("next_track", event, 1073742082):
                self.action_skip_next(True, True)
            elif Keybinds.check("previous_track", event, 1073742083):
                self.action_skip_previous()
            elif Keybinds.check("skip_5_s", event):
                self.action_forward_5()
            elif Keybinds.check("back_5_s", event):
                self.action_backwards_5()
            elif Keybinds.check("rewind_music", event):
                self.action_rewind()
            elif Keybinds.check("toggle_miniplayer", event):
                if self.minip.window is None:
                    self.action_miniplayer()
                else:
                    self.minip.action_back_to_app()
            elif Keybinds.check("music_maximize", event):
                if self.app.modal_state == "fullscreen":
                    self.app.music_fullscreen.close()
                else:
                    self.action_fullscreen()
            elif Keybinds.check("music_fullscreen", event):
                if self.app.modal_state == "fullscreen" and self.super_fullscreen:
                    self.app.modal_state = "none"
                    self.super_fullscreen = False
                elif self.app.modal_state == "fullscreen":
                    self.action_superfullscreen()
                else:
                    self.action_fullscreen()
                    self.action_superfullscreen()
            elif Keybinds.check("extra_controls", event):
                if not self.app.split_screen:
                    if self.app.menu_open and self.app.menu_data == "controls":
                        self.app.close_menu()
                    elif not self.super_fullscreen and not self.clean_ui:
                        self.action_dots()
            elif Keybinds.check("end_music", event):
                self.app.end_music()
            elif Keybinds.check("clean_controls_ui", event):
                self.clean_ui = not self.clean_ui
        if Keybinds.check("volume_up", event):
            self.app.volume += 0.05
            if self.app.volume > 1:
                self.app.volume = 1
            self.app.settings.slider.valuex = self.app.volume
            pygame.mixer.music.set_volume(self.app.volume)
        elif Keybinds.check("volume_down", event):
            self.app.volume -= 0.05
            if self.app.volume < 0:
                self.app.volume = 0
            self.app.settings.slider.valuex = self.app.volume
            pygame.mixer.music.set_volume(self.app.volume)
