import mili
import numpy
import pygame
import random
from ui.common import *
import tkinter.filedialog as filedialog

from ui.common.data import NotCached, MenuButton
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
        self.anims = [animation(-3) for i in range(12)]
        self.overlay_anims = [animation(-3) for i in range(7)]
        self.handle_anim = animation(-10)
        self.slider = mili.Slider(
            {"lock_y": True, "handle_size": 30, "drag_area": False}
        )
        self.bigcover_cache = mili.ImageCache()
        self.black_cache = mili.ImageCache()
        self.split_screen_cache = mili.ImageCache()
        self.cover_cache = mili.ImageCache()
        self.timebar_controlled = False
        self.timebar_pos = None
        self.handle_percentage = None
        self.big_cover = False
        self.bigcover_time = 0
        self.dots_rect = None
        self.width = 0
        self.track_hover_pos = None
        self.videoclip_rects = []
        self.clean_ui = False
        self.slider_hovered = False
        self.volume_shown = False
        self.last_frame_click = pygame.time.get_ticks()
        self.volume_slider = mili.Slider(
            {
                "area_update_id": "volumearea",
                "handle_update_id": "volumehandle",
                "lock_y": True,
            }
        )

    def ui(self):
        if self.app.split_screen:
            self.width = (
                1 - (self.app.split_w / self.app.window.size[0])
            ) * self.app.window.size[0]
        else:
            self.width = self.app.split_w
        if self.app.modal_state != "fullscreen" and self.app.super_fullscreen:
            self.app.super_fullscreen = False
            if self.app.maximized:
                self.app.window.size = (
                    self.app.window.size[0],
                    self.app.before_super_fullscreen_height,
                )
        self.cont_height = 0
        if self.state.music is None:
            return

        if (
            self.app.menu_open
            and self.app.menu_data == "controls"
            and self.dots_rect is not None
        ):
            self.app.menu_pos = self.get_menu_pos(self.app.menu_buttons)

        self.state.update_videoclip_cover()
        self.state.update_bg_effect()

        if (
            self.app.custom_borders.resizing
            or self.app.super_fullscreen
            or (
                self.clean_ui
                and (self.app.split_screen or self.app.modal_state == "fullscreen")
            )
        ):
            self.minip.run()
            return

        if self.state.music_paused:
            self.state.music_play_time += self.app.delta_time * 1000
        self.small_cont = self.main_cont is None or (
            not self.main_cont.data.absolute_rect.collidepoint(pygame.mouse.get_pos())
            and not self.slider_hovered
        )
        self.slider_hovered = False
        contheight = self.mult(116)  # 100 if self.small_cont else 116
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
        else:
            vol_image = ICONS.vol0
            if self.state.volume >= 0.5:
                vol_image = ICONS.vol1
            elif self.state.volume > 0.05:
                vol_image = ICONS.vollow
            hov, rect = self.ui_overlay_btn(
                self.overlay_anims[6],
                self.state.mute,
                vol_image,
                0,
                "Mute/umute the music",
                "left",
            )
            if hov and not self.volume_shown:
                self.volume_shown = True
            if self.volume_shown:
                self.ui_volume_bar(rect, None)

        self.minip.run()

    def ui_split_screen(self):
        if self.state.music is None:
            return
        with self.mili.begin(
            None,
            mili.PADLESS | {"filly": True, "fillx": True, "blocking": None},
        ):
            cover = self.state.get_music_cover()
            if cover is None:
                return
            else:
                it = self.mili.element(
                    (
                        0,
                        0,
                        0,
                        self.app.window.size[1] - self.cont_height - self.app.tbarh,
                    ),
                    {"fillx": True},
                )
                scaled, cover = self.state.get_scaled_cover(cover, it, True)
                self.mili.image(
                    cover,
                    {"cache": self.cover_cache, "ready": scaled} | mili.PADLESS,
                )
                if it.hovered:
                    self.app.cursor_hover = True
                if it.left_just_released:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        if (
                            self.app.view_state != "playlist"
                            or self.app.playlist_viewer.playlist
                            is not self.state.music.playlist
                        ):
                            self.app.playlist_viewer.enter(self.state.music.playlist)
                        self.app.playlist_viewer.set_scroll_to_music()
                    else:
                        if pygame.time.get_ticks() - self.last_frame_click <= 200:
                            self.action_fullscreen()
                            self.action_superfullscreen()
                        self.clean_ui = False
                        self.state.pause()
                        self.last_frame_click = pygame.time.get_ticks()
                elif (
                    it.just_released_button == pygame.BUTTON_MIDDLE
                    and self.state.music_videoclip_cover is not None
                    and pygame.key.get_mods() & pygame.KMOD_CTRL
                ):
                    self.state.music.cover = self.state.music_videoclip_cover.copy()
                    self.state.music.loaded_cover = True
                    pygame.image.save(
                        self.state.music.cover,
                        f"data/music_covers/{self.state.music.playlist.name}_{self.state.music.realstem}.png",
                    )

    def ui_cover(self):
        bigcover = False
        imgsize = 0
        cover = self.state.get_music_cover()
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
                        is not self.state.music.playlist
                    ):
                        self.app.playlist_viewer.enter(self.state.music.playlist)
                    self.app.playlist_viewer.set_scroll_to_music()
                elif (
                    it.just_released_button == pygame.BUTTON_MIDDLE
                    and self.state.music_videoclip_cover is not None
                ):
                    self.state.music.cover = self.state.music_videoclip_cover.copy()
                    self.state.music.loaded_cover = True
                    pygame.image.save(
                        self.state.music.cover,
                        f"data/music_covers/{self.state.music.playlist.name}_{self.state.music.realstem}.png",
                    )
                if it.absolute_hover:
                    bigcover = True
                    self.app.cursor_hover = True
                    self.app.tick_tooltip("Jump to the track in the playlist")
        else:
            self.mili.element(None, {"blocking": None})
        return bigcover

    def ui_track_control(self):
        if self.state.music.pos_supported and self.state.music.duration not in [
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
        pos = self.state.get_music_pos()
        txt, txtstyle = (
            format_music_time(pos, self.state.music.duration),
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
        pos = self.state.get_music_pos()
        percentage = (pos) / self.state.music.duration

        if percentage > 1.01:
            self.state.music_auto_finish()
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
        pos = self.state.get_music_pos()
        percentage = (pos) / self.state.music.duration
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
                        self.state.set_music_pos(
                            self.timebar_pos * self.state.music.duration
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
        music_pos = self.state.music.duration * hperc
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            self.track_hover_pos = music_pos
        else:
            self.track_hover_pos = None
        hpostxt = format_music_time(self.state.music.duration * hperc, None)
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
                    self.state.set_music_pos(
                        self.slider.valuex * self.state.music.duration
                    )
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
                f"{parse_music_stem(self.app, self.state.music.realstem)}",
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
        cover = self.state.get_music_cover()
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
            if self.state.music_index > 0:
                self.ui_control_btn(
                    ICONS.skip_previous,
                    self.state.skip_previous,
                    40,
                    1,
                    tooltip="Skip to previous track",
                )
            self.ui_control_btn(
                ICONS.back5,
                self.state.previous_5,
                40,
                2,
                tooltip="Back 5 seconds",
                morepadding=True,
            )
            self.ui_control_btn(
                ICONS.play if self.state.music_paused else ICONS.pause,
                self.state.pause,
                50,
                3,
                tooltip="Resume music" if self.state.music_paused else "Pause music",
            )
            self.ui_control_btn(
                ICONS.skip5,
                self.state.forward_5,
                40,
                4,
                tooltip="Forward 5 seconds",
                morepadding=True,
            )
            if self.state.music_index < len(self.state.music.playlist.musiclist) - 1:
                self.ui_control_btn(
                    ICONS.skip_next,
                    self.state.skip_next,
                    40,
                    5,
                    tooltip="Skip to next track",
                )

    def ui_control_btn(
        self,
        image,
        action,
        size,
        animi,
        special=False,
        dots=False,
        tooltip=None,
        morepadding=False,
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
                    "cache": get_img_cache(),
                    "pad": self.mult(1)
                    + anim.value
                    + (self.mult(3) if morepadding else 0),
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

    def ui_overlay_control_btn(
        self,
        anim: mili.animation.ABAnimation,
        on_action,
        image,
        y_side=0,
        tooltip=None,
        split_side="right",
        inner_side=0,
    ):
        size = self.mult(40)
        offset = self.mult(5) * 0.6
        xoffset = offset
        winw = self.app.window.size[0]
        if split_side == "right":
            xoffset += inner_side * (size + offset)
        else:
            xoffset += (winw - self.app.split_w) - ((inner_side + 1) * (size + offset))
        sideoffset = y_side * size + y_side * (offset)
        hovered = False
        if it := self.mili.element(
            pygame.Rect(0, 0, size, size).move_to(
                bottomright=(
                    winw - xoffset,
                    self.app.window.size[1]
                    - offset
                    - self.app.music_controls.cont_height
                    - sideoffset,
                )
            ),
            {"ignore_grid": True, "clip_draw": False, "parent_id": 0, "z": 9999},
        ):
            self.mili.circle(
                {
                    "color": (cond(self.app, it, *OVERLAY_CV),) * 3,
                    "border_radius": "50",
                    "pad": -self.mult(abs(anim.value) / 2.2),
                }
            )
            self.mili.image(
                image,
                {
                    "cache": get_img_cache(),
                    "pad": self.mult(8 + anim.value / 1.8),
                },
            )
            if self.app.can_interact():
                if it.hovered or it.unhover_pressed:
                    self.app.cursor_hover = True
                if it.hovered:
                    self.app.tick_tooltip(tooltip)
                    hovered = True
                if it.just_hovered:
                    anim.goto_b()
                    hovered = True
                if it.left_just_released:
                    on_action()
                    anim.goto_a()
            if it.just_unhovered:
                anim.goto_a()
            if not it.absolute_hover and not anim.active and anim.value != anim.a:
                anim.goto_a()
        return hovered, it.data.absolute_rect

    def ui_split_screen_btns(self):
        self.mili.id_jump(10000)
        self.ui_overlay_control_btn(
            self.overlay_anims[0],
            self.state.end_music,
            ICONS.close,
            0,
            "End music playback",
        )
        self.ui_overlay_control_btn(
            self.overlay_anims[1],
            self.action_rewind,
            ICONS.reset,
            1,
            "Rewind track",
        )
        self.ui_overlay_control_btn(
            self.overlay_anims[2],
            self.action_loop,
            ICONS.loopon if self.state.music_loops else ICONS.loopoff,
            0,
            "Disable track looping"
            if self.state.music_loops
            else "Enable track looping",
            inner_side=1,
        )
        self.ui_overlay_control_btn(
            self.overlay_anims[3],
            self.action_fullscreen
            if self.app.modal_state != "fullscreen"
            else self.action_superfullscreen,
            ICONS.fullscreen,
            0,
            "Enable fullscreen"
            if self.app.modal_state == "fullscreen"
            else "Maximize track",
            "left",
        )
        self.ui_overlay_control_btn(
            self.overlay_anims[4],
            self.action_miniplayer,
            ICONS.minip if self.minip.window is None else ICONS.maxip,
            1,
            "Open miniplayer" if self.minip.window is None else "Close miniplayer",
            "left",
        )
        extraoffset = 0
        if self.can_save_frame():
            self.ui_overlay_control_btn(
                self.overlay_anims[5],
                self.action_save_frame,
                ICONS.save_frame,
                0,
                "Save current frame (highest resolution)",
                "left",
                1,
            )
            extraoffset = 1
        vol_image = ICONS.vol0
        if self.state.volume >= 0.5:
            vol_image = ICONS.vol1
        elif self.state.volume > 0.05:
            vol_image = ICONS.vollow
        hovered, rect = self.ui_overlay_control_btn(
            self.overlay_anims[6],
            self.state.mute,
            vol_image,
            0,
            "Mute/umute the music",
            "left",
            1 + extraoffset,
        )
        if hovered and not self.volume_shown:
            self.volume_shown = True
        if self.volume_shown:
            self.ui_volume_bar(rect)

    def ui_volume_bar(self, button_rect, pid=0):
        if self.app.split_screen:
            size = self.mult(40)
            width = (
                self.app.window.size[0]
                - self.app.split_w
                - (size + self.mult(5) * 0.6) * 4.5
            )
            barh = size / (4.5)
        else:
            size = self.mult(50)
            width = self.app.split_w - (size + self.mult(8)) * 1.7
            barh = size / 6
        height = size
        area_height = barh * 3
        width = min(width, 800)
        self.volume_slider.style["handle_size"] = (barh * 2, barh * 2)
        with self.mili.begin(
            (button_rect.topleft, (width, height)),
            {
                "ignore_grid": True,
                "z": 9995,
                "axis": "x",
                "default_align": "center",
                "pad": 0,
            }
            | ({"parent_id": 0} if pid == 0 else {}),
        ) as hover_area:
            with self.mili.begin(
                (0, 0, width, area_height),
                {"blocking": False, "axis": "x", "default_align": "center"},
            ):
                self.mili.rect({"color": (OVERLAY_CV[0],) * 3, "border_radius": "50"})
                self.mili.element((0, 0, size * 1.2, 0))
                with self.mili.begin(
                    (0, 0, 0, barh),
                    {"fillx": f"100-{barh}", "z": 9996, "anchor": "first", "pad": 0}
                    | self.volume_slider.area_style,
                ) as area:
                    self.mili.rect({"color": (45,) * 3})
                    self.mili.rect_element(
                        {"color": (110,) * 3},
                        (0, 0, area.data.rect.w * self.volume_slider.valuex, barh),
                        {"z": 9997, "blocking": False},
                    )
                    with self.mili.element(
                        self.volume_slider.handle_rect,
                        self.volume_slider.handle_style
                        | {"z": 9998, "clip_draw": False},
                    ) as handle:
                        self.mili.circle({"color": (255,) * 3})
            if (
                not hover_area.absolute_hover
                and not self.volume_slider.dragging_area
                and not handle.left_pressed
            ):
                self.volume_shown = False
            if self.app.can_interact():
                if (
                    area.hovered
                    or handle.hovered
                    or handle.left_pressed
                    or self.volume_slider.dragging_area
                ):
                    self.app.cursor_hover = True
                if self.volume_slider.dragging_area or handle.left_pressed:
                    self.state.change_volume(self.volume_slider.valuex)
                else:
                    self.volume_slider.valuex = self.state.volume
            else:
                self.volume_shown = False

            self.mili.element((0, 0, barh, 0))

    def when_play(self):
        self.offset = 0
        self.offset_restart_time = pygame.time.get_ticks()

        if self.minip.window is not None:
            self.minip.resize_ratio()

    def when_end_music(self):
        if self.minip.window is not None:
            self.minip.close()
        self.clean_ui = False

    def action_dots(self):
        if self.dots_rect is None:
            return
        if self.app.menu_open:
            self.app.close_menu()
            return
        buttons = [
            MenuButton(
                ICONS.close,
                self.state.end_music,
                self.anims[6],
                tooltip="End music playback",
            ),
            MenuButton(ICONS.reset, self.action_rewind, self.anims[7], tooltip="Rewind track"),
            MenuButton(
                ICONS.loopon if self.state.music_loops else ICONS.loopoff,
                self.action_loop,
                self.anims[8],
                "15" if self.state.music_loops else "30",
                "Disable track looping"
                if self.state.music_loops
                else "Enable track looping",
            ),
            MenuButton(
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
            MenuButton(
                ICONS.minip if self.minip.window is None else ICONS.maxip,
                self.action_miniplayer,
                self.anims[10],
                "35",
                "Open miniplayer" if self.minip.window is None else "Close miniplayer",
            ),
        ]
        if self.can_save_frame():
            buttons.append(
                MenuButton(
                    ICONS.save_frame,
                    self.action_save_frame,
                    self.anims[11],
                    "35",
                    "Save current frame (highest resolution)",
                )
            )
        self.app.open_menu(
            "controls",
            *buttons,
            pos=self.get_menu_pos(buttons),
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

    def can_save_frame(self):
        return (
            self.state.async_videoclip is not None
            and self.state.music is not None
            and self.state.music.isvideo
            and self.state.videoclip_on
        )

    def action_save_frame(self):
        frame = self.state.async_videoclip
        paused = self.state.music_paused
        if not paused:
            self.state.pause()
        time = frame.time
        path = filedialog.asksaveasfilename(
            initialfile=self.state.music.realstem + f"_{int(time)}.png"
        )
        if path:
            videoclip = frame.videoclip
            if frame.videoclip_scaled:
                import moviepy

                videoclip = moviepy.VideoFileClip(videoclip.filename, audio=False)
            image = pygame.surfarray.make_surface(
                numpy.transpose(videoclip.get_frame(time), (1, 0, 2))
            )
            pygame.image.save(image, path)
            if frame.videoclip_scaled:
                videoclip.close()
            self.app.notify(NOTIF.DOWNLOAD, f"Video frame saved at '{path}'")
        if not paused:
            self.state.pause()

    def action_fullscreen(self):
        self.app.modal_state = "fullscreen"
        self.app.close_menu()

    def action_superfullscreen(self):
        self.app.before_super_fullscreen_height = self.app.window.size[1]
        if self.app.maximized:
            self.app.window.size = (
                self.app.window.size[0],
                pygame.display.get_desktop_sizes()[0][1],
            )
        self.app.super_fullscreen = True
        self.app.close_menu()

    def action_loop(self):
        self.state.music_loops = not self.state.music_loops
        self.app.close_menu()
        if not self.app.split_screen:
            self.action_dots()

    def action_miniplayer(self):
        self.app.close_menu()
        if self.minip.window is None:
            self.minip.open()
        else:
            self.minip.close()

    def action_rewind(self):
        self.app.close_menu()
        self.state.rewind()

    def event(self, event):
        if event.type == MUSIC_ENDEVENT:
            if self.state.music is None:
                return
            self.state.music_auto_finish()
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
        if self.state.music is not None:
            if Keybinds.check("pause_music", event, 1073742085):
                self.state.pause()
            if (
                event.mod & pygame.KMOD_META
                and event.mod & pygame.KMOD_SHIFT
                and event.mod & pygame.KMOD_CTRL
            ):
                self.state.pause()
            if event.scancode == pygame.KSCAN_PAUSE:
                self.state.pause()
            if Keybinds.check("next_track", event, 1073742082):
                self.state.skip_next(True, True)
            elif Keybinds.check("previous_track", event, 1073742083):
                self.state.skip_previous()
            elif Keybinds.check("skip_5_s", event):
                self.state.forward_5()
            elif Keybinds.check("back_5_s", event):
                self.state.previous_5()
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
                if self.app.modal_state == "fullscreen" and self.app.super_fullscreen:
                    pygame.mouse.set_visible(True)
                    self.app.modal_state = "none"
                    self.app.super_fullscreen = False
                    if self.app.maximized:
                        self.app.window.size = (
                            self.app.window.size[0],
                            self.app.before_super_fullscreen_height,
                        )
                elif self.app.modal_state == "fullscreen":
                    self.action_superfullscreen()
                else:
                    self.action_fullscreen()
                    self.action_superfullscreen()
            elif Keybinds.check("extra_controls", event):
                if not self.app.split_screen:
                    if self.app.menu_open and self.app.menu_data == "controls":
                        self.app.close_menu()
                    elif not self.app.super_fullscreen and not self.clean_ui:
                        self.action_dots()
            elif Keybinds.check("end_music", event):
                self.state.end_music()
            elif Keybinds.check("clean_controls_ui", event):
                self.clean_ui = not self.clean_ui
            elif Keybinds.check("toggle_videoclip_threading", event):
                self.state.toggle_thread()
        if Keybinds.check("volume_up", event):
            self.state.volume_up()
        elif Keybinds.check("volume_down", event):
            self.state.volume_down()
