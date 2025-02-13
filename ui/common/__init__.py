import os
import mili
import json
import pygame
import typing

if typing.TYPE_CHECKING:
    from MILIMP import MILIMP

DEV_VERSION = 36
PREFERRED_SIZES = (415, 700)
MINIP_PREFERRED_SIZES = 200, 200
UI_SIZES = (480, 720)
SURF = pygame.Surface((10, 10), pygame.SRCALPHA)
USE_FAST_VIDEO = True
VIDEO_SUPPORTED = [
    "mp4",
    "webm",
    "avi",
    "mkv",
    "mov",
    "flv",
    "wmv",
    "m4v",
    "3gp",
    "mpeg",
    "mpg",
    "ogv",
    "mts",
    "ts",
]
CONVERT_SUPPORTED = [
    "aac",
    "m4a",
    "wma",
    "alac",
    "amr",
    "au",
    "snd",
    "mpc",
    "tta",
    "caf",
    "webm",
]
FORMATS = (
    VIDEO_SUPPORTED
    + CONVERT_SUPPORTED
    + ["wav", "mp3", "ogg", "flac", "opus", "wv", "mod", "aiff"]
)
POS_UNSUPPORTED = ["wav", "opus", "wv", "aiff"]
MUSIC_ENDEVENT = pygame.event.custom_type()
HISTORY_LEN = 100
RESIZE_SIZE = 3
WIN_MIN_SIZE = (200, 300)
DISCORD_COOLDOWN = 20000
BIG_COVER_COOLDOWN = 300
SAVE_COOLDOWN = 60000 * 2
TOOLTIP_COOLDOWN = 1200
SPLIT_SCREEN = 1.7
RATIO_MIN = 0.52
BG_CV = 3
MUSIC_CV = 3, 18, 8
LIST_CV = MUSIC_CV
OVERLAY_CV = 30, 50, 20
SBAR_CV = 8
BSBAR_CV = 12
SHANDLE_CV = 18, 25, 15
MODAL_CV = 15
MODALB_CV = 25, 45, 20
MUSICC_CV = 10
CONTROLS_CV = 10, 30, 18
MENU_CV = 6, 20
MENUB_CV = 20, 30, 18
MP_OVERLAY_CV = (50, 50, 50, 150), (80, 80, 80, 150), (30, 30, 30, 150)
MP_BG_FILL = (50, 50, 50, 120)
ALPHA = 180
BORDER_CV = 100
TOPB_CV = 15, 25, 8
GROUP_CV = MUSIC_CV
THUMBNAILS = {
    "120x90": "",
    "320x180": "mq",
    "480x360": "hq",
    "640x480": "sd",
    "1920x1080": "maxres",
}


def cond(app: "MILIMP", it: mili.Interaction, normal, hover, press):
    if not app.can_interact():
        return normal
    if it.left_pressed:
        return press
    elif it.hovered:
        return hover
    return normal


def load_json(path, content_if_not_exist):
    if os.path.exists(path):
        with open(path, "r") as file:
            return json.load(file)
    else:
        with open(path, "w") as file:
            json.dump(content_if_not_exist, file)
            return content_if_not_exist


def write_json(path, content):
    with open(path, "w") as file:
        json.dump(content, file)


def load_icon(name):
    return pygame.image.load(f"appdata/icons/{name}.png").convert_alpha()


def animation(value):
    return mili.animation.ABAnimation(
        0, value, "number", 50, 50, mili.animation.EaseIn()
    )


def handle_arrow_scroll(
    app: "MILIMP", scroll: mili.Scroll, scrollbar: mili.Scrollbar = None
):
    if not app.focused:
        return
    keys = pygame.key.get_pressed()
    amount = 0
    upbind = Keybinds.instance.keybinds["scroll_up"]
    downbind = Keybinds.instance.keybinds["scroll_down"]
    if any([keys[key] for key in upbind.get_keycodes()]):
        amount -= 1
    if any([keys[key] for key in downbind.get_keycodes()]):
        amount += 1
    scroll.scroll(0, amount * 600 * app.delta_time)
    if scrollbar is not None:
        scrollbar.scroll_moved()


def handle_wheel_scroll(
    event: pygame.Event,
    app: "MILIMP",
    scroll: mili.Scroll,
    scrollbar: mili.Scrollbar = None,
):
    if app.split_screen and pygame.mouse.get_pos()[0] > app.split_w:
        return
    scroll.scroll(0, -(event.y * 50) * app.ui_mult)
    if scrollbar is not None:
        scrollbar.scroll_moved()


def parse_music_stem(app: "MILIMP", stem: str):
    if stem.endswith("novideo"):
        stem = stem.removesuffix("novideo")
    if app.strip_youtube_id:
        if len(stem) >= 14:
            if stem.endswith("]") and stem[-13] == "[" and stem[-14] == " ":
                return stem[:-14]
        return stem
    return stem


