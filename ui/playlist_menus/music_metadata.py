import mili
import pygame
import pathlib
from ui.common import *
from ui.common.data import MusicData, NotCached


class MusicMetadataUI(UIComponent):
    def init(self):
        self.anim_close = animation(-5)
        self.cache = mili.ImageCache()
        self.music: MusicData = None

    def ui(self):
        self.mili.id_checkpoint(ID_OFFSET + 150000)
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
                    "fillx": "60" if self.app.split_w > 1500 else "80",
                    "resizey": True,
                    "align": "center",
                    "spacing": self.mult(13),
                    "offset": (0, -self.app.tbarh),
                    "blocking": None,
                }
                | mili.CENTER,
            ):
                self.mili.rect({"color": (MODAL_CV,) * 3, "border_radius": "5"})

                self.mili.text_element(
                    "Music Metadata",
                    {"size": self.mult(26)},
                    None,
                    mili.CENTER | {"blocking": None},
                )
                with self.mili.begin(
                    None,
                    {
                        "fillx": "80" if self.app.split_w > 1500 else "95",
                        "resizey": True,
                        "pad": 0,
                        "spacing": 0,
                    }
                    | mili.CENTER,
                ):
                    self.ui_metadata_column(
                        "Title", parse_music_stem(self.app, self.music.realpath.stem)
                    )
                    self.ui_metadata_column("Real Path", self.music.realpath, path=True)
                    pname = self.music.playlist.name
                    converted = pathlib.Path(
                        f"data/mp3_converted/{pname}_{self.music.realpath.stem}.mp3"
                    ).resolve()
                    has_converted = True
                    if not os.path.exists(converted):
                        converted = "Not Converted"
                        has_converted = False
                    self.ui_metadata_column(
                        "Converted Path", converted, has_converted, path=True
                    )
                    cover = pathlib.Path(
                        f"data/music_covers/{pname}_{self.music.realpath.stem}.png"
                    ).resolve()
                    has_cover = True
                    if not os.path.exists(cover):
                        cover = "No Cover"
                        has_cover = False
                    self.ui_metadata_column("Cover Path", cover, has_cover, path=True)
                    self.ui_metadata_column("Playlist Name", pname)
                    self.ui_metadata_column(
                        "Playlist Group Name",
                        self.music.group.name
                        if self.music.group
                        else "Not added to a group",
                        self.music.group is not None,
                    )
                    if isinstance(self.music.duration, float):
                        duration = (
                            format_music_time(self.music.duration)
                            + f" ({self.music.duration:.2f} seconds)"
                        )
                    else:
                        duration = "Unknown"
                    self.ui_metadata_column(
                        "Duration", duration, isinstance(self.music.duration, float)
                    )
                    self.ui_metadata_column(
                        "Is Video", "Yes" if self.music.isvideo else "No (audio only)"
                    )
                    self.ui_metadata_column(
                        "Track Positioning",
                        "Supported" if self.music.pos_supported else "Unsupported",
                    )
                    if self.music.isvideo:
                        extra = ""
                        if self.music.filesize > LARGE_MEDIA_SIZE:
                            extra = " (Heavy File)"
                        sourceres = "N/D"

                        if (
                            self.music.video_size is NotCached
                            or self.music.video_fps is NotCached
                        ):
                            if (
                                self.music is self.app.music
                                and self.app.music_controls.async_videoclip is not None
                                and self.app.music_controls.async_videoclip.videoclip
                                is not None
                            ):
                                self.music.video_size = self.app.music_controls.async_videoclip.original_size
                                self.music.video_fps = self.app.music_controls.async_videoclip.videoclip.fps
                            else:
                                self.music.cache_video_metadata()
                        if self.music.video_size is not None:
                            sourceres = f"{int(self.music.video_size[0])}x{int(self.music.video_size[1])} px"
                        sourcefps = "N/D"
                        frameno = "N/D"
                        if self.music.video_fps is not None:
                            sourcefps = f"{int(self.music.video_fps)} FPS"
                            if isinstance(self.music.duration, float):
                                frameno = (
                                    f"{int(self.music.duration * self.music.video_fps)}"
                                )
                        self.ui_metadata_column(
                            "Video Metadata",
                            f"Source Resolution: {sourceres}, Source Framerate: {sourcefps}, File Size: {self.music.filesize} Bytes {extra}, Frames: {frameno}",
                        )
                    else:
                        self.ui_metadata_column("Video Metadata", "Not a video", False)

                self.mili.element((0, 0, 0, self.mult(10)))

            self.ui_overlay_btn(
                self.anim_close, self.close, ICONS.close, tooltip="Close"
            )

    def ui_metadata_column(self, title, value, active=True, path=False):
        with self.mili.begin(
            None, {"fillx": True, "resizey": True, "axis": "x", "pad": 0, "spacing": 0}
        ) as parent:
            self.mili.element(
                None,
                {"fillx": "25", "filly": True},
            )
            self.mili.rect(
                {
                    "color": (MODALB_CV[1],) * 3,
                    "border_radius": 0,
                    "outline": 1,
                    "draw_above": True,
                }
            )
            self.mili.text(
                title,
                {
                    "size": self.mult(18),
                    "growx": False,
                    "growy": False,
                    "align": "left",
                    "font_align": pygame.FONT_LEFT,
                    "color": (150,) * 3,
                },
            )
            self.mili.element(
                (0, 0, mili.percentage(100 - 25, parent.data.rect.w), 0),
                {"fillx": str(100 - 25)},
            )
            self.mili.rect(
                {
                    "color": (MODALB_CV[1],) * 3,
                    "border_radius": 0,
                    "outline": 1,
                    "draw_above": True,
                }
            )
            self.mili.text(
                value,
                {
                    "size": self.mult(15 if path and active else 17),
                    "growx": False,
                    "slow_grow": True,
                    "wraplen": "100",
                    "color": "white" if active else (120,) * 3,
                    "align": "left",
                    "font_align": pygame.FONT_LEFT,
                },
            )

    def close(self):
        self.app.playlist_viewer.modal_state = "none"

    def event(self, event):
        if self.app.listening_key:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return False
