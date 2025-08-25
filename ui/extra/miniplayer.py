import mili
import pygame
from pygame._sdl2 import video as pgvideo
from ui.common import *


class MiniplayerUI:
    def __init__(self, app: "MILIMP"):
        self.app = app
        self.state = app.state
        self.window = None
        self.focused = False
        self.mili = mili.MILI(mili.SurfaceCanva(pygame.Surface((10, 10))), True)
        self.press_pos = pygame.Vector2()
        self.rel_pos = pygame.Vector2()
        self.last_pressed = False
        self.ui_mult = 1
        self.cover_cache = mili.ImageCache()
        self.bg_cache = mili.ImageCache()
        self.anims = [animation(-5) for i in range(3)]
        self.controls_rect = pygame.Rect()
        self.bg_surf = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.hovered = False
        self.last_size = MINIP_PREFERRED_SIZES
        self.last_pos = None
        self.last_borderless = True
        self.prev_mpos = pygame.Vector2()
        self.static_time = None
        self.desktop = pygame.display.get_desktop_sizes()[0]
        self.custom_borders = mili.CustomWindowBorders(
            self.window,
            2,
            4,
            0,
            True,
        )
        if mili.VERSION >= (1, 0, 5):
            self.custom_borders.constraint_rect = pygame.Rect((0, 0), self.desktop)

        self.mili.default_styles(
            line={"color": (255,) * 3},
            circle={"antialias": True},
            image={"smoothscale": True},
        )

    def mult(self, v):
        return max(1, int(v * self.ui_mult * 0.7))

    def open(self):
        if self.last_pos is None:
            self.window = pygame.Window(
                "MILIMP Miniplayer",
                self.last_size,
                resizable=True,
                borderless=self.last_borderless,
            )
        else:
            self.window = pygame.Window(
                "MILIMP Miniplayer",
                self.last_size,
                self.last_pos,
                resizable=True,
                borderless=self.last_borderless,
            )
        if USE_RENDERER:
            canva = pgvideo.Renderer(self.window)
        else:
            canva = self.window.get_surface()
        self.mili.canva = canva
        self.window.always_on_top = True
        self.window.minimum_size = (100, 100)
        if not USE_RENDERER:
            self.window.get_surface()
        self.window.set_icon(ICONS.music_cover)
        try:
            self.window.flash(pygame.FLASH_BRIEFLY)
        except Exception:
            pass
        self.focused = True
        self.mouse_data = []
        self.custom_borders.window = self.window
        self.resize_ratio()

    def action_toggle_border(self):
        if not self.window.borderless:
            self.window.borderless = True
            self.window.resizable = True
        else:
            self.window.borderless = False
            self.window.resizable = True

    def save_state(self):
        if self.window is None:
            return
        self.last_size = self.window.size
        self.last_pos = self.window.position
        self.last_borderless = self.window.borderless

    def close(self):
        self.save_state()
        self.window.destroy()
        self.window = None
        self.focused = False
        if USE_RENDERER:
            mili.ImageCache._preallocated_caches = []
            self.mili.canva._shape_cache = {}
            self.app.mili.canva._shape_cache = {}

    def can_interact(self):
        return (
            self.can_abs_interact()
            and not self.custom_borders.resizing
            and not self.custom_borders.dragging
            and self.custom_borders.cumulative_relative.length() == 0
        )

    def can_abs_interact(self):
        return self.window is not None

    def action_back_to_app(self):
        self.close()
        self.app.window.focus()
        try:
            self.app.window.flash(pygame.FLASH_BRIEFLY)
        except Exception:
            pass

    def move_window(self):
        if not self.can_interact():
            return
        pressed = pygame.mouse.get_pressed(5, True)[0]
        just = pressed and not self.last_pressed
        self.last_pressed = pressed
        if just:
            self.rel_pos = pygame.Vector2(pygame.mouse.get_pos())
            self.press_pos = pygame.Vector2(pygame.mouse.get_pos(True))

        if pressed and self.hovered:
            gmpos = pygame.mouse.get_pos(True)
            self.window.position = (
                self.press_pos + (gmpos - self.press_pos) - self.rel_pos
            )
            self.clamp_window()

    def resize_ratio(self):
        cover = self.state.get_music_cover()
        if cover is None:
            return
        ratio = cover.width / cover.height
        neww = self.window.size[1] * ratio
        diff = neww - self.window.size[0]
        self.window.size = (neww, self.window.size[1])
        self.window.position = (
            int(self.window.position[0] - diff),
            self.window.position[1],
        )
        self.clamp_window(True)

    def clamp_window(self, force=False):
        if mili.VERSION >= (1, 0, 5) and self.window.borderless and not force:
            return
        size = (
            pygame.math.clamp(self.window.size[0], 100, self.desktop[0]),
            pygame.math.clamp(self.window.size[1], 100, self.desktop[1]),
        )
        if self.window.size != size:
            self.window.size = size
        pos = (
            pygame.math.clamp(self.window.position[0], 0, self.desktop[0] - size[0]),
            pygame.math.clamp(self.window.position[1], 0, self.desktop[1] - size[1]),
        )
        if self.window.position != pos:
            self.window.position = pos

    def ui(self):
        mpos = pygame.Vector2(pygame.mouse.get_pos(True))
        self.hovered = pygame.Rect(self.window.position, self.window.size).collidepoint(
            mpos
        )
        if round(mpos - self.prev_mpos).length() != 0:
            self.static_time = None
        else:
            if self.static_time is None:
                self.static_time = pygame.time.get_ticks()
        self.custom_borders.titlebar_height = self.window.size[1]
        if self.window.borderless:
            if self.can_abs_interact():
                self.custom_borders.update()
            if self.custom_borders.dragging or self.custom_borders.resizing:
                self.clamp_window()
        else:
            self.move_window()

        wm = self.window.size[0] / MINIP_PREFERRED_SIZES[0]
        hm = self.window.size[1] / MINIP_PREFERRED_SIZES[1]
        self.ui_mult = min(1.4, max(0.69, (wm * 0.1 + hm * 1) / 1.1))

        self.mili.rect({"color": (3,) * 3})
        self.mili.rect(
            {"color": (20,) * 3, "outline": 1, "border_radius": 0, "draw_above": True}
        )

        show_controls = (
            self.hovered
            and (
                self.static_time is None
                or (pygame.time.get_ticks() - self.static_time < 1000)
            )
            or self.custom_borders.resizing
            or self.custom_borders.dragging
        )
        self.ui_cover()
        self.mili.id_checkpoint(20)
        if show_controls:
            self.ui_controls()
        self.mili.id_checkpoint(ID_OFFSET + 70000)

        if show_controls:
            self.ui_line()
            self.mili.id_checkpoint(ID_OFFSET + 71000)
            self.ui_top_btn(ICONS.minip_back, "left", self.action_back_to_app)
            if self.window is None:
                return
            self.ui_top_btn(
                ICONS.resize if self.window.borderless else ICONS.borderless,
                "rightleft",
                self.action_toggle_border,
            )
            self.ui_top_btn(ICONS.ratio, "rightleftleft", self.resize_ratio)
            self.ui_top_btn(ICONS.close, "right", self.close)

        if not self.custom_borders.dragging and not self.custom_borders.resizing:
            self.custom_borders.cumulative_relative = pygame.Vector2()
        self.prev_mpos = mpos

    def ui_line(self):
        totalw = self.window.size[0] - self.mult(8)
        pos = self.state.get_music_pos()
        percentage = (pos) / self.state.music.duration

        sizeperc = totalw * percentage
        data = self.mili.line_element(
            [(-totalw / 2, 0), (totalw / 2, 0)],
            {"color": (50,) * 3, "size": self.mult(2)},
            pygame.Rect(0, 0, totalw, 2).move_to(
                midbottom=(self.window.size[0] / 2, self.window.size[1] - self.mult(3))
            ),
            {"align": "center", "ignore_grid": True, "blocking": None},
        )
        self.mili.line_element(
            [(-totalw / 2, 0), (-totalw / 2 + sizeperc, 0)],
            {"color": (255, 0, 0), "size": self.mult(2)},
            data.data.absolute_rect,
            {"ignore_grid": True, "parent_id": 0, "z": 99999, "blocking": None},
        )

    def ui_cover(self):
        cover = self.state.get_music_cover(True)
        if cover is None:
            return
        it = self.mili.element(None, {"fillx": True, "filly": True})
        ready = False
        if self.state.async_videoclip is not None:
            self.state.async_videoclip.miniplayer_rect.set_rect(it.data.rect)
            cover, ready = self.state.async_videoclip.miniplayer_rect.get_or(cover)
        self.mili.image(cover, {"cache": self.cover_cache, "ready": ready})

    def ui_controls(self):
        with self.mili.begin(
            pygame.Rect((0, 0), self.controls_rect.size).move_to(
                midbottom=(self.window.size[0] / 2, self.window.size[1] - self.mult(15))
            ),
            {
                "resizex": True,
                "resizey": True,
                "align": "center",
                "clip_draw": False,
                "axis": "x",
                "ignore_grid": True,
            },
        ) as data:
            shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
            self.controls_rect = data.data.rect
            self.mili.image(
                self.bg_surf,
                {
                    "cache": self.bg_cache,
                    "border_radius": "50",
                    "fill": True,
                    "fill_color": MP_BG_FILL,
                },
            )
            if self.state.music_index > 0 or shift:
                self.ui_control_btn(
                    ICONS.back5 if shift else ICONS.skip_previous,
                    50,
                    self.state.previous_5 if shift else self.state.skip_previous,
                    0,
                )
            self.ui_control_btn(
                ICONS.play if self.state.music_paused else ICONS.pause,
                60,
                self.state.pause,
                1,
            )
            if (
                self.state.music_index < len(self.state.music.playlist.musiclist) - 1
                or shift
            ):
                self.ui_control_btn(
                    ICONS.skip5 if shift else ICONS.skip_next,
                    50,
                    self.state.forward_5 if shift else self.state.skip_next,
                    2,
                )

    def ui_control_btn(self, image, size, action, animi):
        anim: mili.animation.ABAnimation = self.anims[animi]
        size = self.mult(size)
        if it := self.mili.element((0, 0, size, size), {"align": "center"}):
            if it.hovered and self.can_interact():
                self.mili.image(
                    self.bg_surf,
                    {
                        "cache": get_img_cache(),
                        "fill": True,
                        "border_radius": "50",
                        "fill_color": cond(self, it, *MP_OVERLAY_CV),
                    },
                )
            self.mili.image(
                image,
                {
                    "cache": get_img_cache(),
                    "pad": self.mult(1) + anim.value / 3,
                },
            )
            if (it.left_just_released and self.can_interact()) and self.can_interact():
                action()
            if it.just_hovered and self.can_interact():
                anim.goto_b()
            if it.just_unhovered and self.can_interact():
                anim.goto_a()

    def ui_top_btn(self, img, side, action):
        size = self.mult(35)
        offset = self.mult(4)
        if it := self.mili.element(
            pygame.Rect(0, 0, size, size).move_to(topleft=(offset, offset))
            if side == "left"
            else pygame.Rect(0, 0, size, size).move_to(
                topright=(
                    self.window.size[0]
                    - (
                        offset
                        if side == "right"
                        else (
                            size + offset * 2
                            if side == "rightleft"
                            else size * 2 + offset * 3
                        )
                    ),
                    offset,
                )
            ),
            {"ignore_grid": True, "parent_id": 0},
        ):
            self.mili.image(
                self.bg_surf,
                {
                    "cache": self.bg_cache,
                    "border_radius": 0,
                    "fill": True,
                    "fill_color": cond(self, it, *MP_OVERLAY_CV),
                },
            )
            self.mili.image(img, {"cache": get_img_cache()})
            if (it.left_just_released and self.can_interact()) and self.can_interact():
                action()

    def run(self):
        if self.window is None:
            return

        if self.mili.canva.backend == "surface":
            surf = self.window.get_surface()
            self.mili.canva = surf
            surf.fill("black")
        else:
            self.mili.canva._clear("black", self.window)

        self.mili.start(
            {
                "anchor": "center",
                "padx": self.mult(0),
                "pady": self.mult(0),
            },
            is_global=False,
            window_position=self.window.position,
        )
        self.ui()

        if self.window is None:
            return

        self.mili.update_draw()
        self.mili.canva._flip(self.window)