def format_music_time(position, duration=None):
    string = (
        f"{int(position / 60):.0f}".rjust(2, "0")
        + ":"
        + f"{position % 60:.0f}".rjust(2, "0")
    )
    if duration is not None:
        string += (
            "/"
            + f"{int(duration / 60):.0f}".rjust(2, "0")
            + ":"
            + f"{duration % 60:.0f}".rjust(2, "0")
        )
    return string


class UIComponent:
    def __init__(self, app: "MILIMP"):
        self.app = app
        self.mili: mili.MILI = app.mili
        self.init()

    def init(self): ...

    def ui(self): ...

    def mult(self, size, clamp0=True):
        if not clamp0:
            return int(size * self.app.ui_mult)
        return max(0, int(size * self.app.ui_mult))

    def ui_image_btn(
        self,
        image,
        action,
        anim: mili.animation.ABAnimation,
        size=62,
        br="50",
        tooltip=None,
    ):
        if it := self.mili.element(
            (0, 0, self.mult(size), self.mult(size)),
            {"align": "center", "clip_draw": False},
        ):
            (self.mili.rect if br != "50" else self.mili.circle)(
                {
                    "color": (cond(self.app, it, MODAL_CV, MODALB_CV[1], MODALB_CV[2]),)
                    * 3,
                    "border_radius": br,
                    "pad": self.mult(
                        anim.value / 2 if br != "50" else anim.value / 2, False
                    ),
                }
            )
            self.mili.image(
                image,
                {
                    "smoothscale": True,
                    "cache": mili.ImageCache.get_next_cache(),
                    "pad": self.mult(anim.value, False) + self.mult(3),
                },
            )
            if self.app.can_interact():
                if it.hovered or it.unhover_pressed:
                    self.app.cursor_hover = True
                if it.hovered:
                    self.app.tick_tooltip(tooltip)
                if it.left_just_released:
                    action()
                if it.just_hovered:
                    anim.goto_b()
            if it.just_unhovered:
                anim.goto_a()
            if not it.absolute_hover and not anim.active and anim.value != anim.a:
                anim.goto_a()

    def ui_overlay_btn(
        self,
        anim: mili.animation.ABAnimation,
        on_action,
        image,
        side=0,
        tooltip=None,
        nosplitscreen=False,
        leftmult=0,
    ):
        size = self.mult(40 if nosplitscreen else 50)
        offset = self.mult(5 if nosplitscreen else 8)
        xoffset = offset * 0.6
        if (
            self.app.modal_state == "none"
            and not nosplitscreen
            and (
                (
                    self.app.view_state == "list"
                    and self.app.list_viewer.scrollbar.needed
                    and self.app.list_viewer.modal_state == "none"
                )
                or (
                    self.app.view_state == "playlist"
                    and self.app.playlist_viewer.scrollbar.needed
                    and self.app.playlist_viewer.modal_state == "none"
                )
                or (
                    self.app.view_state == "search"
                    and self.app.yt_search.scrollbar.needed
                    and self.app.yt_search.modal_state == "none"
                )
            )
        ):
            xoffset = offset * 1.6
        xoffset += leftmult * size + leftmult * self.mult(5)
        if nosplitscreen == 2:
            xoffset = self.app.window.size[0] - self.app.split_w - offset - size
        sideoffset = side * size + side * (offset / 2)
        winw = self.app.window.size[0] if nosplitscreen else self.app.split_w
        musiccontrolsh = (
            self.app.music_controls.cont_height
            if (not self.app.split_screen or nosplitscreen)
            else 0
        )
        extrastyle = {}
        if nosplitscreen:
            extrastyle = {"parent_id": 0}
        if it := self.mili.element(
            pygame.Rect(0, 0, size, size).move_to(
                bottomright=(
                    winw - xoffset,
                    self.app.window.size[1]
                    - (0 if nosplitscreen else self.app.tbarh)
                    - offset
                    - musiccontrolsh
                    - sideoffset,
                )
            ),
            {"ignore_grid": True, "clip_draw": False} | extrastyle,
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
                    "cache": mili.ImageCache.get_next_cache(),
                    "pad": self.mult(8 + anim.value / 1.8),
                },
            )
            if self.app.can_interact():
                if it.hovered or it.unhover_pressed:
                    self.app.cursor_hover = True
                if it.hovered:
                    self.app.tick_tooltip(tooltip)
                if it.just_hovered:
                    anim.goto_b()
                if it.left_just_released:
                    on_action()
                    anim.goto_a()
            if it.just_unhovered:
                anim.goto_a()
            if not it.absolute_hover and not anim.active and anim.value != anim.a:
                anim.goto_a()

    def ui_overlay_top_btn(
        self,
        anim: mili.animation.ABAnimation,
        on_action,
        image,
        side,
        sidei=0,
        red=False,
        tooltip=None,
    ):
        if self.app.custom_title:
            size = self.app.tbarh
        else:
            y = self.mili.text_size("Media Player", {"size": self.mult(35)}).y
            size = self.mult(36)
            offset = self.mult(10)
        winw = (
            self.app.split_w if not self.app.custom_borders else self.app.window.size[0]
        )
        if it := self.mili.element(
            pygame.Rect(0, 0, size, size).move_to(
                topleft=(
                    0,
                    0,
                )
                if self.app.custom_title
                else (offset, y / 2 - size / 2 + 5)
            )
            if side == "left"
            else pygame.Rect(0, 0, size, size).move_to(
                topright=(winw - (size * sidei), 0)
                if self.app.custom_title
                else (
                    winw - (offset if side == "right" else offset * 2 + size),
                    y / 2 - size / 2 + 5,
                )
            ),
            {
                "ignore_grid": True,
                "clip_draw": False,
                "z": 9999,
            },
        ):
            if red:
                color = (TOPB_CV[0],) * 3
                if self.app.can_abs_interact():
                    if it.hovered:
                        color = (200, 0, 0)
                    if it.left_pressed:
                        color = (80, 0, 0)
            else:
                color = (cond(self.app, it, *TOPB_CV),) * 3
            animvalue = 0 if side == "left" else anim.value
            self.mili.rect(
                {"color": color, "border_radius": 0, "pad": int(animvalue) / 1.5}
            )
            self.mili.image(
                image,
                {
                    "cache": mili.ImageCache.get_next_cache(),
                    "smoothscale": True,
                    "pad": self.mult(3 + anim.value),
                },
            )
            if self.app.can_interact():
                if it.hovered or it.unhover_pressed:
                    self.app.cursor_hover = True
                if it.hovered:
                    self.app.tick_tooltip(tooltip)
                if it.just_hovered:
                    anim.goto_b()
                if it.left_just_released:
                    on_action()
                    anim.goto_a()
            if it.just_unhovered:
                anim.goto_a()
            if not it.absolute_hover and not anim.active and anim.value != anim.a:
                anim.goto_a()


