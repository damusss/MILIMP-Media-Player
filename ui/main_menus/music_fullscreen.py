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
        self.super_fullscreen_on_hover = False
        self.bottom_hover_time = pygame.time.get_ticks()

    def ui(self):
        mouse = pygame.mouse.get_pos()
        ws = self.app.window.size
        if (
            self.app.custom_behavior.fullscreen
            and self.app.super_fullscreen
            and (
                pygame.Rect(0, ws[1] - 5, ws[0], 5).collidepoint(mouse)
                or pygame.Rect(0, 0, ws[0], 5).collidepoint(mouse)
            )
        ):
            self.app.super_fullscreen = False
            self.super_fullscreen_on_hover = True
            self.bottom_hover_time = pygame.time.get_ticks()

        self.mili.id_checkpoint(ID_OFFSET + 120000)
        if self.state.music is None:
            self.close()
            return
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": None} | mili.PADLESS,
        ):
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 255), "cache": self.cache}
            )

            cover = self.state.get_music_cover()
            if cover is None:
                self.close_superfullscreen()
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
                ready = False
                if self.state.async_videoclip is not None:
                    self.state.async_videoclip.main_rect.set_rect(it.data.rect)
                    cover, ready = self.state.async_videoclip.main_rect.get_or(cover)
                self.mili.image(
                    cover,
                    {"cache": self.music_cache, "ready": ready} | mili.PADLESS,
                )
                if it.hovered:
                    self.app.cursor_hover = True
                if it.data.absolute_rect.inflate(0, -self.mult(70 * 2)).collidepoint(
                    mouse
                ):
                    if (
                        pygame.time.get_ticks() - self.bottom_hover_time >= 100
                        and self.super_fullscreen_on_hover
                    ):
                        if self.app.custom_behavior.fullscreen:
                            self.app.super_fullscreen = True
                        self.super_fullscreen_on_hover = False
                if it.left_just_released and self.app.can_interact():
                    if pygame.time.get_ticks() - self.last_frame_click <= 200:
                        self.close_superfullscreen()
                        self.close()
                    self.app.state.pause()
                    self.last_frame_click = pygame.time.get_ticks()
                if it.right_clicked:
                    if pygame.time.get_ticks() - self.last_frame_click <= 200:
                        self.close_superfullscreen()
                        self.close()
                    self.last_frame_click = pygame.time.get_ticks()
            if not self.app.super_fullscreen or (
                pygame.time.get_ticks() - self.last_move <= 2000
            ):
                if not pygame.mouse.get_visible():
                    pygame.mouse.set_visible(True)
                self.ui_overlay_btn(
                    self.anims[0],
                    self.close,
                    ICONS.fullscreenclose,
                    tooltip="Disable fullscreen"
                    if self.app.super_fullscreen
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
        pygame.mouse.set_visible(True)
        if self.app.super_fullscreen:
            self.app.super_fullscreen = False
            self.app.custom_behavior.fullscreen_off()
            return True
        return False

    def close(self):
        pygame.mouse.set_visible(True)
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
