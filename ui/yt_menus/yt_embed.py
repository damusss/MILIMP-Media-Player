import mili
import pygame
from ui.common import *


class YTEmbedUI(UIComponent):
    def init(self):
        self.anims = [animation(-5) for i in range(7)]
        self.cache = mili.ImageCache()
        self.rect = pygame.Rect()

    def ui(self):
        if self.app.yt_search.embed is None:
            self.close()
            return
        self.mili.id_checkpoint(50000)
        with self.mili.begin(
            ((0, 0), self.app.split_size),
            {"ignore_grid": True, "blocking": False} | mili.PADLESS,
        ) as shadowit:
            self.mili.image(
                SURF, {"fill": True, "fill_color": (0, 0, 0, 200), "cache": self.cache}
            )
            ar = shadowit.data.absolute_rect
            h = ar.h - self.mult(150)
            w = h * 1.777
            do = False
            if w > ar.w:
                do = True
                w = ar.w - 4
                h = w * 0.5625
            x = ar.w / 2 - w / 2
            y = ar.h / 2 - h / 2
            winpos = self.app.window.position
            x += winpos[0]
            if do:
                x = winpos[0] + 2
            y += winpos[1]
            self.rect = pygame.Rect(x, y, w, h)
            if self.app.yt_search.embed is not None and ar.w != 0 and ar.y != 0:
                self.app.yt_search.embed.send(f"nums{x},{y},{w},{h}")

            self.ui_overlay_btn(
                self.anims[0],
                self.close,
                ICONS.close,
                tooltip="Close",
            )
            self.ui_overlay_btn(
                self.anims[1],
                self.action_next,
                ICONS.skip_next,
                tooltip="Preview next video",
                leftmult=1,
            )
            self.ui_overlay_btn(
                self.anims[2],
                self.action_previous,
                ICONS.skip_previous,
                tooltip="Preview previous video",
                leftmult=2,
            )
            self.ui_overlay_btn(
                self.anims[3],
                self.action_link,
                ICONS.link,
                tooltip="Toggle embed link/youtube link",
                leftmult=3,
            )
            self.ui_overlay_btn(
                self.anims[4],
                self.app.yt_search.action_open_link,
                ICONS.minip,
                tooltip="Open video in browser",
                leftmult=4,
            )
            self.ui_overlay_btn(
                self.anims[5],
                self.action_download,
                ICONS.download,
                tooltip="Select formats and download",
                leftmult=5,
            )
            self.ui_overlay_btn(
                self.anims[6],
                self.app.yt_search.action_copy_url,
                ICONS.copy,
                tooltip="Copy url to clipboard",
                leftmult=6,
            )

    def action_download(self):
        self.close()
        self.app.yt_search.action_download()

    def action_next(self):
        if self.app.yt_search.embed is None:
            return
        if self.app.yt_search.video_i < len(self.app.yt_search.video_results) - 1:
            self.app.yt_search.video_i += 1
            video = self.app.yt_search.video_results[self.app.yt_search.video_i]
            self.app.yt_search.embed.video = video
            self.app.yt_search.embed.send_url(video.embed_url)

    def action_previous(self):
        if self.app.yt_search.embed is None:
            return
        if self.app.yt_search.video_i > 0:
            self.app.yt_search.video_i -= 1
            video = self.app.yt_search.video_results[self.app.yt_search.video_i]
            self.app.yt_search.embed.video = video
            self.app.yt_search.embed.send_url(video.embed_url)

    def action_link(self):
        if self.app.yt_search.embed is None:
            return
        embed = self.app.yt_search.embed
        url = embed.video.url
        if "embed" not in embed.url:
            url = embed.video.embed_url
        embed.send_url(url)

    def close(self):
        if self.app.yt_search.embed is not None:
            self.app.yt_search.embed.close()
        self.app.yt_search.embed = None
        self.app.yt_search.modal_state = "none"
        self.mili.use_global_mouse = False

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