class Keybinds:
    class Binding:
        class Bind:
            def __init__(self, key, ctrl=False):
                self.key = key
                self.ctrl = ctrl

        def __init__(self, *binds, ctrl=False):
            newbinds = []
            for bind in binds:
                if isinstance(bind, int):
                    newbinds.append(Keybinds.Binding.Bind(bind, ctrl))
                else:
                    newbinds.append(bind)
            self.binds: list[Keybinds.Binding.Bind] = newbinds

        def get_keycodes(self):
            return [bind.key for bind in self.binds]

        def check(self, event: pygame.Event, extra_keys, input_stolen, ignore_input):
            if event.type == pygame.KEYDOWN:
                for key in extra_keys:
                    if event.key == key and (not input_stolen or ignore_input):
                        return True
                for bind in self.binds:
                    if bind.ctrl:
                        if event.key == bind.key and event.mod & pygame.KMOD_CTRL:
                            return True
                    else:
                        if (
                            event.key == bind.key
                            and (not input_stolen or ignore_input)
                            and not event.mod & pygame.KMOD_CTRL
                        ):
                            return True

            return False

    instance: "Keybinds" = None

    def __init__(self, app):
        self.app: "MILIMP" = app
        self.reset()
        Keybinds.instance = self

    @classmethod
    def check(cls, name, event, *extra_keys, ignore_input=False):
        return not cls.instance.app.listening_key and cls.instance.keybinds[name].check(
            event, extra_keys, cls.instance.app.input_stolen, ignore_input
        )

    def reset(self):
        Binding = Keybinds.Binding
        self.keybinds = {
            "confirm": Binding(pygame.K_RETURN),
            "toggle_settings": Binding(pygame.K_s),
            "music_maximize": Binding(pygame.K_F11),
            "extra_controls": Binding(pygame.K_TAB),
            "volume_up": Binding(pygame.K_UP, pygame.K_KP8),
            "volume_down": Binding(pygame.K_DOWN, pygame.K_KP2),
            "pause_music": Binding(pygame.K_SPACE, pygame.K_KP_ENTER),
            "previous_track": Binding(pygame.K_LEFT, pygame.K_KP4),
            "next_track": Binding(pygame.K_RIGHT, pygame.K_KP6),
            "back_5_s": Binding(pygame.K_LEFT, pygame.K_KP4, ctrl=True),
            "skip_5_s": Binding(pygame.K_RIGHT, pygame.K_KP6, ctrl=True),
            "quit": Binding(pygame.K_q, ctrl=True),
            "new/add": Binding(pygame.K_a, ctrl=True),
            "save": Binding(pygame.K_s, ctrl=True),
            "open_history": Binding(pygame.K_h, ctrl=True),
            "open_keybinds": Binding(pygame.K_k, ctrl=True),
            "toggle_search": Binding(pygame.K_f, ctrl=True),
            "erase_input": Binding(pygame.K_BACKSPACE, ctrl=True),
            "change_cover": Binding(pygame.K_c, ctrl=True),
            "end_music": Binding(pygame.K_e, ctrl=True),
            "rewind_music": Binding(pygame.K_r, ctrl=True),
            "toggle_miniplayer": Binding(pygame.K_d, ctrl=True),
            "music_fullscreen": Binding(pygame.K_F11, ctrl=True),
            "minimize_window": Binding(pygame.K_l, ctrl=True),
            "maximize_window": Binding(pygame.K_m, ctrl=True),
            "clean_controls_ui": Binding(pygame.K_F1),
            "refresh_yt_search": Binding(pygame.K_x, ctrl=True),
            "scroll_up": Binding(pygame.K_PAGEUP, pygame.K_KP9),
            "scroll_down": Binding(pygame.K_PAGEDOWN, pygame.K_KP3),
        }
        self.default_keybinds = self.keybinds.copy()

    def load_from_data(self, data: dict):
        for name, bdata in data.items():
            if name not in self.keybinds:
                continue
            binding = self.keybinds[name]
            binding.binds = [Keybinds.Binding.Bind(d["key"], d["ctrl"]) for d in bdata]

    def get_save_data(self):
        return {
            name: [{"key": bind.key, "ctrl": bind.ctrl} for bind in binding.binds]
            for name, binding in self.keybinds.items()
        }


