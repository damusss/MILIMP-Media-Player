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
            zfile.write("data/settings.json", "settings.json")
            zfile.write("data/gpu.json", "gpu.json")
        if categories["Playlists"]:
            zfile.write("data/playlists.json", "playlists.json")
        if categories["History"]:
            zfile.write("data/history.json", "history.json")
            zfile.write("data/search_results.json", "search_results.json")
        if categories["Playlist Covers"]:
            zfile.mkdir("covers")
            for file in os.listdir("data/covers"):
                zfile.write(f"data/covers/{file}", f"covers/{file}")
        if categories["Music Covers"]:
            zfile.mkdir("music_covers")
            for file in os.listdir("data/music_covers"):
                zfile.write(f"data/music_covers/{file}", f"music_covers/{file}")
        if categories["MP3 Converted"]:
            zfile.mkdir("mp3_converted")
            for file in os.listdir("data/mp3_converted"):
                zfile.write(f"data/mp3_converted/{file}", f"mp3_converted/{file}")
        if categories["YT Downloads"]:
            for folder, subfolders, files in os.walk("data/yt_downloads"):
                zfile.mkdir(folder.removeprefix("data/"))
                for file in files:
                    zfile.write(os.path.join(f"{folder.removeprefix('data/')}", file))
    comp.backing_up = False
    comp.app.notify(NOTIF.DOWNLOAD, f"Backup saved to '{path}'")


class MenuButton:
    def __init__(self, icon, action, animation, br="50", tooltip=""):
        self.icon = icon
        self.action = action
        self.animation = animation
        self.br = br
        self.tooltip = tooltip


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


