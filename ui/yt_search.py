import mili
import pygame
import shutil
import threading
import webbrowser
from ui.common import *
from ui.yt_menus.yt_embed import YTEmbedUI
from ui.yt_menus.yt_download import YTDownloadUI
from ui.common.data import (
    YTVideoResult,
    AsyncYTEmbed,
)
from ui.common.yt_actions import (
    search_videos_ytdlp_async,
    search_videos_fast_async,
    download_thumbail_async,
    download_channel_async,
    save_thumbnail_async,
)
from ui.common.entryline import UIEntryline

try:
    import webview
except ImportError:
    webview = None
try:
    import youtubesearchpython as fast_yt_search
except ImportError:
    fast_yt_search = None


class YTSearchUI(UIComponent):
    def init(self):
        self.anim_back = animation(-3)
        self.anims = [animation(-3) for i in range(5)]
        self.search_more_anim = animation(-5)
        self.embed_ui = YTEmbedUI(self.app)
        self.download_ui = YTDownloadUI(self.app)
        self.embed = None
        self.scroll = mili.Scroll()
        self.scrollbar = mili.Scrollbar(
            self.scroll, {"short_size": 8, "padding": 3, "border_dist": 3, "axis": "y"}
        )
        self.sbar_size = self.scrollbar.style["short_size"]
        self.modal_state = "none"
        self.search_entryline = UIEntryline("Enter video query...", False)
        self.video_results: list[YTVideoResult] = []
        self.sort_method = "default"
        self.thumb_method = "640x480"
        self.search_method = "yt-dlp"
        self.sort_dm = mili.DropMenu(
            ["default", "title", "views", "channel"],
            "default",
            {
                "menu_update_id": "dm_m_sort",
                "selected_update_id": "dm_s_sort",
                "option_update_id": "dm_o_sort",
                "padding": 0,
            },
        )
        self.thumb_dm = mili.DropMenu(
            list(THUMBNAILS.keys()),
            self.thumb_method,
            {
                "menu_update_id": "dm_m_thumb",
                "selected_update_id": "dm_s_thumb",
                "option_update_id": "dm_o_thumb",
                "padding": 0,
            },
        )
        self.search_dm = mili.DropMenu(
            ["yt-dlp", "youtube-search-python"],
            self.search_method,
            {
                "menu_update_id": "dm_m_search",
                "selected_update_id": "dm_s_search",
                "option_update_id": "dm_o_search",
                "padding": 0,
            },
        )
        self.fetch_amount = 7
        self.found_dependency = False
        self.search_error = None
        self.searching = False
        self.searched = False
        self.search_canceled = False
        self.downloading = 0
        self.download_error = None
        self.thubnails = {}
        self.channel_covers = {}
        self.searching_more = False
        self.downloading_thumbs = set()
        self.downloading_channels = set()
        self.more_options = False
        self.video_i = 0

    def ui_check(self):
        if self.app.modal_state != "none" and self.modal_state != "none":
            if self.modal_state == "embed":
                self.embed_ui.close()
            if self.modal_state == "download":
                self.download_ui.close()
            self.modal_state = "none"

    def ui_top_buttons(self):
        if self.app.modal_state != "none" or self.modal_state != "none":
            return
        self.ui_overlay_top_btn(
            self.anim_back, self.back, ICONS.back, "left", tooltip="Back"
        )

    def ui(self):
        if self.modal_state == "none" and self.app.modal_state == "none":
            handle_arrow_scroll(self.app, self.scroll, self.scrollbar)
        self.search_entryline.update(self.app)

        self.ui_title_area()
        self.ui_container()

        if self.modal_state == "embed":
            self.embed_ui.ui()
        elif self.modal_state == "download":
            self.download_ui.ui()

    def ui_title_area(self):
        self.mili.text_element(
            "YT Music Search",
            {
                "size": self.mult(32),
                "align": "left",
            },
            None,
            {"align": "center", "blocking": None},
        )
        self.ui_search_row()
        if self.more_options:
            self.ui_dropmenus_row()
        self.mili.line_element(
            [("-49.5", 0), ("49.5", 0)],
            {"size": 1, "color": (100,) * 3},
            (0, 0, 0, self.mult(7)),
            {"fillx": True, "blocking": None},
        )

    def ui_search_row(self):
        with self.mili.begin(
            None,
            {
                "resizey": True,
                "fillx": True,
                "axis": "x",
                "pady": 0,
                "padx": self.mult(8),
            },
        ):
            size = self.mult(30)
            self.search_entryline.ui(
                self.mili,
                (0, 0, 0, size),
                {"fillx": True},
                self.mult,
                CONTROLS_CV[0] + 5,
                CONTROLS_CV[1],
            )
            for image, tooltip, action in [
                (
                    ICONS.close if self.searching else ICONS.search,
                    "Cancel search" if self.searching else "Search",
                    self.action_cancel_search
                    if self.searching
                    else self.action_start_search,
                ),
                (ICONS.refresh, "Refresh search", self.action_refresh_search),
                (
                    ICONS.up if self.more_options else ICONS.down,
                    "More options" if self.more_options else "Hide more options",
                    self.action_more_options,
                ),
            ]:
                if it := self.mili.element((0, 0, size, size)):
                    self.mili.rect(
                        {
                            "color": (cond(self.app, it, *OVERLAY_CV),) * 3,
                            "border_radius": 0,
                        }
                    )
                    self.mili.image(
                        image,
                        {"cache": mili.ImageCache.get_next_cache()},
                    )
                    if self.app.can_interact():
                        if it.left_just_released:
                            action()
                        if it.hovered or it.unhover_pressed:
                            self.app.cursor_hover = True
                        if it.hovered:
                            self.app.tick_tooltip(tooltip)

    def ui_dropmenus_row(self):
        with self.mili.begin(
            None,
            {
                "resizey": True,
                "fillx": True,
                "axis": "x",
                "pady": 0,
                "padx": self.mult(8),
            },
        ):
            for i, (dropmenu, wordid, prefix) in enumerate(
                [
                    (self.sort_dm, "sort", "Sort By"),
                    (self.thumb_dm, "thumb", "Thumbnail Res"),
                    (self.search_dm, "search", "Search Method"),
                ]
            ):
                self.ui_dropmenu(dropmenu, wordid, prefix, i)

    def ui_dropmenu(self, dm: mili.DropMenu, wordid, prefix, i):
        self.mili.id_checkpoint(200 + i * 200)
        size = self.mult(25)
        with self.mili.begin(
            (0, 0, 0, size),
            {
                "fillx": True,
                "axis": "x",
                "update_id": f"dm_s_{wordid}",
                "pad": 0,
                "default_align": "center",
            },
        ) as sel:
            self.mili.rect(
                {
                    "color": (
                        OVERLAY_CV[1] if dm.shown else cond(self.app, sel, *OVERLAY_CV),
                    )
                    * 3,
                    "border_radius": 0,
                }
            )
            txt = dm.selected.replace("_", " ")
            if wordid != "search":
                txt = txt.title()
            self.mili.text_element(
                f"{prefix}: {txt}",
                {
                    "size": self.mult(15),
                    "align": "left",
                    "growy": False,
                    "growx": False,
                },
                (0, 0, 0, size),
                {"blocking": False, "fillx": True},
            )
            self.mili.image_element(
                ICONS.up if dm.shown else ICONS.down,
                {"cache": mili.ImageCache.get_next_cache()},
                (0, 0, size, size),
                {"blocking": False},
            )
            if sel.left_just_released:
                for menu in [self.sort_dm, self.thumb_dm, self.search_dm]:
                    if menu is dm:
                        continue
                    menu.hide()
            if sel.hovered:
                self.app.cursor_hover = True
        if dm.shown:
            self.ui_dropmenu_menu(dm, wordid, sel.data.rect.w)

    def ui_dropmenu_menu(self, dm: mili.DropMenu, wordid, w):
        size = self.mult(20)
        with self.mili.begin(
            (dm.topleft, (w, 0)),
            {
                "resizey": True,
                "update_id": f"dm_m_{wordid}",
                "pad": 0,
                "ignore_grid": True,
                "parent_id": 0,
                "z": 99999,
            },
        ):
            if (int(dm.topleft.x), int(dm.topleft.y)) == (0, 0):
                return
            self.mili.rect({"color": (OVERLAY_CV[0],) * 3, "border_radius": 0})
            self.mili.rect(
                {
                    "color": (OVERLAY_CV[1],) * 3,
                    "border_radius": 0,
                    "outline": 1,
                    "draw_above": True,
                }
            )
            for option in dm.options:
                it = self.mili.element(
                    (0, 0, 0, size), {"fillx": True, "update_id": f"dm_o_{wordid}"}
                )
                self.mili.rect(
                    {
                        "color": (cond(self.app, it, *OVERLAY_CV),) * 3,
                        "border_radius": 0,
                    }
                )
                txt = option.replace("_", " ")
                if wordid != "search":
                    txt = txt.title()
                self.mili.text(
                    txt,
                    {
                        "align": "center",
                        "growx": False,
                        "growy": False,
                        "size": self.mult(15),
                    },
                )
                if dm.just_selected:
                    setattr(self, f"{wordid}_method", option)
                if it.hovered:
                    self.app.cursor_hover = True

    def ui_container(self):
        self.mili.id_checkpoint(850)
        with self.mili.begin(
            (0, 0, self.app.split_w, 0),
            {"filly": True},
        ) as scroll_cont:
            if len(self.video_results) > 0:
                results = self.sort_results()
                self.scroll.update(scroll_cont)
                self.scrollbar.style["short_size"] = self.mult(self.sbar_size)
                self.scrollbar.update(scroll_cont)

                self.mili.id_checkpoint(900)
                self.ui_scrollbar()
                self.mili.id_checkpoint(1000)

                if self.downloading > 0:
                    self.ui_searching("Downloading...")
                if self.searching and not self.searching_more:
                    self.ui_searching()
                if self.ui_info_str():
                    return
                for i, video in enumerate(results):
                    self.ui_video(video, i)
                if self.searching and self.searching_more:
                    self.ui_searching()
                if not self.searching_more and not self.searching:
                    with self.mili.begin(
                        None,
                        mili.RESIZE
                        | mili.PADLESS
                        | {
                            "clip_draw": False,
                            "offset": self.scroll.get_offset(),
                            "align": "center",
                        },
                    ):
                        self.ui_image_btn(
                            ICONS.search_more,
                            self.action_search_more,
                            self.search_more_anim,
                            size=52,
                            tooltip="Search 5 more videos",
                        )
            else:
                self.ui_info_str()

    def ui_info_str(self):
        string = ""
        color = (150,) * 3
        if len(self.video_results) <= 0:
            if self.searched:
                string = "No videos found"
            else:
                string = "Enter a query and press search"
        if self.search_error:
            string = self.search_error
            color = "red"
        if string:
            self.mili.text_element(
                string,
                {
                    "color": color,
                    "size": self.mult(20),
                    "growx": False,
                    "growy": True,
                    "slow_grow": True,
                    "wraplen": "100",
                },
                None,
                {"fillx": True, "offset": self.scroll.get_offset()},
            )
            return True
        return False

    def ui_searching(self, txt=None):
        if txt is None:
            txt = "Searching..."
        self.mili.text_element(
            txt,
            {
                "color": (150,) * 3,
                "size": self.mult(20),
                "growx": False,
                "growy": True,
                "slow_grow": True,
                "wraplen": "100",
            },
            None,
            {"fillx": True, "offset": self.scroll.get_offset()},
        )

    def ui_scrollbar(self):
        if self.scrollbar.needed:
            with self.mili.begin(
                self.scrollbar.bar_rect, self.scrollbar.bar_style | {"blocking": None}
            ):
                self.mili.rect({"color": (SBAR_CV,) * 3})
                if handle := self.mili.element(
                    self.scrollbar.handle_rect, self.scrollbar.handle_style
                ):
                    self.mili.rect(
                        {"color": (cond(self.app, handle, *SHANDLE_CV),) * 3}
                    )
                    self.scrollbar.update_handle(handle)
                    if (
                        handle.hovered or handle.unhover_pressed
                    ) and self.app.can_interact():
                        self.app.cursor_hover = True
                        self.app.tick_tooltip(None)

    def ui_video(self, video: YTVideoResult, i):
        H = self.mult(140)
        VH = self.mult(140 - 10)
        mult = 1 / 0.5625
        with self.mili.begin(
            None,
            {
                "fillx": "100" if not self.scrollbar.needed else "98",
                "offset": (
                    self.scrollbar.needed * -self.mult(self.sbar_size / 2),
                    self.scroll.get_offset()[1],
                ),
                "padx": self.mult(8),
                "axis": "x",
                "align": "center",
                "anchor": "first",
                "resizey": {"min": H},
            },
        ) as cont:
            if cont.data.absolute_rect.colliderect(((0, 0), self.app.split_size)):
                self.ui_video_bg(cont, video)
                thumbnail = self.thubnails.get(video.thumbnail, None)
                if thumbnail is None:
                    if video.thumbnail not in self.downloading_thumbs:
                        self.start_downloading_thumb(video)
                    thumbnail = ICONS.loading
                with self.mili.begin(
                    (0, 0, VH * mult, VH), {"blocking": False, "pad": 0}
                ):
                    self.mili.image(
                        thumbnail,
                        {"cache": video.thumb_cache, "fill": True},
                    )
                    self.ui_video_duration(video, (VH * mult, VH))
                with self.mili.begin(
                    None,
                    {
                        "fillx": True,
                        "filly": True,
                        "pad": 0,
                        "blocking": False,
                        "anchor": "first",
                    },
                ):
                    self.mili.text_element(
                        video.title if video.title else "<No Title>",
                        {
                            "size": self.mult(19),
                            "growx": False,
                            "growy": True,
                            "slow_grow": True,
                            "wraplen": "100",
                            "font_align": pygame.FONT_LEFT,
                            "align": "topleft",
                            "cache": video.cache,
                        },
                        (
                            0,
                            0,
                            self.app.split_w / 1.05 - VH * mult - 10,
                            0,
                        ),
                        {"align": "first", "blocking": False},
                    )
                    stack = False
                    out = video.cache.get_output()
                    if out is not None and out.height >= H / 2.5:
                        stack = True
                    self.ui_video_metadata(video, stack)
                if self.app.can_interact():
                    if cont.just_released_button != -1:
                        if self.modal_state == "none":
                            self.open_video_menu(video)
                        elif self.embed is not None:
                            self.embed.video = video
                            self.embed.send_url(video.embed_url)
                        self.video_i = i
                    if cont.hovered:
                        self.app.cursor_hover = True
            else:
                self.mili.element((0, 0, 0, VH), {"blocking": False})

    def ui_video_duration(self, video: YTVideoResult, isize):
        style = {"size": self.mult(16), "padx": 3}
        if isinstance(video.duration, str):
            txt = video.duration
        else:
            try:
                duration = float(video.duration)
            except ValueError:
                return

            txt = format_music_time(duration)
        size = self.mili.text_size(txt, style)
        self.mili.element(
            pygame.Rect((0, 0), size).move_to(
                bottomright=pygame.Vector2(isize) - (2, 2)
            ),
            {"ignore_grid": True, "blocking": False},
        )
        self.mili.rect({"color": MENU_CV[0], "border_radius": 2})
        self.mili.text(txt, style)

    def ui_video_metadata(self, video: YTVideoResult, stack):
        if stack:
            self.mili.begin(
                None, mili.RESIZE | mili.X | mili.PADLESS | {"blocking": False}
            )
        views = self.format_views(video.views)
        if views is not None:
            self.mili.text_element(
                views,
                {"color": (160,) * 3, "size": self.mult(18)},
                None,
                {"blocking": False},
            )
        imgsize = self.mult(30)
        image = self.channel_covers.get(video.channel_id, None)
        if image is None:
            image = ICONS.account
            if video.channel_id not in self.downloading_channels:
                self.start_downloading_channel(video)
        with self.mili.begin(None, mili.RESIZE | mili.X | {"pady": 0}) as hit:
            if hit.hovered or hit.left_pressed:
                self.mili.rect(
                    {
                        "color": (cond(self.app, hit, 15, 25, 20),) * 3,
                        "border_radius": 0,
                    }
                )
            self.mili.image_element(
                image,
                {
                    "cache": video.channel_cache,
                    "alpha": cond(self.app, hit, 180, 255, 150),
                },
                (0, 0, imgsize, imgsize),
                {"blocking": False},
            )
            self.mili.text_element(
                video.channel if video.channel else "<Unknown Channel>",
                {
                    "color": (cond(self.app, hit, 200, 255, 180),) * 3,
                    "size": self.mult(17),
                },
                None,
                {"align": "center", "blocking": False},
            )
            if self.app.can_interact():
                if hit.left_just_released:
                    webbrowser.open(video.channel_url)
                if hit.hovered:
                    self.app.tick_tooltip(f"Open channel at '{video.channel_url}'")
                    self.app.cursor_hover = True
        if stack:
            self.mili.end()

    def ui_video_bg(self, cont, video):
        forcehover = self.app.menu_data == video and self.app.menu_open
        color = MUSIC_CV[1] if forcehover else cond(self.app, cont, *MUSIC_CV)
        if self.app.bg_effect:
            self.mili.image(
                SURF,
                {
                    "fill": True,
                    "fill_color": (
                        *((color,) * 3),
                        ALPHA,
                    ),
                    "border_radius": 0,
                    "cache": mili.ImageCache.get_next_cache(),
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

    def format_views(self, n):
        if n.isdecimal():
            n = int(n)
        else:
            return None
        suffix = ""
        if n >= 1_000_000_000:
            n = round(n / 1_000_000_000, 3)
            suffix = "B"
        elif n >= 1_000_000:
            n = round(n / 1_000_000, 3)
            suffix = "M"
        elif n >= 1_000:
            n = round(n / 1000, 3)
            suffix = "K"
        return f"{n:,}{suffix} Views"

    def open_video_menu(self, video):
        self.app.open_menu(
            video,
            (
                ICONS.minip,
                self.action_open_link,
                self.anims[0],
                "30",
                "Open video in browser",
            ),
            (
                ICONS.minipd,
                self.action_open_embed,
                self.anims[1],
                "30",
                "Open video embed (SHIFT for full youtube embed)",
            ),
            (
                ICONS.download,
                self.action_download,
                self.anims[2],
                "Select formats and download",
            ),
            (
                ICONS.download_file,
                self.action_download_thumb,
                self.anims[3],
                "30",
                "Download thumbnail (highest resolution)",
            ),
            (
                ICONS.copy,
                self.action_copy_url,
                self.anims[4],
                "30",
                "Copy url to clipboard",
            ),
        )

    def action_copy_url(self):
        pygame.scrap.put_text(self.app.menu_data.url)

    def action_download_thumb(self):
        thread = threading.Thread(
            target=save_thumbnail_async, args=(self.app.menu_data,)
        )
        thread.start()
        self.app.close_menu()

    def action_download(self):
        self.modal_state = "download"
        self.download_ui.enter(self.app.menu_data)
        self.app.close_menu()

    def action_open_link(self):
        webbrowser.open(self.app.menu_data.url)

    def action_open_embed(self):
        if webview is None and not os.path.exists("ytembed.exe"):
            pygame.display.message_box(
                "Missing Python Dependency 'pywebview'",
                "To open the video embed in-app you must install the pywebview library with pip",
                "error",
                None,
                ("Understood",),
            )
            return

        self.embed = AsyncYTEmbed(
            self.app.menu_data, pygame.key.get_mods() & pygame.KMOD_SHIFT
        )
        self.modal_state = "embed"
        self.app.close_menu()
        self.mili.use_global_mouse = True

    def action_cancel_search(self):
        self.search_canceled = True
        self.searching = False
        self.searching_more = False

    def action_start_search(self):
        if self.search_warmup():
            return
        if self.searching:
            return
        self.fetch_amount = 7
        self.start_search()

    def action_search_more(self):
        if self.search_warmup():
            return
        if self.searching:
            return
        self.searching_more = True
        self.fetch_amount += 5
        self.start_search()

    def action_refresh_search(self):
        if self.search_warmup():
            return
        if self.searching:
            return
        self.start_search()

    def search_warmup(self):
        if self.search_method == "yt-dlp":
            found = self.check_ytdlp_dependency()
            if not found:
                return True
        else:
            if not fast_yt_search:
                pygame.display.message_box(
                    "Missing Dependency 'youtube-search-python'",
                    "Searching with mode 'youtube-search-python' relies on the 'youtube-search-python' python package dependency that must be pip installed. If that isn't an option use the search mode 'yt-dlp' with yt-dlp installed.",
                    "error",
                    None,
                    ("Understood",),
                )
                return True
        return False

    def start_search(self):
        query = self.search_entryline.text.strip()
        self.search_error = None
        self.searching = True
        func = (
            search_videos_ytdlp_async
            if self.search_method == "yt-dlp"
            else search_videos_fast_async
        )
        thread = threading.Thread(target=func, args=(self, query))
        thread.start()

    def start_downloading_thumb(self, video: YTVideoResult):
        self.downloading_thumbs.add(video.thumbnail)
        thread = threading.Thread(
            target=download_thumbail_async, args=(video, self, ICONS.error)
        )
        thread.start()

    def start_downloading_channel(self, video: YTVideoResult):
        self.downloading_channels.add(video.channel_id)
        thread = threading.Thread(
            target=download_channel_async, args=(video, self, ICONS.account)
        )
        thread.start()

    def action_more_options(self):
        self.more_options = not self.more_options

    def enter(self):
        self.app.change_state("search")

    def check_ytdlp_dependency(self):
        if self.found_dependency:
            return True
        dep = shutil.which("yt-dlp")
        if dep is None:
            pygame.display.message_box(
                "Missing Dependency 'yt-dlp'",
                "Searching with mode 'yt-dlp' relies on the yt-dlp dependency that must be downloaded and possibly added to PATH. You can download the latest EXE from 'https://github.com/yt-dlp/yt-dlp/releases'.",
                "error",
                None,
                ("Understood",),
            )
            return False
        else:
            self.found_dependency = True
        return True

    def sort_results(self):
        if self.sort_method == "default":
            return self.video_results
        return sorted(
            self.video_results,
            key=lambda v: getattr(v, self.sort_method),
            reverse=self.sort_method == "views",
        )

    def back(self):
        self.app.change_state("list")
        self.scroll.set_scroll(0, 0)
        self.scrollbar.scroll_moved()

    def event(self, event):
        if (
            self.app.can_interact()
            and self.modal_state == "none"
            and self.app.modal_state == "none"
        ):
            self.search_entryline.event(event)
        if (
            event.type == pygame.MOUSEWHEEL
            and self.app.modal_state == "none"
            and self.modal_state != "download"
        ):
            handle_wheel_scroll(event, self.app, self.scroll, self.scrollbar)

        if self.app.listening_key or not self.app.can_interact():
            return
        doexit = False
        if self.modal_state == "embed":
            doexit = self.embed_ui.event(event)
        elif self.modal_state == "download":
            doexit = self.download_ui.event(event)
        if doexit:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back()
            if Keybinds.check(
                "toggle_search", event, ignore_input=True
            ) or Keybinds.check("confirm", event, ignore_input=True):
                self.action_start_search()
            if Keybinds.check("refresh_yt_search", event, ignore_input=True):
                self.action_refresh_search()
