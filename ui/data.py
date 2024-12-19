import numpy
import pygame
import pathlib
import threading
from ui.common import *
import moviepy.editor as moviepy


def load_cover_async(path, obj):
    obj.cover = pygame.image.load(path).convert_alpha()


def get_cover_async(music: "MusicData", videofile: moviepy.VideoClip, cover_path):
    try:
        frame: numpy.ndarray = videofile.get_frame(videofile.duration / 2)
        surface = pygame.image.frombytes(frame.tobytes(), videofile.size, "RGB")
        pygame.image.save(surface, cover_path)
        music.cover = surface
    except Exception:
        music.cover = None


def convert_music_async(music: "MusicData", audiofile: moviepy.AudioClip, new_path):
    try:
        audiofile.write_audiofile(str(new_path), verbose=True)
        music.pending = False
        if music.audio_converting:
            music.converted = True
        music.audio_converting = False
    except Exception as e:
        music.load_exc = e


class NotCached: ...


class AsyncVideoclipGetter:
    def __init__(self, videoclip):
        self.thread = None
        self.active = False
        self.videoclip = videoclip
        self.time = None
        self.output = None
        self.scaled_output = {}
        self.framerate = 60
        self.alive = True
        self.clock = pygame.Clock()
        self.rects = []

    def loop(self):
        while self.alive:
            self.clock.tick(self.framerate)
            if not self.active or self.videoclip is None or self.time is None:
                continue
            frame = self.videoclip.get_frame(self.time)
            self.output = pygame.image.frombytes(
                frame.tobytes(), self.videoclip.size, "RGB"
            )
            self.scaled_output = {}
            for pad, rect in self.rects:
                res = mili.fit_image(rect, self.output, pad, pad, smoothscale=True)
                self.scaled_output[rect.size] = res


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

    @classmethod
    def load(cls, realpath, playlist: "Playlist", loading_image=None, converted=False):
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

        cover_path = f"data/music_covers/{playlist.name}_{self.realstem}.png"
        if not os.path.exists(realpath):
            pygame.display.message_box(
                "Could not load music",
                f"Could not load music '{realpath}' as the file doesn't exist anymore. Music will be skipped.",
                "error",
                None,
                ("Understood",),
            )
            return

        if self.isvideo:
            new_path = pathlib.Path(
                f"data/mp3_converted/{playlist.name}_{self.realstem}.mp3"
            ).resolve()

            if os.path.exists(new_path) and os.path.exists(cover_path):
                self.load_cover_async(cover_path, loading_image)
                self.audiopath = new_path
                return self

            videofile = moviepy.VideoFileClip(str(realpath))
            self.videofile = videofile
            if not os.path.exists(cover_path):
                try:
                    self.pending = True
                    if loading_image is not None:
                        self.cover = loading_image
                    thread = threading.Thread(
                        target=get_cover_async, args=(self, videofile, cover_path)
                    )
                    thread.start()
                except Exception:
                    self.cover = None
            else:
                self.load_cover_async(cover_path, loading_image)

            if os.path.exists(new_path):
                self.audiopath = new_path
                return self

            audiofile = videofile.audio
            if audiofile is None:
                pygame.display.message_box(
                    "Could not load music",
                    f"Could not convert '{realpath}' to audio format: the video has no associated audio. Music will be skipped.",
                    "error",
                    None,
                    ("Understood",),
                )
                return
            self.audiopath = new_path
            self.pending = True
            thread = threading.Thread(
                target=convert_music_async, args=(self, audiofile, new_path)
            )
            thread.start()
            return self
        elif self.isconvertible:
            new_path = pathlib.Path(
                f"data/mp3_converted/{playlist.name}_{self.realstem}.mp3"
            ).resolve()

            if os.path.exists(cover_path):
                self.load_cover_async(cover_path, loading_image)
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
                target=convert_music_async, args=(self, audiofile, new_path)
            )
            thread.start()
            return self
        else:
            if os.path.exists(cover_path):
                self.load_cover_async(cover_path, loading_image)
            if self.converted:
                self.audiopath = pathlib.Path(
                    f"data/mp3_converted/{playlist.name}_{self.realstem}.mp3"
                ).resolve()
            else:
                self.audiopath = realpath
            return self

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

    def load_cover_async(self, path, loading_image=None):
        if loading_image is not None:
            self.cover = loading_image
        thread = threading.Thread(target=load_cover_async, args=(path, self))
        thread.start()

    def cache_duration(self):
        try:
            soundfile = moviepy.AudioFileClip(str(self.audiopath))
            self.duration = soundfile.duration
            soundfile.close()
        except Exception:
            self.duration = None

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
        return self.realpath.suffix.lower()[1:] in VIDEO_SUPPORTED

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
    def load_from_data(self, data: dict, app: "MusicPlayerApp"):
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
    def __init__(self, name, filepaths, groups_data=None, loading_image=None):
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
            )
            thread.start()

        self.musiclist: list[MusicData] = []
        self.musictable: dict[pathlib.Path, MusicData] = {}
        for path in filepaths:
            self.load_music(path, loading_image)

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

    def load_music(self, path, loading_image=None, idx=-1):
        converted = False
        if isinstance(path, list):
            path = path[0]
            converted = True
        if path in self.musictable or path in self.realpaths:
            return
        music_data = MusicData.load(path, self, loading_image, converted)
        if music_data is None:
            return
        if idx != -1:
            self.musiclist.insert(idx, music_data)
        else:
            self.musiclist.append(music_data)
        self.musictable[music_data.audiopath] = music_data

    def remove(self, path):
        music = self.musictable.pop(path)
        self.musiclist.remove(music)
        if music.group is not None:
            music.group.remove(music)
