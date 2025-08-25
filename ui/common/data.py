import av.codec
import av.codec.hwaccel
import av.container
import av.error
import av.stream
import av.video
import av.video.reformatter
import numpy
import pygame
import pathlib
import threading
import subprocess
import datetime
from pygame._sdl2 import video as pgvideo
from ui.common import *
import moviepy
import zipfile
import av
import os
import math

try:
    import webview
except ImportError:
    webview = None


def safeguard_window(arg, position=False):
    if arg is None:
        return arg
    for value in arg:
        if value <= 0 and not position:
            return None
        if value > 100000:
            return None
    return arg


def load_cover_async(path, obj):
    obj.cover = pygame.image.load(path).convert_alpha()
    obj.loaded_cover = True


def get_cover_async(music: "MusicData", videofile: moviepy.VideoClip, cover_path):
    try:
        frame: numpy.ndarray = videofile.get_frame(videofile.duration / 2)
        surface = pygame.image.frombytes(frame.tobytes(), videofile.size, "RGB")
        pygame.image.save(surface, cover_path)
        music.cover = surface
        music.loaded_cover = True
    except Exception:
        music.cover = None


def get_virtual_cover_async(track: "VirtualMusic", path, fail_icon):
    try:
        cont = av.open(str(path))
        stream = cont.streams.video[0]
        duration = stream.duration
        if duration is None:
            duration = 0
        cont.seek(int((duration / 2) / stream.time_base), stream=stream)
        decoder = cont.decode(stream)
        frame = next(decoder)
        track.cover = pygame.surfarray.make_surface(
            numpy.transpose(frame.reformat(format="rgb24").to_ndarray(), (1, 0, 2))
        )
    except Exception as e:
        print(e)
        track.cover = fail_icon


def convert_music_async(
    music: "MusicData", audiofile: moviepy.AudioClip, new_path, success=None
):
    try:
        audiofile.write_audiofile(str(new_path))
        music.pending = False
        if music.audio_converting:
            music.converted = True
        music.audio_converting = False
        if success is not None:
            success.notify(
                NOTIF.INFO, f"Track {music.realpath} converted successfully to mp3"
            )
    except Exception as e:
        music.load_exc = e


def create_backup_async(categories, path, comp):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zfile:
        if categories["Settings"]:
            zfile.write(f"{DATA_PATH}/settings.json", "settings.json")
            zfile.write(f"{DATA_PATH}/gpu.json", "gpu.json")
        if categories["Playlists"]:
            zfile.write(f"{DATA_PATH}/playlists.json", "playlists.json")
        if categories["History"]:
            zfile.write(f"{DATA_PATH}/history.json", "history.json")
            zfile.write(f"{DATA_PATH}/search_results.json", "search_results.json")
        if categories["Playlist Covers"]:
            zfile.mkdir("covers")
            for file in os.listdir(f"{DATA_PATH}/covers"):
                zfile.write(f"{DATA_PATH}/covers/{file}", f"covers/{file}")
        if categories["Music Covers"]:
            zfile.mkdir("music_covers")
            for file in os.listdir(f"{DATA_PATH}/music_covers"):
                zfile.write(f"{DATA_PATH}/music_covers/{file}", f"music_covers/{file}")
        if categories["MP3 Converted"]:
            zfile.mkdir("mp3_converted")
            for file in os.listdir(f"{DATA_PATH}/mp3_converted"):
                zfile.write(
                    f"{DATA_PATH}/mp3_converted/{file}", f"mp3_converted/{file}"
                )
        if categories["YT Downloads"]:
            for folder, subfolders, files in os.walk(f"{DATA_PATH}/yt_downloads"):
                zfile.mkdir(folder.removeprefix(f"{DATA_PATH}/"))
                for file in files:
                    save = pathlib.Path(os.path.join(folder, file)).relative_to(
                        f"{DATA_PATH}"
                    )
                    zfile.write(os.path.join(folder, file), save)
        if categories["YT Playlists"]:
            for folder, subfolders, files in os.walk(f"{DATA_PATH}/yt_playlists"):
                zfile.mkdir(folder.removeprefix(f"{DATA_PATH}/"))
                for file in files:
                    save = pathlib.Path(os.path.join(folder, file)).relative_to(
                        f"{DATA_PATH}"
                    )
                    zfile.write(os.path.join(folder, file), save)
    comp.backing_up = False
    comp.app.notify(NOTIF.DOWNLOAD, f"Backup saved to '{path}'")


