import mili
import pygame
import threading
from ui.common.data import (
    YTVideoResult,
    YTVideoFormat,
)
from ui.common.yt_actions import (
    get_yt_formats_async,
    download_yt_async,
    merge_yt_async,
    check_ffmpeg,
    download_yt_default_async,
)
from ui.common import *


class YTDownloadUI(UIComponent):
    def init(self):
        self.extra_anim = animation(-3)
        self.anims = [animation(-5) for i in range(3)]
        self.cache = mili.ImageCache()
        self.video: YTVideoResult = None
        self.getting_formats = False
        self.formats: list[YTVideoFormat] = []
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(self.scroll, {"short_size": 7, "axis": "y"})
        self.sbar_size = self.scrollbar.style["short_size"]
        self.error = None
        self.chosen: list[YTVideoFormat] = []
        self.last_chosen = None
        self.ffmpeg_version = None
        self.show_extra = False

    def ui(self):
        if self.video is None:
            return
        handle_arrow_scroll(self.app, self.scroll, self.scrollbar)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": True} | mili.PADLESS | mili.CENTER,
        ) as shadowit:
            if shadowit.left_just_released:
                self.close()
                return
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.cache}
            )
            perc = 40 if self.app.split_w > 1200 else 80
            with self.mili.begin(
                (0, 0, 0, 0),
                {
                    "fillx": f"{perc}",
                    "filly": "80",
                    "align": "center",
                    "offset": (
                        0,
                        -self.app.tbarh
                        - (self.app.music_controls.cont_height / 2.7)
                        * (not self.app.split_screen),
                    ),
                    "blocking": None,
                },
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                with self.mili.begin(
                    None, mili.RESIZE | mili.X | mili.CENTER | {"pady": 0}
                ):
                    self.mili.text_element(
                        "Download Video",
                        {"size": self.mult(26)},
                        None,
                        mili.CENTER | {"blocking": None},
                    )
                    self.ui_image_btn(
                        ICONS.infoon if self.show_extra else ICONS.infooff,
                        self.action_show_more,
                        self.extra_anim,
                        size=30,
                        tooltip=f"{'Hide' if self.show_extra else 'Show'} id, codec and more details",
                    )
                if self.getting_formats or self.error:
                    self.mili.text_element(
                        self.error if self.error else "Getting formats...",
                        {
                            "color": "red" if self.error else (150,) * 3,
                            "size": self.mult(17),
                            "slow_grow": True,
                            "growx": False,
                            "wraplen": "100",
                        },
                        (0, 0, mili.percentage(perc, self.app.split_w), 0),
                        {
                            "align": "center",
                            "fillx": True,
                            "blocking": None,
                            "offset": self.scroll.get_offset(),
                        },
                    )
                if self.error:
                    self.ui_overlay_btn(
                        self.anims[0],
                        self.close,
                        ICONS.close,
                        tooltip="Close",
                    )
                    return
                if len(self.formats) > 0:
                    self.ui_formats(perc)
                if len(self.chosen) > 0:
                    merge = self.can_merge()
                    with self.mili.begin(None, mili.RESIZE | mili.X | mili.CENTER):
                        self.ui_image_btn(
                            ICONS.download,
                            self.action_start_download,
                            self.anims[1],
                            size=40,
                            tooltip="Start download",
                        )
                        if merge:
                            self.ui_image_btn(
                                ICONS.merge,
                                self.action_start_merge,
                                self.anims[2],
                                size=40,
                                br="15",
                                tooltip="Download and merge tracks",
                            )
                elif not self.getting_formats:
                    self.mili.text_element(
                        "Select at least one format to download",
                        {
                            "color": (150,) * 3,
                            "size": self.mult(15),
                            "slow_grow": True,
                            "growx": False,
                            "wraplen": "100",
                        },
                        (0, 0, mili.percentage(perc, self.app.split_w), 0),
                        {"align": "center", "fillx": True, "blocking": None},
                    )

            self.ui_overlay_btn(
                self.anims[0],
                self.close,
                ICONS.close,
                tooltip="Close",
            )

    def ui_help(self, perc):
        self.mili.text_element(
            self.error
            if self.error
            else "If you select one video track and one audio track you have the option to merge them",
            {
                "color": "red" if self.error else (150,) * 3,
                "size": self.mult(14),
                "slow_grow": True,
                "growx": False,
                "wraplen": "100",
            },
            (0, 0, mili.percentage(perc, self.app.split_w), 0),
            {
                "align": "center",
                "fillx": True,
                "blocking": None,
                "offset": self.scroll.get_offset(),
            },
        )

    def ui_formats(self, perc):
        self.mili.id_checkpoint(20000)
        with self.mili.begin(
            None,
            {"fillx": True, "filly": True},
        ) as cont:
            self.scroll.update(cont)
            self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
            self.scrollbar.update(cont)
            lasttype = None
            first = True
            for fmt in self.formats:
                if first:
                    self.ui_help(perc)
                    first = False
                if fmt.type != lasttype:
                    size = self.mult(22)
                    with self.mili.begin(
                        None,
                        mili.RESIZE
                        | mili.CENTER
                        | mili.PADLESS
                        | mili.X
                        | {"offset": self.scroll.get_offset()},
                    ):
                        self.mili.image_element(
                            ICONS.video_track
                            if fmt.type in ["video", "full"]
                            else ICONS.audio_track,
                            {"cache": mili.ImageCache.get_next_cache()},
                            (0, 0, size, size),
                        )
                        title = {
                            "full": "Audio & Video",
                            "audio": "Audio Only",
                            "video": "Video Only",
                        }[fmt.type]
                        self.mili.text_element(
                            f"{title} Formats",
                            {"size": self.mult(18)},
                            None,
                        )

                        self.mili.image_element(
                            ICONS.audio_track
                            if fmt.type in ["audio", "full"]
                            else ICONS.video_track,
                            {"cache": mili.ImageCache.get_next_cache()},
                            (0, 0, size, size),
                        )
                    self.ui_column_info()
                self.ui_format(fmt)
                if self.show_extra and fmt.extra_data is not None:
                    self.mili.text_element(
                        fmt.extra_data,
                        {"growx": False, "size": self.mult(12), "color": (160,) * 3},
                        None,
                        {"fillx": True},
                    )
                lasttype = fmt.type

            self.ui_scrollbar()

    def ui_format(self, fmt: YTVideoFormat):
        with self.mili.begin(
            None,
            {
                "resizey": True,
                "fillx": "98" if self.scrollbar.needed else True,
                "axis": "x",
                "pad": 0,
                "offset": self.scroll.get_offset(),
            },
        ) as fmtcont:
            chosen = fmt in self.chosen
            if fmtcont.hovered:
                self.app.cursor_hover = True
                self.app.tick_tooltip("Deselect format" if chosen else "Select format")
            if fmtcont.left_just_released:
                if chosen:
                    self.chosen.remove(fmt)
                else:
                    self.chosen.append(fmt)
            self.mili.rect(
                {
                    "color": (
                        MENUB_CV[1] if chosen else cond(self.app, fmtcont, *MENUB_CV),
                    )
                    * 3
                }
            )
            for attrname in ["type", "ext", "res", "filesize", "fps"]:
                with self.mili.begin(
                    None,
                    {
                        "fillx": "80" if attrname == "type" else True,
                        "resizey": True,
                        "pady": 0,
                        "padx": 3 if attrname == "type" else 0,
                        "anchor": "first" if attrname == "type" else "center",
                        "axis": "x",
                        "blocking": False,
                    },
                ):
                    value = getattr(fmt, attrname)
                    if value is None:
                        continue
                    if attrname == "type":
                        if fmt.default:
                            self.mili.text_element(
                                "DEFAULT",
                                {"size": self.mult(15)},
                                None,
                                {"blocking": False},
                            )
                        else:
                            size = self.mult(22)
                            if fmt.type == "full":
                                self.mili.begin(
                                    None, mili.RESIZE | mili.PADLESS | mili.X
                                )
                            if fmt.type in ["video", "full"]:
                                self.mili.image_element(
                                    ICONS.video_track,
                                    {"cache": mili.ImageCache.get_next_cache()},
                                    (0, 0, size, size),
                                )
                            if fmt.type in ["audio", "full"]:
                                self.mili.image_element(
                                    ICONS.audio_track,
                                    {"cache": mili.ImageCache.get_next_cache()},
                                    (0, 0, size, size),
                                )
                            if fmt.type == "full":
                                self.mili.end()
                    else:
                        if attrname == "ext":
                            value = f".{value}"
                        if attrname == "fps":
                            value = f"{value}FPS"
                        self.mili.text_element(
                            value, {"size": self.mult(15)}, None, {"blocking": False}
                        )

    def ui_column_info(self):
        with self.mili.begin(
            None,
            {
                "resizey": True,
                "fillx": "98" if self.scrollbar.needed else True,
                "axis": "x",
                "pad": 0,
                "offset": self.scroll.get_offset(),
            },
        ):
            for attrname in [
                "TYPE",
                "EXTENSION",
                "RESOLUTION",
                "FILE SIZE",
                "FRAMERATE",
            ]:
                with self.mili.begin(
                    None,
                    {
                        "fillx": "80" if attrname == "TYPE" else True,
                        "resizey": True,
                        "pad": 0,
                        "anchor": "first" if attrname == "TYPE" else "center",
                        "axis": "x",
                        "blocking": False,
                    },
                ):
                    self.mili.text_element(
                        attrname,
                        {"size": self.mult(12), "color": (120,) * 3},
                        None,
                        {"blocking": False},
                    )

    def ui_scrollbar(self):
        if self.scrollbar.needed:
            with self.mili.begin(
                self.scrollbar.bar_rect, self.scrollbar.bar_style | {"blocking": None}
            ):
                self.mili.rect({"color": (BSBAR_CV,) * 3})
                if handle := self.mili.element(
                    self.scrollbar.handle_rect, self.scrollbar.handle_style
                ):
                    self.mili.rect(
                        {"color": (cond(self.app, handle, *SHANDLE_CV) * 1.2,) * 3}
                    )
                    self.scrollbar.update_handle(handle)
                    if (
                        handle.hovered or handle.unhover_pressed
                    ) and self.app.can_interact():
                        self.app.cursor_hover = True
                        self.app.tick_tooltip(None)

    def enter(self, video: YTVideoResult):
        self.video = video
        if self.video.formats is not None:
            self.formats = self.video.formats
        else:
            self.getting_formats = True
            thread = threading.Thread(
                target=get_yt_formats_async, args=(self.app.yt_search, self, self.video)
            )
            thread.start()

    def close(self):
        self.app.yt_search.modal_state = "none"
        self.getting_formats = False
        self.formats = []
        self.error = None
        self.chosen = []
        self.last_chosen = None

    def can_merge(self):
        vid = False
        aud = False
        for fmt in self.chosen:
            if fmt.type == "audio":
                aud = True
            if fmt.type == "video":
                vid = True
        return vid and aud and len(self.chosen) == 2

    def action_show_more(self):
        self.show_extra = not self.show_extra

    def action_start_download(self):
        for fmt in self.chosen:
            func = download_yt_default_async if fmt.default else download_yt_async
            self.app.yt_search.downloading += 1
            thread = threading.Thread(
                target=func, args=(self.app.yt_search, self.video, fmt)
            )
            thread.start()
        self.close()

    def action_start_merge(self):
        if self.ffmpeg_version is None:
            self.ffmpeg_version = check_ffmpeg()
        if self.ffmpeg_version is None:
            return
        if int(self.ffmpeg_version) < 7:
            pygame.display.message_box(
                "Outdated Dependency 'ffmpeg'",
                "Merging audio and video tracks relies on an ffmpeg version not older than 7.0. You can download the latest EXE from 'https://www.ffmpeg.org/download.html'.",
                "error",
                None,
                ("Understood",),
            )
            return
        self.app.yt_search.downloading += 1
        thread = threading.Thread(
            target=merge_yt_async,
            args=(self.app.yt_search, self.video, self.chosen[0], self.chosen[1]),
        )
        thread.start()
        self.close()

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.MOUSEWHEEL:
            handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
