import mili
import pygame
from ui.common import *


class MusicFullscreenUI(UIComponent):
    def init(self):
        self.anims = [animation(-5) for i in range(2)]
        self.cache = mili.ImageCache()
        self.music_cache = mili.ImageCache()
        self.last_move = pygame.time.get_ticks()
        self.last_mouse = pygame.Vector2()
        self.last_frame_click = pygame.time.get_ticks()

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 120000)
        if self.app.music is None:
            self.close()
            return
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": None} | mili.PADLESS,
        ):
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 255), "cache": self.cache}
            )

            cover = ICONS.music_cover
            current = (
                self.app.music_controls.async_videoclip is not None
                and self.app.music_controls.music_videoclip_cover is not None
                and not self.app.music_paused
                and self.app.focused
            )
            if self.app.music.cover is not None:
                cover = self.app.music.cover
            if (
                self.app.music_controls.music_videoclip_cover is not None
                and self.app.focused
            ):
                cover = self.app.music_controls.music_videoclip_cover
            if cover is None:
                self.close()
            else:
                it = self.mili.element(
                    (
                        0,
                        0,
                        0,
                        self.app.window.size[1]
                        - self.app.music_controls.cont_height
                        - self.app.tbarh,
                    ),
                    {"fillx": True},
                )
                scaled = False
                if current:
                    self.app.music_controls.videoclip_rects.append((0, it.data.rect))
                    if it.data.rect.size in (
                        out := self.app.music_controls.async_videoclip.scaled_output
                    ):
                        cover = out[it.data.rect.size]
                        scaled = True
                self.mili.image(
                    cover,
                    {"cache": self.music_cache, "ready": scaled} | mili.PADLESS,
                )
                if it.hovered:
                    self.app.cursor_hover = True
                if it.left_just_released:
                    if pygame.time.get_ticks() - self.last_frame_click <= 200:
                        if self.app.music_controls.super_fullscreen:
                            self.close_superfullscreen()
                        else:
                            self.close()
                    self.app.music_controls.clean_ui = False
                    self.app.music_controls.action_play()
                    self.last_frame_click = pygame.time.get_ticks()
            if not self.app.music_controls.super_fullscreen or (
                pygame.time.get_ticks() - self.last_move <= 2000
            ):
                if not pygame.mouse.get_visible():
                    pygame.mouse.set_visible(True)
                self.ui_overlay_btn(
                    self.anims[0],
                    self.close,
                    ICONS.fullscreenclose,
                    tooltip="Disable fullscreen"
                    if self.app.music_controls.super_fullscreen
                    else "Minimize",
                )
            else:
                if pygame.mouse.get_visible():
                    pygame.mouse.set_visible(False)
            mouse = pygame.mouse.get_pos()
            if mouse != self.last_mouse:
                self.last_move = pygame.time.get_ticks()
            self.last_mouse = mouse

    def close_superfullscreen(self):
        if self.app.music_controls.super_fullscreen:
            self.app.music_controls.super_fullscreen = False
            if self.app.maximized:
                self.app.window.size = (
                    self.app.window.size[0],
                    self.app.music_controls.before_super_fullscreen_height,
                )
            return True
        return False

    def close(self):
        if self.close_superfullscreen():
            return
        self.app.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
