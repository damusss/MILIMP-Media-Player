import mili
import pygame
import zipfile
import webbrowser
from ui.common import *
import tkinter.filedialog as filedialog


class SettingsUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.anim_handle = animation(-3)
        self.anim_info = animation(-3)
        self.anim_log = animation(-3)
        self.anims = [animation(-3) for i in range(15)]
        self.cache = mili.ImageCache()
        self.slider = mili.Slider(
            {"lock_y": True, "handle_size": (10, 10), "drag_area": False}
        )
        self.bar_controlled = False

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 130000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.close()
            self.mili.image(
                SURF, {"fill": True, "fill_color": MENU_BG_COL, "cache": self.cache}
            )

            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": "50" if self.app.split_w > 1200 else "80",
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

    def ui_line(self):
        self.mili.hline_element(
            {"size": 1, "color": (120,) * 3},
            (0, 0, 0, 1),
            {"fillx": "80", "align": "center"},
        )

    def ui_modal_content(self):
        with self.mili.begin(None, mili.RESIZE | mili.X | mili.CENTER | {"pady": 0}):
            self.ui_image_btn(
                ICONS.log,
                self.action_notifs,
                self.anim_log,
                size=30,
                br="30",
                tooltip="Show application notification log",
            )
            self.mili.text_element(
                "Settings",
                {"size": self.mult_fs(26)},
                None,
                mili.CENTER | {"blocking": None},
            )
            self.ui_image_btn(
                ICONS.infooff,
                self.action_metadata,
                self.anim_info,
                size=30,
                tooltip="Show application state information",
            )
        self.ui_slider()
        self.ui_buttons_top()
        self.ui_line()
        self.ui_buttons_middle()
        self.ui_line()
        self.ui_buttons_bottom()

    def ui_buttons_top(self):
        self.mili.id_checkpoint(ID_OFFSET + 131000)
        with self.mili.begin(
            None,
            {
                "fillx": True,
                "resizey": True,
                "axis": "x",
                "clip_draw": False,
                "align": "center",
                "blocking": None,
                "layout": "grid",
                "grid_align": "center",
            }
            | mili.PADLESS,
        ):
            vol_image = ICONS.vol0
            if self.state.volume >= 0.5:
                vol_image = ICONS.vol1
            elif self.state.volume > 0.05:
                vol_image = ICONS.vollow
            self.ui_image_btn(
                vol_image,
                self.state.mute,
                self.anims[0],
                tooltip="Mute/unmute the music",
            )

            self.ui_image_btn(
                ICONS.loopon if self.state.loops else ICONS.loopoff,
                self.action_loop,
                self.anims[1],
                br="50" if not self.state.loops else "5",
                tooltip="Disable playlist looping"
                if self.state.loops
                else "Enable playlist looping",
            )
            self.ui_image_btn(
                ICONS.shuffleon if self.state.shuffle else ICONS.shuffleoff,
                self.action_shuffle,
                self.anims[2],
                br="50" if not self.state.shuffle else "5",
                tooltip="Enable playlist shuffling"
                if self.state.shuffle
                else "Enable playlist shuffle",
            )
            self.ui_image_btn(
                ICONS.queue,
                self.action_queue,
                self.anims[14],
                br="50",
                tooltip="Open queue",
            )

    def ui_buttons_middle(self):
        with self.mili.begin(
            None,
            {
                "fillx": True,
                "resizey": True,
                "axis": "x",
                "layout": "grid",
                "clip_draw": False,
                "align": "center",
                "blocking": None,
                "grid_align": "center",
            }
            | mili.PADLESS,
        ):
            self.ui_image_btn(
                ICONS.health,
                self.action_health_check,
                self.anims[13],
                br="50",
                tooltip="View unused files",
            )
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
            self.ui_image_btn(
                ICONS.backup_save,
                self.action_backup_save,
                self.anims[11],
                br="5",
                tooltip="Create a backup",
            )

    def ui_buttons_bottom(self):
        with self.mili.begin(
            None,
            {
                "fillx": True,
                "resizey": True,
                "axis": "x",
                "layout": "grid",
                "clip_draw": False,
                "align": "center",
                "blocking": None,
                "grid_align": "center",
            }
            | mili.PADLESS,
        ):
            self.ui_image_btn(
                ICONS.gpuon if self.app.save_use_renderer else ICONS.gpuoff,
                self.action_gpu,
                self.anims[10],
                br="15",
                tooltip=(
                    "Disable hardware acceleration (requires restart)"
                    if self.app.save_use_renderer
                    else "Enable hardware acceleration (requires restart)"
                ),
            )
            self.ui_image_btn(
                ICONS.t_two if self.app.universal_font else ICONS.t_one,
                self.action_font,
                self.anims[5],
                br="15",
                tooltip=(
                    "Use YT Music font"
                    if self.app.universal_font
                    else "Use universal font"
                ),
            )
            self.ui_image_btn(
                ICONS.fps60 if self.state.user_framerate == 60 else ICONS.fps30,
                self.action_fps,
                self.anims[6],
                br="15",
                tooltip="Set the framerate to 30"
                if self.state.user_framerate == 60
                else "Set the framerate to 60",
            )
            self.ui_image_btn(
                ICONS.backup_load,
                self.action_backup_load,
                self.anims[12],
                br="5",
                tooltip="Load a previously saved backup",
            )
            self.ui_image_btn(
                ICONS.video_track if self.state.videoclip_on else ICONS.video_off,
                self.action_videoclip,
                self.anims[8],
                br="15",
                tooltip="Disable videoclip"
                if self.state.videoclip_threaded
                else "Enable videoclip",
            )
            self.ui_image_btn(
                ICONS.threadon if self.state.videoclip_threaded else ICONS.threadoff,
                self.state.toggle_thread,
                self.anims[9],
                tooltip="Disable videoclip multithreading"
                if self.state.videoclip_threaded
                else "Enable videoclip multithreading",
            )
            self.ui_image_btn(
                ICONS.discordoff
                if not self.app.discord_presence.active
                else ICONS.discordon,
                self.action_discord,
                self.anims[7],
                tooltip="Disable the discord presence"
                if self.app.discord_presence.active
                else "Enable the discord presence",
            )

    def ui_slider(self):
        self.slider.style["handle_size"] = self.mult(40), self.mult(40)

        with self.mili.begin(
            (0, 0, 0, self.mult(10)),
            {"align": "center", "fillx": "94"} | self.slider.area_style,
        ) as bar:
            self.slider.update_area(bar)
            self.mili.rect({"color": (30,) * 3})

            if self.state.volume > 0:
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
                self.state.change_volume(volume)
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
                    self.state.change_volume(self.slider.valuex)
                else:
                    self.slider.valuex = self.state.volume
                if handle.hovered or handle.unhover_pressed:
                    self.app.cursor_hover = True
        return handle

    def action_health_check(self):
        self.app.modal_state = "health_check"
        self.app.health_check.refresh()

    def action_backup_load(self):
        button = pygame.display.message_box(
            "Confirm loading backup",
            "After you select a ZIP backup, this action will replace the selected content. Files in the data folder that are not present in the backup won't be deleted. You need to make the backup with the application for it to work correctly. It is advised to create a backup of the current state before this operation in case anything goes wrong.",
            "info",
            buttons=["Load Backup", "Cancel"],
        )
        if button == 1:
            return
        path = filedialog.askopenfilename(
            defaultextension="zip", filetypes=[(".zip", "ZIP")]
        )
        if not path:
            return
        try:
            with zipfile.ZipFile(
                path, "r", zipfile.ZIP_DEFLATED, compresslevel=9
            ) as zfile:
                files = zfile.namelist()
                print(files)
                # BACKUP
        except Exception as e:
            self.app.save()
            messagebox_notify(
                self.app,
                NOTIF.ERROR,
                "Loading backup failed",
                f"Loading the backup failed because of the exception: '{e}', therefore it has been aborted and the current app state has been saved to mitigate damages.",
                "error",
                buttons=["Understood"],
            )
            return
        pygame.display.message_box(
            "Backup loaded",
            "The backup loaded succesfully. The app will now terminate without saving, to avoid overriding the data. The new data from the backup will be available at the next startup.",
            "info",
            buttons=["Understood"],
        )
        self.app.quit_abort()

    def action_backup_save(self):
        self.app.modal_state = "backup_save"
        self.app.backup_save.refresh_size()

    def action_queue(self):
        self.app.modal_state = "queue"

    def action_notifs(self):
        self.app.modal_state = "notifs"

    def action_metadata(self):
        self.app.modal_state = "state_info"

    def action_font(self):
        self.app.universal_font = not self.app.universal_font
        mili.clear_font_cache()
        if self.app.universal_font and not os.path.exists("appdata/universal.ttf"):
            btn = pygame.display.message_box(
                "Missing universal font file",
                "For unknown reasons the appdata folder is missing the 'universal.ttf' font file. If you deleted it by accident you can get it back from 'https://github.com/satbyy/go-noto-universal/releases/' (pick the latest regular).",
                "error",
                None,
                ("Understood", "Open Link"),
            )
            if btn == 1:
                webbrowser.open("https://github.com/satbyy/go-noto-universal/releases/")
            self.app.universal_font = False
        self.app.apply_font()

    def action_gpu(self):
        self.app.save_use_renderer = not self.app.save_use_renderer

    def action_videoclip(self):
        self.state.videoclip_on = not self.state.videoclip_on

    def action_discord(self):
        self.app.discord_presence.toggle()

    def action_history(self):
        self.app.modal_state = "history"

    def action_fps(self):
        if self.state.user_framerate == 60:
            self.state.user_framerate = 30
        else:
            self.state.user_framerate = 60

    def action_shuffle(self):
        self.state.shuffle = not self.state.shuffle

    def action_loop(self):
        self.state.loops = not self.state.loops

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
