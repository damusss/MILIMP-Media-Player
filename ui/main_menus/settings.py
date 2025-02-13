import mili
import pygame
import threading
from ui.common import *


class SettingsUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_handle = animation(-3)
        self.anims = [animation(-3) for i in range(8)]
        self.cache = mili.ImageCache()
        self.slider = mili.Slider({"lock_y": True, "handle_size": (10, 10)})
        self.bar_controlled = False

    def ui(self):
        self.mili.id_checkpoint(3000 + 400)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.close()
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.cache}
            )

            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": "80",
                    "resizey": True,
                    "align": "center",
                    "spacing": self.mult(13),
                    "offset": (0, -self.app.tbarh),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.ui_modal_content()

            self.ui_overlay_btn(
                self.anim_close, self.close, ICONS.close, tooltip="Close"
            )

    def ui_modal_content(self):
        self.mili.text_element(
            "Settings", {"size": self.mult(26)}, None, mili.CENTER | {"blocking": None}
        )
        self.ui_slider()
        self.ui_buttons_top()
        self.ui_buttons_middle()
        self.ui_buttons_bottom()

    def ui_buttons_top(self):
        with self.mili.begin(
            None,
            {
                "resizex": True,
                "resizey": True,
                "axis": "x",
                "clip_draw": False,
                "align": "center",
                "blocking": None,
            }
            | mili.PADLESS,
        ):
            vol_image = ICONS.vol0
            if self.app.volume >= 0.5:
                vol_image = ICONS.vol1
            elif self.app.volume > 0.05:
                vol_image = ICONS.vollow
            self.ui_image_btn(
                vol_image,
                self.action_mute,
                self.anims[0],
                tooltip="Mute/unmute the music",
            )

            self.ui_image_btn(
                ICONS.loopon if self.app.loops else ICONS.loopoff,
                self.action_loop,
                self.anims[1],
                br="50" if not self.app.loops else "5",
                tooltip="Disable playlist looping"
                if self.app.loops
                else "Enable playlist looping",
            )
            self.ui_image_btn(
                ICONS.shuffleon if self.app.shuffle else ICONS.shuffleoff,
                self.action_shuffle,
                self.anims[2],
                br="50" if not self.app.shuffle else "5",
                tooltip="Enable playlist shuffling"
                if self.app.shuffle
                else "Enable playlist shuffle",
            )

    def ui_buttons_middle(self):
        with self.mili.begin(
            None,
            {
                "resizex": True,
                "resizey": True,
                "axis": "x",
                "clip_draw": False,
                "align": "center",
                "blocking": None,
            }
            | mili.PADLESS,
        ):
            self.ui_image_btn(
                ICONS.history,
                self.action_history,
                self.anims[3],
                tooltip="Open history",
            )
            self.ui_image_btn(
                ICONS.keybinds,
                self.action_keybinds,
                self.anims[4],
                br="5",
                tooltip="Open keybindings",
            )

    def ui_buttons_bottom(self):
        with self.mili.begin(
            None,
            {
                "resizex": True,
                "resizey": True,
                "axis": "x",
                "clip_draw": False,
                "align": "center",
                "blocking": None,
            }
            | mili.PADLESS,
        ):
            self.ui_image_btn(
                ICONS.fps60 if self.app.user_framerate == 60 else ICONS.fps30,
                self.action_fps,
                self.anims[5],
                br="5",
                tooltip="Set the framerate to 30"
                if self.app.user_framerate == 60
                else "Set the framerate to 60",
            )
            self.ui_image_btn(
                ICONS.discordoff
                if not self.app.discord_presence.active
                else ICONS.discordon,
                self.action_discord,
                self.anims[6],
                tooltip="Disable the discord presence"
                if self.app.discord_presence.active
                else "Enable the discord presence",
            )
            self.ui_image_btn(
                ICONS.threadon if self.app.videoclip_threaded else ICONS.threadoff,
                self.action_thread,
                self.anims[7],
                tooltip="Disable videoclip multithreading"
                if self.app.videoclip_threaded
                else "Enable videoclip multithreading",
            )

    def ui_slider(self):
        self.slider.style["handle_size"] = self.mult(40), self.mult(40)

        with self.mili.begin(
            (0, 0, 0, self.mult(10)),
            {"align": "center", "fillx": "94"} | self.slider.area_style,
        ) as bar:
            self.slider.update_area(bar)
            self.mili.rect({"color": (30,) * 3})

            if self.app.volume > 0:
                self.mili.rect_element(
                    {"color": (110,) * 3},
                    (0, 0, bar.data.rect.w * self.slider.valuex, bar.data.rect.h),
                    {"ignore_grid": True, "blocking": False},
                )
            handle = self.ui_slider_handle()
            mpressed = pygame.mouse.get_pressed()[0]
            if not self.bar_controlled:
                if (
                    not handle.absolute_hover
                    and self.app.can_interact()
                    and bar.absolute_hover
                    and mpressed
                ):
                    self.bar_controlled = True
                    self.anim_handle.goto_b()
            else:
                if not mpressed:
                    self.bar_controlled = False

            if self.bar_controlled:
                mposx = pygame.mouse.get_pos()[0]
                relmpos = mposx - bar.data.absolute_rect.x
                volume = pygame.math.clamp(relmpos / bar.data.absolute_rect.w, 0, 1)
                self.change_volume(volume)
                self.slider.valuex = volume
                self.app.cursor_hover = True
            elif bar.absolute_hover:
                self.app.cursor_hover = True

    def ui_slider_handle(self):
        if handle := self.mili.element(
            self.slider.handle_rect,
            self.slider.handle_style,
        ):
            self.slider.update_handle(handle)
            self.mili.circle(
                {"color": (255,) * 3, "pad": self.mult(12 + self.anim_handle.value)}
            )
            if not self.bar_controlled:
                if handle.just_hovered and self.app.can_interact():
                    self.anim_handle.goto_b()
                if handle.just_unhovered and not handle.left_pressed:
                    self.anim_handle.goto_a()
                if (
                    handle.left_just_released
                    and self.app.can_interact()
                    and not handle.hovered
                ):
                    self.anim_handle.goto_a()
                if handle.left_pressed:
                    self.change_volume()
                else:
                    self.slider.valuex = self.app.volume
                if handle.hovered or handle.unhover_pressed:
                    self.app.cursor_hover = True
        return handle

    def action_thread(self):
        if self.app.videoclip_threaded:
            if (
                self.app.music is not None
                and self.app.music_controls.async_videoclip is not None
            ):
                self.app.music_controls.async_videoclip.alive = False
                self.app.music_controls.async_videoclip.thread.join()
        else:
            if (
                self.app.music is not None
                and self.app.music_controls.async_videoclip is not None
            ):
                self.app.music_controls.async_videoclip.first = True
                thread = threading.Thread(
                    target=self.app.music_controls.async_videoclip.loop
                )
                self.app.music_controls.async_videoclip.alive = True
                self.app.music_controls.async_videoclip.thread = thread
                thread.start()
        self.app.videoclip_threaded = not self.app.videoclip_threaded

    def action_discord(self):
        self.app.discord_presence.toggle()

    def action_history(self):
        self.app.modal_state = "history"

    def action_fps(self):
        if self.app.user_framerate == 60:
            self.app.user_framerate = 30
        else:
            self.app.user_framerate = 60

    def action_shuffle(self):
        self.app.shuffle = not self.app.shuffle

    def change_volume(self, value=None):
        if value is None:
            value = self.slider.valuex
        self.app.volume = self.slider.valuex
        pygame.mixer.music.set_volume(self.app.volume)

    def action_mute(self):
        if self.app.volume > 0:
            self.app.vol_before_mute = self.app.volume
            self.app.volume = 0
        else:
            self.app.volume = self.app.vol_before_mute
        pygame.mixer.music.set_volume(self.app.volume)

    def action_loop(self):
        self.app.loops = not self.app.loops

    def action_keybinds(self):
        self.app.modal_state = "keybinds"

    def close(self):
        self.app.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