class Entryline(mili.EntryLine):
    def __init__(
        self,
        app: "MILIMP",
        placeholder="Enter text...",
        target_files=True,
        bgcol=20,
        outlinecol=40,
        txtcol="white",
        specialspaces=False,
    ):
        self.app = app
        super().__init__(
            "",
            {
                "placeholder": placeholder,
                "validator_windows_path": target_files,
                "bg_rect_style": {"color": (bgcol,) * 3, "border_radius": 0},
                "outline_rect_style": {
                    "color": (outlinecol,) * 3,
                    "outline": 1,
                    "border_radius": 0,
                },
                "text_style": {"color": txtcol},
                "space_characters": [" ", "\\", "/"] if specialspaces else [" "],
            },
        )

    def set_text(self, text):
        self.text = text

    def ui(self, rect, style):
        if self.focused:
            self.app.input_stolen = True
        self.style["text_style"]["size"] = self.app.mult_fs(20)
        with self.app.mili.begin(rect, style | {"axis": "x"}) as cont:
            with self.app.mili.push_styles(rect={"border_radius": 0}):
                super().ui(cont)


class MenuButton:
    def __init__(self, icon, action, animation, br="50", tooltip="", red=False):
        self.icon = icon
        self.action = action
        self.animation = animation
        self.br = br
        self.tooltip = tooltip
        self.red = red


class Notification:
    def __init__(self, kind, message, error=False, hidden=False):
        self.kind = kind
        self.message = message
        self.error = error
        self.hidden = hidden
        self.time = datetime.datetime.now()


class SafeRunningContext:
    def __init__(self, app: "MILIMP"):
        self.app = app

    def __enter__(self):
        return self

    def __exit__(self, exctype, excval, exctb):
        if exctype is SystemExit:
            return
        if self.app is not None or exctype is not None:
            if os.path.exists(RUNNING_INSTANCE_SENTINEL):
                os.remove(RUNNING_INSTANCE_SENTINEL)
        if exctype is not None:
            if self.app is not None:
                self.app.aborted = True
                self.app.save()
                async_videoclip = self.app.state.async_videoclip
                if async_videoclip is not None:
                    async_videoclip.alive = False
                    if self.app.state.videoclip_threaded:
                        async_videoclip.thread.join()
                yt_syncer = self.app.playlist_viewer.yt_syncer
                if yt_syncer.alive and yt_syncer.thread is not None:
                    yt_syncer.alive = False
                    yt_syncer.force_quit = True
                    yt_syncer.thread.join()
                audioplayer = self.app.state.async_audioplayer
                if audioplayer is not None:
                    audioplayer.alive = False
                    audioplayer.thread.join()
            print(f"Application aborted with an exception ({exctype.__name__}).")


class YTVideoFormat:
    def __init__(self, id_, type_, ext, res, fps, filesize, extra_data, default=False):
        self.id = id_
        self.type = type_
        self.ext = ext
        self.res = res
        self.fps = fps
        self.filesize = filesize
        self.extra_data = extra_data
        self.default = default

    def save(self):
        return {
            "id": self.id,
            "type": self.type,
            "ext": self.ext,
            "res": self.res,
            "fps": self.fps,
            "filesize": self.filesize,
            "extra_data": self.extra_data,
            "default": self.default,
        }

    @classmethod
    def load(self, data):
        return YTVideoFormat(
            data["id"],
            data["type"],
            data["ext"],
            data["res"],
            data["fps"],
            data["filesize"],
            data["extra_data"],
            data["default"],
        )


