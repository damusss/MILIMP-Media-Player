import pathlib
import shutil
import traceback
from ui.common import *
from ui.common.data import (
    VirtualMusic,
    VirtualPlaylist,
    Entryline,
    VirtualPlayingMusic,
)


class ExplorerUI(UIComponent):
    def init(self):
        self.anim_back = animation(-3)
        self.anim_search = animation(-5)
        self.search_active = False
        self.search_entryline = Entryline(
            self.app, "Enter search...", False, CONTROLS_CV[0] + 5, CONTROLS_CV[1]
        )
        self.path_entryline = Entryline(
            self.app,
            "Enter folder path and refresh...",
            False,
            CONTROLS_CV[0] + 5,
            CONTROLS_CV[1],
            specialspaces=True,
        )
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(
            self.scroll, {"short_size": 8, "padding": 3, "border_dist": 3, "axis": "y"}
        )
        self.sbar_size = self.scrollbar.style["short_size"]
        self.modal_state = "none"
        self.playlist = None
        self.last_path = None
        self.history = []
        self.history_idx = 0
        self.ffplay_dep = shutil.which("ffplay")
        self.favorites = []

    def ui_check(self):
        self.modal_state = "none"

    def ui_top_buttons(self):
        if self.app.modal_state != "none" or self.modal_state != "none":
            return
        self.ui_overlay_top_btn(
            self.anim_back, self.back, ICONS.back, "left", tooltip="Back"
        )

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 60000)

        if self.modal_state == "none" and self.app.modal_state == "none":
            handle_arrow_scroll(self.app, self.scroll, self.scrollbar)
        self.ui_title()
        self.ui_container()

    def ui_container(self):
        with self.mili.begin(
            (0, 0, self.app.split_w, 0),
            {"filly": True},
        ) as scroll_cont:
            if len(self.playlist.folders) > 0 or len(self.playlist.tracks) > 0:
                self.scroll.update(scroll_cont)
                self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                self.scrollbar.update(scroll_cont)
                self.ui_scrollbar()
                for folder in self.playlist.folders:
                    self.ui_folder(folder)
                for track in self.playlist.tracks:
                    self.ui_track(track)
                details = ""
                if len(self.playlist.folders) > 0:
                    details += f"{len(self.playlist.folders)} folder{'s' if len(self.playlist.folders) > 1 else ''}"
                    if len(self.playlist.tracks) > 0:
                        details += ", "
                if len(self.playlist.tracks) > 0:
                    details += f"{len(self.playlist.tracks)} track{'s' if len(self.playlist.tracks) > 1 else ''}"
                self.mili.text_element(
                    details,
                    {"size": self.mult_fs(19), "color": (170,) * 3},
                    None,
                    {"offset": self.scroll.get_offset(), "blocking": None},
                )
            else:
                self.mili.text_element(
                    "No track matches your search"
                    if self.search_active
                    else "No tracks or subfolders found",
                    {"size": self.mult_fs(20), "color": (200,) * 3},
                    None,
                    {"align": "center", "blocking": None},
                )

    def ui_folder(self, folder):
        with self.ui_list_cont() as cont:
            if cont.data.absolute_rect.colliderect(((0, 0), self.app.split_size)):
                self.ui_list_bg(cont)
                imgsize = self.mult(EXPLORER_ITEM_H - 5)
                self.ui_list_cover(ICONS.folder, imgsize)
                self.mili.text_element(
                    folder,
                    {
                        "size": self.mult_fs(18),
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
                        self.app.split_w / 1.1 - imgsize,
                        self.mult(EXPLORER_ITEM_H) / 1.1,
                    ),
                    {"blocking": False},
                )
                if self.app.can_interact():
                    if cont.hovered:
                        self.app.cursor_hover = True
                        self.app.tick_tooltip("Enter folder")
                    if cont.left_clicked:
                        # self.history_append(self.last_path)
                        self.enter_folder(self.playlist.path / folder)
            else:
                self.mili.element(
                    (0, 0, 0, self.mult(EXPLORER_ITEM_H - 3 * 2)), {"blocking": False}
                )

    def ui_track(self, track: VirtualMusic):
        with self.ui_list_cont() as cont:
            if cont.data.absolute_rect.colliderect(((0, 0), self.app.split_size)):
                self.ui_list_bg(cont, track)
                imgsize = self.mult(EXPLORER_ITEM_H - 5)
                self.ui_list_cover(track.cover, imgsize)
                self.mili.text_element(
                    track.path.name,
                    {
                        "size": self.mult_fs(18),
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
                        self.app.split_w / 1.1 - imgsize,
                        self.mult(EXPLORER_ITEM_H) / 1.1,
                    ),
                    {"blocking": False},
                )
                if self.app.can_interact():
                    if cont.hovered:
                        self.app.cursor_hover = True
                        self.app.tick_tooltip("Play track")
                    if cont.left_clicked:
                        self.action_play_track(track)
            else:
                self.mili.element(
                    (0, 0, 0, self.mult(EXPLORER_ITEM_H - 3 * 2)), {"blocking": False}
                )

    def ui_list_cover(self, image, imgsize):
        self.mili.image_element(
            image,
            {"cache": get_img_cache()},
            (0, 0, imgsize, imgsize),
            {"blocking": False},
        )

    def ui_list_cont(self):
        return self.mili.begin(
            None,
            {
                "fillx": "100" if not self.scrollbar.needed else "98",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "padx": self.mult(5),
                "axis": "x",
                "align": "center",
                "anchor": "first",
                "size_clamp": {"min": (None, self.mult(60))},
                "pad": 3,
            },
        )

    def ui_list_bg(self, cont, track: VirtualMusic = None):
        forcehover = (
            track is not None
            and self.state.music is not None
            and self.state.music.realstem == track.path.stem
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

    def ui_title(self):
        self.mili.text_element(
            "Explorer",
            {"size": self.mult_fs(30)},
            None,
            {"align": "center", "blocking": None},
        )
        self.ui_path()
        if self.search_active:
            self.ui_line("50")
        self.ui_line("49.5")

    def ui_path(self):
        with self.mili.begin(
            (0, 0, self.app.split_w - self.mult(20), 0),
            {"resizey": True, "blocking": None, "align": "center"}
            | mili.PADLESS
            | mili.X,
        ):
            size = self.mult(30)
            self.ui_entry_btn(
                ICONS.up_arrow,
                self.action_folder_up,
                "Enter parent folder",
                self.last_path.parent != self.last_path,
            )
            self.ui_entry_btn(
                ICONS.back, self.action_history_back, "Back", self.history_idx > 0
            )
            self.ui_entry_btn(
                ICONS.back_back,
                self.action_history_forward,
                "Forward",
                self.history_idx < len(self.history) - 1,
            )
            self.path_entryline.ui(
                (0, 0, 0, size),
                {"fillx": True},
            )
            self.ui_entry_btn(
                ICONS.favorite
                if self.playlist.path in self.favorites
                else ICONS.not_favorite,
                self.action_favorite,
                "Remove from favorites"
                if self.playlist.path in self.favorites
                else "Add to favorites",
            )
            self.ui_entry_btn(
                ICONS.refresh, self.action_refresh_folder, "Enter selected folder"
            )

    def ui_entry_btn(self, icon, action, tooltip, condition=True):
        size = self.mult(30)
        if it := self.mili.element((0, 0, size, size)):
            self.mili.rect(
                {
                    "color": (cond(self.app, it, *OVERLAY_CV),) * 3
                    if condition
                    else (OVERLAY_CV[2],) * 3,
                    "border_radius": 0,
                }
            )
            self.mili.image(
                icon,
                {"cache": get_img_cache()},
            )
            if self.app.can_interact():
                if it.left_just_released and condition:
                    action()
                if (it.hovered or it.unhover_pressed) and condition:
                    self.app.cursor_hover = True
                if it.hovered and condition:
                    self.app.tick_tooltip(tooltip)

    def ui_line(self, perc):
        self.mili.line_element(
            [(f"-{perc}", 0), (f"{perc}", 0)],
            {"size": 1, "color": (100,) * 3},
            (0, 0, 0, self.mult(7)),
            {"fillx": True, "blocking": None},
        )

    def history_append(self, path):
        if len(self.history) >= EXPLORER_HISTORY_LEN:
            self.history.pop(0)
        self.history.append(path)
        self.history_idx = len(self.history) - 1

    def action_favorite(self):
        if self.playlist.path in self.favorites:
            self.favorites.remove(self.playlist.path)
        else:
            self.favorites.append(self.playlist.path)

    def unfavorite(self, path):
        self.favorites.remove(path)

    def action_play_track(self, track: VirtualMusic):
        try:
            playling_music = VirtualPlayingMusic(
                track.path, track.cover, track.isvideo, self.last_path.name
            )
        except Exception as e:
            pygame.display.message_box(
                "Failed to play track",
                f"Playing '{track.path}' failed due to an unexpected error: '{e}'",
                "error",
                buttons=["Understood"],
            )
            return
        if playling_music.require_ffplay and self.ffplay_dep is None:
            pygame.display.message_box(
                "FFPLAY dependency not found",
                "Playing tracks not supported by pygame from folders without adding them to a playlist requires the ffplay dependency. The binary usally comes shipped with ffmpeg, so make sure they are both available and added to PATH.",
                "error",
                buttons=["Understood"],
            )
            return
        self.state.play_music(playling_music, 0)

    def action_folder_up(self):
        if self.last_path.parent != self.last_path:
            self.enter_folder(self.last_path.parent)

    def action_history_back(self):
        if self.history_idx > 0:
            self.history_idx -= 1
            self.enter_folder(self.history[self.history_idx], False)

    def action_history_forward(self):
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self.enter_folder(self.history[self.history_idx], False)

    def action_refresh_folder(self):
        folder = self.path_entryline.text_strip
        if os.path.exists(folder):
            self.enter_folder(pathlib.Path(folder).absolute())
        else:
            self.path_entryline.set_text(self.playlist.path)

    def enter_folder(self, path=None, history=True):
        if path is None:
            path = self.last_path
        path = pathlib.Path(path)
        prev = self.last_path
        self.last_path = path
        if self.app.view_state != "explorer":
            self.app.change_state("explorer")
        self.playlist = VirtualPlaylist(path)
        self.path_entryline.set_text(self.playlist.path)
        if history and path != prev:
            if self.history_idx != len(self.history) - 1:
                self.history = self.history[: self.history_idx]
            self.history_append(self.last_path)

    def back(self):
        self.app.change_state("list")
        self.scroll.set_scroll(0, 0)

    def event(self, event):
        self.path_entryline.event(event)
        if (
            self.search_active
            and self.app.can_interact()
            and self.modal_state == "none"
            and self.app.modal_state == "none"
        ):
            self.search_entryline.event(event)
        if event.type == pygame.MOUSEWHEEL:
            if self.modal_state == "none" and self.app.modal_state == "none":
                handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)
        if self.app.listening_key or not self.app.can_interact():
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search_active:
                    ...
                # self.stop_searching()
                else:
                    self.back()
            if self.path_entryline.focused and event.key == pygame.K_RETURN:
                self.action_refresh_folder()
            if event.mod & pygame.KMOD_CTRL:
                if event.key == pygame.K_UP:
                    self.action_history_back()
                if event.key == pygame.K_DOWN:
                    self.action_history_forward()