class Icons:
    def load(self):
        self.close = load_icon("close")
        self.playlistadd = load_icon("playlist_add")
        self.music_cover = load_icon("music")
        self.playlist_cover = load_icon("playlist")
        self.settings = load_icon("settings")
        self.loading = load_icon("loading")
        self.confirm = load_icon("confirm")
        self.back = load_icon("back")
        self.delete = load_icon("delete")
        self.rename = load_icon("edit")
        self.loopon = load_icon("loopon")
        self.loopoff = load_icon("loopoff")
        self.minimize = load_icon("minimize")
        self.maximize = load_icon("maximize")
        self.resize = load_icon("resize")
        self.reset = load_icon("reset")
        self.playbars = load_icon("playbars")
        self.search = load_icon("search")
        self.error = load_icon("error")
        self.up = load_icon("up")
        self.down = load_icon("down")
        self.uploadf = load_icon("uploadf")
        self.brush = load_icon("brush")
        self.borderless = load_icon("borderless")
        self.minip_back = pygame.transform.flip(load_icon("opennew"), True, False)
        self.play = load_icon("play")
        self.pause = load_icon("pause")
        self.skip_next = load_icon("skip_next")
        self.skip_previous = load_icon("skip_previous")
        self.skip5 = load_icon("skip5")
        self.back5 = load_icon("back5")
        self.fullscreen = load_icon("fullscreen")
        self.dots = load_icon("dots")
        self.minip = load_icon("opennew")
        self.maxip = pygame.transform.flip(self.minip, True, True)
        self.minipd = pygame.transform.flip(self.minip, False, True)
        self.fullscreenclose = load_icon("fullscreenclose")
        self.upload = load_icon("upload")
        self.change_cover = load_icon("cover")
        self.forward = load_icon("forward")
        self.searchoff = load_icon("searchoff")
        self.backspace = load_icon("backspace")
        self.convert = load_icon("convert")
        self.remove = load_icon("playlist_remove")
        self.rows = load_icon("rows")
        self.columns = load_icon("columns")
        self.vol0 = load_icon("vol0")
        self.vol1 = load_icon("vol1")
        self.vollow = load_icon("vollow")
        self.shuffleon = load_icon("shuffleon")
        self.shuffleoff = load_icon("shuffleoff")
        self.fps30 = load_icon("fps30")
        self.fps60 = load_icon("fps60")
        self.history = load_icon("history")
        self.discordon = load_icon("discordon")
        self.discordoff = load_icon("discordoff")
        self.keybinds = load_icon("keyboard")
        self.threadon = load_icon("threadon")
        self.threadoff = load_icon("threadoff")
        self.link = load_icon("link")
        self.refresh = load_icon("refresh")
        self.account = load_icon("account")
        self.download = load_icon("download")
        self.merge = load_icon("merge")
        self.download_file = load_icon("download_file")
        self.copy = load_icon("copy")
        self.infoon = load_icon("infoon")
        self.infooff = load_icon("infooff")
        self.video_track = load_icon("video_track")
        self.audio_track = load_icon("audio_track")
        self.search_video = load_icon("search_video")
        self.search_more = load_icon("search_more")


ICONS = Icons()