class YTVideoResult:
    def __init__(
        self,
        title,
        id_,
        url,
        views,
        channel,
        channel_id,
        channel_url,
        duration,
        live_status,
        globality,
        thumb_prefix,
        thumb_sizes,
        thumb_url=None,
        formats=None,
        quick_pfp_url=None,
    ):
        self.title = title.strip()
        self.id = id_
        self.url = url
        self.views = views
        self.channel = channel.strip()
        self.channel_id = channel_id
        self.channel_url = channel_url
        self.duration = duration
        self.live_status = live_status
        self.globality = globality
        self.thumb_sizes = thumb_sizes
        self.embed_url = f"https://www.youtube.com/embed/{self.id}?feature=oembed"
        if thumb_url:
            self.thumb_url = thumb_url
        else:
            self.thumb_url = (
                f"https://i.ytimg.com/vi/{self.id}/{thumb_prefix}default.jpg"
            )
        self.cache = mili.TextCache()
        self.thumb_cache = mili.ImageCache()
        self.channel_cache = mili.ImageCache()
        self.formats = formats
        self.quick_pfp_url = None

    @property
    def hd_thumb_url(self):
        return f"https://i.ytimg.com/vi/{self.id}/maxresdefault.jpg"

    @property
    def thumbnail(self):
        return f"{self.id}_{self.thumb_sizes}"

    @property
    def title_fn(self):
        return "".join(
            char
            for char in self.title
            if char not in ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
        )

    @property
    def channel_fn(self):
        return "".join(
            char
            for char in self.channel
            if char not in ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
        )

    def save(self):
        return {
            "title": self.title,
            "id": self.id,
            "url": self.url,
            "views": self.views,
            "channel": self.channel,
            "channel_id": self.channel_id,
            "channel_url": self.channel_url,
            "duration": self.duration,
            "thumb_url": self.thumb_url,
            "thumb_sizes": self.thumb_sizes,
            "formats": [fmt.save() for fmt in self.formats]
            if self.formats is not None
            else None,
            "quick_pfp_url": self.quick_pfp_url,
        }

    @classmethod
    def load(self, data):
        return YTVideoResult(
            data["title"],
            data["id"],
            data["url"],
            data["views"],
            data["channel"],
            data["channel_id"],
            data["channel_url"],
            data["duration"],
            "NA",
            "NA",
            "NA",
            data["thumb_sizes"],
            data["thumb_url"],
            [YTVideoFormat.load(fmt) for fmt in data["formats"]]
            if data["formats"] is not None
            else data["formats"],
            data["quick_pfp_url"],
        )


class NotCached: ...