class AsyncVideoclipGetter:
    def __init__(self, realpath, app: "MILIMP"):
        self.app = app
        self.state = app.state
        self.first = True
        self.realpath = realpath
        self.thread = None
        self.active = False
        self.videoclip = None
        self.time = None
        self.output = None
        self.scaled_output = {}
        self.framerate = 60
        self.alive = True
        self.clock = pygame.Clock()
        self.rects = []
        self.close_on_kill = True
        self.desktop_size = pygame.Vector2(pygame.display.get_desktop_sizes()[0])
        self.is_large_media = False
        self.remake_videoclip = False
        self.fps_history = []
        self.last_fps_check = pygame.time.get_ticks()
        self.current_fps = 0
        self.original_size = None
        self.videoclip_scaled = False
        self.textures = {}

    def make_videoclip(self):
        if self.videoclip is not None:
            self.videoclip.close()
        self.videoclip_scaled = False
        filesize = os.path.getsize(self.realpath)
        self.is_large_media = filesize > LARGE_MEDIA_SIZE
        resize = (
            (
                "neighbor"
                if USE_RENDERER
                else "fast_bilinear"
                if self.state.videoclip_threaded
                else "neighbor"
            )
            if self.is_large_media
            else "bicubic"
        )
        self.videoclip = moviepy.VideoFileClip(
            self.realpath, audio=False, resize_algorithm=resize
        )
        desktop = self.desktop_size
        if self.is_large_media:
            desktop = self.desktop_size / (
                1.2 if USE_RENDERER else 1.5 if self.state.videoclip_threaded else 1
            )
        size = pygame.Vector2(self.videoclip.size)
        self.original_size = size
        new_size = None
        if size.x > desktop.x:
            change_ratio = desktop.x / size.x
            new_w = desktop.x
            new_h = size.y * change_ratio
            if new_h > desktop.y:
                new_h = desktop.y
                ratio = size.y / size.x
                new_w = new_h * ratio
            new_size = (int(new_w), int(new_h))
        elif size.y > desktop.y:
            ratio = size.y / size.x
            new_h = desktop.y
            new_w = new_h * ratio
            if new_w > desktop.x:
                ratio = size.x / size.y
                new_w = desktop.x
                new_h = new_w * ratio
            new_size = (int(new_w), int(new_h))
        if new_size is not None:
            self.videoclip.close()
            self.videoclip = moviepy.VideoFileClip(
                self.realpath,
                target_resolution=new_size,
                audio=False,
                resize_algorithm=resize,
            )
            self.videoclip_scaled = True

    def load_videoclip(self):
        try:
            self.make_videoclip()
        except Exception as e:
            self.alive = False
            print(e)
        self.first = False

    def update(self):
        if (self.videoclip is None and self.first) or self.remake_videoclip:
            self.load_videoclip()
            self.remake_videoclip = False
        if not self.active or self.videoclip is None or self.time is None:
            self.clock.tick(10)
            return
        if (
            self.state.videoclip_threaded
            and not self.state.need_low_fps
            and self.state.user_framerate != 30
        ):
            self.clock.tick(min(self.videoclip.fps + 5, self.framerate))
            self.current_fps = self.clock.get_fps()
            if self.state.videoclip_on and len(self.fps_history) < 200:
                now = pygame.time.get_ticks()
                if self.current_fps != 0 and now - self.last_fps_check >= 500:
                    self.fps_history.append(self.current_fps)
                    self.last_fps_check = now
                if len(self.fps_history) > 6:
                    average = sum(self.fps_history) / len(self.fps_history)
                    if average < 15:
                        self.state.need_low_fps = True
        if self.state.videoclip_on:
            self.output = pygame.surfarray.make_surface(
                numpy.transpose(self.videoclip.get_frame(self.time), (1, 0, 2))
            )
            self.scaled_output = {}
            self.small_output = None
            small_output = None
            smallest = float("inf")
            for pad, rect in self.rects:
                res = mili.fit_image(rect, self.output, pad, pad, smoothscale=True)
                ores = res
                if USE_RENDERER:
                    if rect.size in self.textures:
                        tex = self.textures[rect.size]
                        tex.update(res)
                        res = tex
                    else:
                        tex = pgvideo.Texture.from_surface(self.app.canva, res)
                        self.textures[rect.size] = tex
                        res = tex
                self.scaled_output[rect.size] = res
                if rect.w * rect.h < smallest:
                    small_output = ores
                    smallest = rect.w * rect.h
            self.small_output = small_output
        else:
            self.output = None
            self.scaled_output = {}
            self.small_output = None

    def loop(self):
        while self.alive:
            self.update()
        if self.close_on_kill:
            if self.videoclip is not None:
                self.videoclip.close()
            self.videoclip = None


class MusicData:
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

        cover_path = f"data/music_covers/{playlist.name}_{self.realstem}.png"
        if not os.path.exists(realpath):
            self.source_exists = False
            self.audiopath = self.realpath
            return self
        self.filesize = os.path.getsize(realpath)

        if self.isvideo:
            new_path = pathlib.Path(
                f"data/mp3_converted/{playlist.name}_{self.realstem}.mp3"
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
                self.duration = videofile.duration
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
                f"data/mp3_converted/{playlist.name}_{self.realstem}.mp3"
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
                    f"data/mp3_converted/{playlist.name}_{self.realstem}.mp3"
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
                self.duration = videofile.duration
                videofile.close()
            except Exception:
                self.duration = None
            return
        try:
            soundfile = moviepy.AudioFileClip(str(self.audiopath))
            self.duration = soundfile.duration
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
        self, name, filepaths, groups_data=None, loading_image=None, startup=None
    ):
        self.name = name
        self.cover = None
        if groups_data is None:
            groups_data = []
        self.groups: list[PlaylistGroup] = []

        if os.path.exists(f"data/covers/{self.name}.png"):
            if loading_image is not None:
                self.cover = loading_image
            thread = threading.Thread(
                target=load_cover_async,
                args=(f"data/covers/{self.name}.png", self),
                daemon=True,
            )
            thread.start()

        self.musiclist: list[MusicData] = []
        self.musictable: dict[pathlib.Path, MusicData] = {}
        for path in filepaths:
            self.load_music(path, loading_image, startup=startup)

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