class AsyncYTEmbed:
    def __init__(self, video: YTVideoResult, shift=False):
        self.video = video
        self.url = self.video.embed_url
        if os.path.exists("ytembed.py") and webview:
            start = "py ytembed.py"
        else:
            start = "ytembed.exe"
        self.process = subprocess.Popen(
            f"{start} {self.video.url if shift else self.video.embed_url}",
            stdin=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    def send(self, data: str):
        self.process.stdin.write(
            (data + "\n").encode("ascii", errors="replace").decode("ascii")
        )
        self.process.stdin.flush()

    def send_url(self, url):
        self.send(f"newurl:{url}")
        self.url = url

    def close(self):
        self.send("kill")
        self.process.kill()


class VideoclipRect:
    def __init__(
        self, videoclip: "AsyncVideoclipGetter", preview=False, miniplayer=False
    ):
        self.videoclip = videoclip
        self.rect = None
        self.active = False
        self.output = None
        self.preview = preview
        self.texture = None
        self.miniplayer = miniplayer
        self.resampler = av.video.reformatter.VideoReformatter()

    def get_or(self, image):
        if self.output is not None:
            if USE_RENDERER:
                return self.texture, True
            return self.output, True
        return image, False

    def set_rect(self, rect):
        if self.rect != rect and not self.videoclip.active:
            self.videoclip.refresh_frame = True
        self.rect = rect

    def update_texture(self, app: "MILIMP"):
        if not USE_RENDERER:
            return
        renderer = (
            app.music_controls.minip.mili.canva._renderer
            if self.miniplayer
            else app.mili.canva._renderer
        )
        if self.texture is None or self.output.size != (
            self.texture.width,
            self.texture.height,
        ):
            self.texture = pgvideo.Texture.from_surface(renderer, self.output)
            return
        self.texture.update(self.output)


class AsyncVideoclipGetter:
    def __init__(self, realpath, app: "MILIMP"):
        self.app = app
        self.state = app.state
        self.realpath = realpath
        self.thread = None
        self.active = False
        self.time = None
        self.outputs = {}
        self.framerate = 60
        self.alive = True
        self.clock = pygame.Clock()
        self.close_on_kill = True
        self.current_fps = 0
        self.container: av.container.InputContainer = None
        self.stream: av.VideoStream = None
        self.decoder = None
        self.main_rect = VideoclipRect(self)
        self.miniplayer_rect = VideoclipRect(self, miniplayer=True)
        self.preview_rect = VideoclipRect(self, True)
        self.rects = [self.main_rect, self.miniplayer_rect, self.preview_rect]
        self.last_frame_time = -1
        self.frame_queue = []
        self.refresh_frame = False
        self.last_frame = None

    def load_container(self):
        self.container = av.open(
            self.realpath,
        )
        self.stream = self.container.streams.video[0]
        #self.stream.thread_type = "FRAME"
        devices = av.codec.hwaccel.hwdevices_available()
        self.stream.codec_context.options = {
            "hwaccel": devices[0],  # or try 'dxva2', 'd3d11va', 'nvdec'
            "hwaccel_device": "0",
            "hwaccel_output_format": devices[0],
            #"threads": "auto"
        }
        self.decoder = None
        self.frame_queue = []

    def fit_frame(self, rect: pygame.Rect):
        original_width = self.stream.coded_width
        original_height = self.stream.coded_height
        target_width, target_height = rect.size

        width_ratio = target_width / original_width
        height_ratio = target_height / original_height
        scale = min(width_ratio, height_ratio)

        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        return new_width, new_height

    def update(self):
        if self.container is None and self.alive:
            self.load_container()
        if (
            self.time is not None
            and self.state.videoclip_on
            and not self.active
            and self.refresh_frame
            and self.last_frame is not None
        ):
            self.refresh_frame = False
            self.update_frame(self.last_frame)
        if not self.active or self.time is None or not self.state.videoclip_on:
            if self.state.videoclip_threaded:
                self.clock.tick(10)
            return
        if self.state.videoclip_threaded:
            fps = self.stream.average_rate
            if fps is None:
                fps = self.framerate - 1
            self.clock.tick(min(fps + 1, self.framerate))
            self.current_fps = self.clock.get_fps()
        time_pts = int(self.time / self.stream.time_base)
        if self.decoder is None or abs(self.time - self.last_frame_time) > 1.2:
            self.container.seek(time_pts, stream=self.stream)
            self.decoder = self.container.decode(self.stream)
            self.frame_queue.clear()

        while True:
            try:
                if not self.frame_queue:
                    # bef = time.perf_counter()
                    frame = next(self.decoder)
                    # print((time.perf_counter() - bef) * 1000)
                    self.frame_queue.append(frame)
                elif self.frame_queue[0].pts < time_pts:
                    self.frame_queue.pop(0)
                else:
                    break
            except StopIteration:
                break

        if self.frame_queue:
            frame = self.frame_queue[0]
            self.last_frame_time = frame.pts * self.stream.time_base
            self.last_frame = frame
            self.update_frame(frame)

    def update_frame(self, frame):
        for rect in self.rects:
            heavy = self.stream.coded_width > 6000 and self.stream.coded_height > 3000
            if not rect.active and rect.rect is None:
                continue
            if rect.preview and heavy:
                rect.output = None
                continue
            # bef = time.perf_counter()
            size = self.fit_frame(rect.rect)
            try:
                resized = rect.resampler.reformat(
                    frame,
                    size[0],
                    size[1],
                    "rgb24",
                    interpolation="POINT"
                    if heavy
                    else ("BILINEAR" if rect.preview else "BICUBIC"),
                )
            except av.error.ValueError:
                rect.output = None
                continue
            array = numpy.transpose(resized.to_ndarray(), (1, 0, 2))
            surface = pygame.surfarray.make_surface(array)
            # print((time.perf_counter() - bef) * 1000)
            rect.output = surface
            rect.update_texture(self.app)

    def loop(self):
        while self.alive:
            self.update()
        if self.close_on_kill:
            if self.container is not None:
                self.container.close()
            self.container = None


class VirtualMusic:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.cover = ICONS.audio_track
        if self.isvideo:
            self.cover = ICONS.loading
            thread = threading.Thread(
                target=get_virtual_cover_async, args=(self, self.path, ICONS.error)
            )
            thread.start()

    @property
    def isvideo(self):
        return self.path.suffix.lower()[
            1:
        ] in VIDEO_SUPPORTED and not self.path.stem.endswith("novideo")


class VirtualPlaylist:
    def __init__(self, path):
        self.path = path
        self.tracks = []
        self.folders = []
        for file in os.listdir(self.path):
            full = pathlib.Path(os.path.join(self.path, file))
            if os.path.isdir(full):
                self.folders.append(full.stem)
            else:
                if full.suffix[1:] in FORMATS:
                    track = VirtualMusic(full)
                    self.tracks.append(track)


class AsyncFFPLAYAudioPlayer:
    def __init__(self, app: "MILIMP"):
        self.app = app
        self.state = app.state
        self.thread = None
        self.remake_pipe = True
        self.alive = True
        self.process: subprocess.Popen = None
        self.remake_time = pygame.time.get_ticks()

    def loop(self):
        while self.alive:
            if self.remake_pipe or self.process is None:
                self.make_pipe()
            if self.process is not None:
                result = self.process.poll()
                if result is not None:
                    self.state.music_auto_finish()
                    self.alive = False
                    self.thread = None
                    break
                if pygame.time.get_ticks() - self.remake_time >= 50:
                    try:
                        line = self.process.stdout.readline().strip()
                    except Exception:
                        continue
                    sep = line.split(" ")
                    if len(sep) > 0:
                        first = sep[0]
                        try:
                            time = float(first)
                            if (
                                (round(time, 2) - round(self.state.get_music_pos(), 2))
                                > 0.01
                                and time >= 0
                                and time < self.state.get_music_pos()
                                and not math.isnan(time)
                            ):
                                self.state.set_music_pos(time)
                                self.remake_pipe = False
                        except ValueError:
                            ...
        self.close_pipe()

    def make_pipe(self):
        if self.process is not None:
            self.close_pipe()
        if self.state.music_paused:
            self.remake_pipe = False
            return
        command = f'ffplay -nodisp -autoexit -volume {int(self.state.volume * 100)} -ss {self.state.get_music_pos()} "{self.state.music.audiopath}"'
        if sys.platform == "win32":
            self.process = subprocess.Popen(
                command,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                text=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )
        else:
            self.process = subprocess.Popen(
                command,
                preexec_fn=os.setsid,
                text=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )
        self.remake_pipe = False
        self.remake_time = pygame.time.get_ticks()

    def close_pipe(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        self.process = None


class VirtualPlayingMusic:
    virtual = True

    def __init__(self, path, cover, isvideo, parent_folder):
        self.audiopath = path
        self.realpath = path
        self.realstem = self.realpath.stem
        self.realname = self.realpath.name
        self.cover = cover
        self.isvideo = isvideo
        self.has_audio = True
        self.pending = False
        self.filesize = os.path.getsize(path)
        self.pos_supported = True
        self.require_ffplay = False
        cont = av.open(path)
        if isvideo:
            self.require_ffplay = True
            stream = cont.streams.video[0]
            if stream.duration is not None:
                self.duration = stream.duration * stream.time_base
                self.has_audio = len(cont.streams.audio) > 0
                self.video_size = (stream.coded_width, stream.coded_height)
                self.video_fps = stream.average_rate
            else:
                with moviepy.VideoFileClip(path) as videofile:
                    self.duration = videofile.duration
                    self.has_audio = videofile.audio is not None
                    self.video_size = videofile.size
                    self.video_fps = videofile.fps
        else:
            stream = cont.streams.audio[0]
            self.duration = stream.duration * stream.time_base
            if self.realpath.suffix[1:] not in PYGAME_SUPPORTED:
                self.require_ffplay = True
        cont.close()
        self.playlist = Playlist(str(parent_folder), [])
        self.playlist.musiclist.append(self)
        self.playlist.musictable[self.audiopath] = self

    def cover_or(self, default):
        if self.cover is None:
            return default
        return self.cover

    def name_or_alias(self, app):
        return self.realname


class MusicData:
    virtual = False
    require_ffplay = False
    audiopath: pathlib.Path
    realpath: pathlib.Path
    cover: pygame.Surface
    duration: int
    playlist: "Playlist"
    pending: bool
    audio_converting: bool
    converted: bool
    load_exc = None
    group: "PlaylistGroup|None"
    video_size: tuple[int, int] | None
    video_fps: float | None
    filesize: int | None
    loaded_cover: bool
    loading_cover: bool
    cover_path: str
    has_audio: bool
    source_exists: bool
    favorite: bool

    @property
    def yt_id(self):
        return self.realstem[-13:][1:-1]

    @property
    def yt_metadata(self):
        return (
            self.playlist.yt_metadata.get("videos", {}).get(self.yt_id, None)
            if self.playlist.yt_metadata
            else None
        )

    @property
    def alias(self):
        return self.playlist.aliases.get(self.realpath, None)

    def name_or_alias(self, app: "MILIMP"):
        alias = self.alias
        if alias is None:
            return parse_music_stem(app, self.realstem)
        return alias

    @classmethod
    def load(
        cls,
        realpath,
        playlist: "Playlist",
        loading_image=None,
        converted=False,
        startup=None,
    ):
        self = MusicData()
        self.realpath = realpath
        self.playlist = playlist
        self.cover = None
        self.duration = NotCached
        self.pending = False
        self.audio_converting = False
        self.load_exc = None
        self.converted = converted
        self.group = None
        self.video_size = NotCached
        self.video_fps = NotCached
        self.filesize = None
        self.loaded_cover = False
        self.loading_cover = False
        self.cover_path = None
        self.has_audio = True
        self.source_exists = True
        self.favorite = False

        cover_path = f"{DATA_PATH}/music_covers/{playlist.name}_{self.realstem}.png"
        if not os.path.exists(realpath):
            self.source_exists = False
            self.audiopath = self.realpath
            return self
        self.filesize = os.path.getsize(realpath)

        if self.isvideo:
            new_path = pathlib.Path(
                f"{DATA_PATH}/mp3_converted/{playlist.name}_{self.realstem}.mp3"
            ).resolve()

            if os.path.exists(new_path) and os.path.exists(cover_path):
                self.cover_path = cover_path
                self.load_cover_async(cover_path, loading_image, startup=startup)
                self.audiopath = new_path
                return self

            try:
                videofile = moviepy.VideoFileClip(str(realpath))
                self.video_size = videofile.size
                self.video_fps = videofile.fps
                self.duration = float(videofile.duration)
            except Exception:
                pygame.display.message_box(
                    "Could not load music",
                    f"The app tried to load '{realpath}' as a video file and failed. If this was an audio file with a common video extension, suffix the file with \"novideo\".",
                    "error",
                    None,
                    ("Understood",),
                )
                return
            self.videofile = videofile
            if not os.path.exists(cover_path):
                try:
                    self.pending = True
                    if loading_image is not None:
                        self.cover = loading_image
                    self.loading_cover = True
                    thread = threading.Thread(
                        target=get_cover_async,
                        args=(self, videofile, cover_path),
                        daemon=True,
                    )
                    thread.start()
                except Exception:
                    self.cover = None
            else:
                self.cover_path = cover_path
                self.load_cover_async(cover_path, loading_image, startup=startup)

            if os.path.exists(new_path):
                self.audiopath = new_path
                return self

            audiofile = videofile.audio
            if audiofile is None:
                self.has_audio = False
                new_path = realpath
            self.audiopath = new_path
            if self.has_audio:
                self.pending = True
                thread = threading.Thread(
                    target=convert_music_async,
                    args=(self, audiofile, new_path),
                    daemon=True,
                )
                thread.start()
            return self
        elif self.isconvertible:
            new_path = pathlib.Path(
                f"{DATA_PATH}/mp3_converted/{playlist.name}_{self.realstem}.mp3"
            ).resolve()

            if os.path.exists(cover_path):
                self.cover_path = cover_path
                self.load_cover_async(cover_path, loading_image, startup=startup)
            if os.path.exists(new_path):
                self.audiopath = new_path
                return self

            try:
                audiofile = moviepy.AudioFileClip(str(realpath))
                self.audiofile = audiofile
            except Exception as e:
                pygame.display.message_box(
                    "Could not load music",
                    f"Could not convert and load '{realpath}' to Mp3 due to an external exception: '{e}'.",
                    "error",
                    None,
                    ("Understood",),
                )
                return
            self.audiopath = new_path
            self.pending = True
            thread = threading.Thread(
                target=convert_music_async,
                args=(self, audiofile, new_path),
                daemon=True,
            )
            thread.start()
            return self
        else:
            if os.path.exists(cover_path):
                self.cover_path = cover_path
                self.load_cover_async(cover_path, loading_image, startup=startup)
            if self.converted:
                self.audiopath = pathlib.Path(
                    f"{DATA_PATH}/mp3_converted/{playlist.name}_{self.realstem}.mp3"
                ).resolve()
            else:
                self.audiopath = realpath
            return self

    def check_exists(self):
        if self.source_exists and not os.path.exists(self.realpath):
            self.source_exists = False

    def check(self):
        if not self.pending:
            if hasattr(self, "audiofile"):
                self.audiofile.close()
                del self.audiofile
            if hasattr(self, "videofile"):
                self.videofile.close()
                del self.videofile
        if self.load_exc is None:
            return False
        if self.audio_converting:
            self.audio_converting = False
            self.pending = False
            self.load_exc = None
            self.playlist.musictable.pop(self.audiopath)
            self.audiopath = self.realpath
            self.playlist.musictable[self.audiopath] = self
            pygame.display.message_box(
                "Could not convert music",
                f"Could not convert '{self.realpath}' to MP3 due to external exception: '{self.load_exc}'.",
                "error",
                None,
                ("Understood",),
            )
            return False
        pygame.display.message_box(
            "Could not load music",
            f"Could not convert '{self.realpath}' to audio format due to external exception: '{self.load_exc}'. Music will be removed.",
            "error",
            None,
            ("Understood",),
        )
        self.playlist.remove(self.audiopath)
        return True

    def load_cover_async(self, path, loading_image=None, startup=None):
        if self.loading_cover:
            return
        if loading_image is not None:
            self.cover = loading_image
        if startup is None:
            self.loading_cover = True
            thread = threading.Thread(
                target=load_cover_async, args=(path, self), daemon=True
            )
            thread.start()

    def cache_duration(self):
        if not self.source_exists:
            self.duration = None
            return
        if not self.has_audio:
            try:
                videofile = moviepy.VideoFileClip(str(self.realpath), audio=False)
                self.duration = float(videofile.duration)
                videofile.close()
            except Exception:
                self.duration = None
            return
        try:
            soundfile = moviepy.AudioFileClip(str(self.audiopath))
            self.duration = float(soundfile.duration)
            soundfile.close()
        except Exception:
            self.duration = None

    def cache_video_metadata(self):
        try:
            videofile = moviepy.VideoFileClip(str(self.realpath), audio=False)
            self.video_size = videofile.size
            self.video_fps = videofile.fps
            videofile.close()
        except Exception:
            self.video_size = None

    def cover_or(self, default):
        if self.cover is None:
            return default
        return self.cover

    @property
    def realstem(self):
        return self.realpath.stem

    @property
    def realname(self):
        return self.realpath.name

    @property
    def realextension(self):
        return self.realpath.suffix

    @property
    def isvideo(self):
        return self.realpath.suffix.lower()[
            1:
        ] in VIDEO_SUPPORTED and not self.realpath.stem.endswith("novideo")

    @property
    def isconvertible(self):
        return self.realpath.suffix.lower()[1:] in CONVERT_SUPPORTED

    @property
    def pos_supported(self):
        return self.realpath.suffix.lower()[1:] not in POS_UNSUPPORTED


class HistoryData:
    def __init__(self, music: MusicData, position, duration):
        self.music = music
        self.position = position
        if duration is NotCached:
            duration = "not cached"
        self.duration = duration
        if self.duration not in [None, "not cached"]:
            if int(self.position) >= int(self.duration - 0.01):
                self.position = 0

    def get_save_data(self):
        duration = self.duration
        if duration is NotCached:
            duration = "not cached"
        return {
            "audiopath": str(self.music.audiopath),
            "position": self.position,
            "playlist": self.music.playlist.name,
            "duration": duration,
        }

    @classmethod
    def load_from_data(self, data: dict, app: "MILIMP"):
        playlist = None
        for pobj in app.playlists:
            if pobj.name == data["playlist"]:
                playlist = pobj
                break
        if playlist is None:
            return
        musicobj = playlist.musictable.get(pathlib.Path(data["audiopath"]), None)
        if musicobj is None:
            return
        if data["duration"] is not None and data["duration"] != "not cached":
            musicobj.duration = data["duration"]
        return HistoryData(musicobj, data["position"], data["duration"])


class PlaylistGroup:
    def __init__(
        self,
        name,
        playlist: "Playlist",
        musics: list[MusicData],
        idx=0,
        collapsed=True,
        mode="h",
    ):
        self.name: str = name
        self.idx = idx
        self.collapsed = collapsed
        self.mode = mode
        self.playlist = playlist
        self.musics = musics
        for music in self.musics:
            music.group = self

    def get_save_data(self):
        return {
            "name": self.name,
            "idx": self.idx,
            "collapsed": self.collapsed,
            "mode": self.mode,
            "paths": [str(music.audiopath) for music in self.musics],
        }

    def remove(self, music: "MusicData"):
        self.musics.remove(music)
        music.group = None
        music.playlist.musiclist.remove(music)
        music.playlist.musiclist.insert(self.idx, music)


class Playlist:
    def __init__(
        self,
        name,
        filepaths,
        groups_data=None,
        yt_link=None,
        yt_name=None,
        aliases=None,
        folder_path=None,
        favorites=None,
        loading_image=None,
        startup=None,
    ):
        self.name = name
        self.cover = None
        self.yt_link = yt_link
        self.yt_name = yt_name
        self.folder_path = folder_path
        if self.folder_path is not None:
            self.folder_path = pathlib.Path(self.folder_path)
        if groups_data is None:
            groups_data = []
        self.groups: list[PlaylistGroup] = []
        if aliases is None:
            aliases = {}
        self.aliases = aliases
        if favorites is None:
            favorites = []
        self.favorites = favorites
        self.yt_metadata = None
        if self.is_yt:
            if os.path.exists(f"{DATA_PATH}/yt_playlists"):
                fname = f"{DATA_PATH}/yt_playlists/{self.name}"
                if not os.path.exists(fname):
                    os.mkdir(fname)
            if os.path.exists(f"{DATA_PATH}/yt_playlists/{self.name}/{self.name}.json"):
                with open(
                    f"{DATA_PATH}/yt_playlists/{self.name}/{self.name}.json", "r"
                ) as pmeta:
                    self.yt_metadata = json.load(pmeta)

        if os.path.exists(f"{DATA_PATH}/covers/{self.name}.png"):
            if loading_image is not None:
                self.cover = loading_image
            thread = threading.Thread(
                target=load_cover_async,
                args=(f"{DATA_PATH}/covers/{self.name}.png", self),
                daemon=True,
            )
            thread.start()

        self.musiclist: list[MusicData] = []
        self.musictable: dict[pathlib.Path, MusicData] = {}
        for path in filepaths:
            self.load_music(path, loading_image, startup=startup)

        if startup is not None:
            for music in self.musiclist:
                if music.realpath in self.favorites:
                    startup.favorites.append(music)
                    music.favorite = True

        if len(groups_data) > 0 and isinstance(groups_data[0], PlaylistGroup):
            self.groups = groups_data
        else:
            for gdata in groups_data:
                self.groups.append(
                    PlaylistGroup(
                        gdata["name"],
                        self,
                        [
                            self.musictable[pathlib.Path(gdpath)]
                            for gdpath in gdata["paths"]
                        ],
                        gdata.get("idx", 0),
                        gdata.get("collapsed", True),
                        gdata.get("mode", "h"),
                    )
                )

    @property
    def is_yt(self):
        return self.yt_link is not None

    @property
    def is_folder(self):
        return self.folder_path is not None

    @property
    def display_name(self):
        if self.is_yt:
            return self.yt_name
        return self.name

    @property
    def realpaths(self):
        return [music.realpath for music in self.musiclist]

    def get_group_sorted_musics(self, paths=False, groups=False):
        ungrouped_musics = [
            (music.audiopath if paths else music)
            for music in self.musiclist
            if music.group is None
        ]
        i_offset = 0
        for group in sorted(self.groups, key=lambda g: g.idx):
            if groups:
                if len(group.musics) > 0:
                    ungrouped_musics.insert(group.idx, group)
            elif len(group.musics) > 0:
                ungrouped_musics = (
                    ungrouped_musics[: group.idx + i_offset]
                    + (
                        [music.audiopath for music in group.musics]
                        if paths
                        else group.musics
                    )
                    + ungrouped_musics[group.idx + i_offset :]
                )
                i_offset += len(group.musics) - 1
        return ungrouped_musics

    def load_music(self, path, loading_image=None, idx=-1, startup=None):
        converted = False
        if isinstance(path, list):
            path = path[0]
            converted = True
        if path in self.musictable or path in self.realpaths:
            return
        music_data = MusicData.load(
            path, self, loading_image, converted, startup=startup
        )
        if music_data is None:
            return
        if idx != -1:
            self.musiclist.insert(idx, music_data)
        else:
            self.musiclist.append(music_data)
        self.musictable[music_data.audiopath] = music_data
        return music_data

    def remove(self, path):
        music = self.musictable.pop(path)
        self.musiclist.remove(music)
        if music.group is not None:
            music.group.remove(music)
