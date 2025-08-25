from ui.common import *
from ui.common.data import (
    MusicData,
    NotCached,
    AsyncVideoclipGetter,
    AsyncFFPLAYAudioPlayer,
    VirtualPlayingMusic,
)
import time
import threading
import random


class MusicState:
    def __init__(self, app: "MILIMP"):
        self.app = app
        self.user_framerate = 60
        self.volume = 1
        self.loops = True
        self.shuffle = False
        self.videoclip_on = True
        self.videoclip_threaded = True
        self.vol_before_mute = 1
        self.need_low_fps = False
        self.music: MusicData = None
        self.music_paused = False
        self.music_index = -1
        self.music_play_time = 0
        self.music_play_offset = 0
        self.music_loops = False
        self.music_start_time = None
        self.async_videoclip: AsyncVideoclipGetter = None
        self.async_audioplayer: AsyncFFPLAYAudioPlayer = None
        self.bg_effect = False
        self.queue: list[MusicData] = []

    @property
    def music_container(self):
        if self.async_videoclip is None:
            return None
        return self.async_videoclip.container

    def set_music_pos(self, pos):
        if (
            self.music is None
            or not self.music.pos_supported
            or self.music.duration in [None, NotCached]
        ):
            return
        self.music_play_time = pygame.time.get_ticks()
        self.music_play_offset = pos
        if self.music.has_audio:
            if self.music.require_ffplay:
                if self.async_audioplayer is not None:
                    self.async_audioplayer.remake_pipe = True
                    while self.async_audioplayer.remake_pipe:
                        ...
            else:
                pygame.mixer.music.set_pos(pos)

    def get_music_pos(self):
        return (
            self.music_play_offset
            + (pygame.time.get_ticks() - self.music_play_time) / 1000
        )

    def play_music(self, music: MusicData | VirtualPlayingMusic, idx):
        if music.pending:
            self.end_music()
            return
        self.need_low_fps = False
        if self.async_videoclip is not None:
            self.async_videoclip.alive = False
            if self.videoclip_threaded:
                self.async_videoclip.thread.join()
        if self.async_audioplayer is not None:
            self.async_audioplayer.alive = False
            self.async_audioplayer.thread.join()
        self.async_videoclip = None
        if self.music is not None:
            self.app.add_to_history()
        if not os.path.exists(music.audiopath):
            pygame.display.message_box(
                "Failed playing music",
                "The request music was renamed or deleted externally.",
                "error",
                None,
                ("Understood",),
            )
            return
        self.music = music
        self.music_paused = False
        self.music_index = idx
        self.music_start_time = time.time()
        self.music_play_offset = 0
        if self.music.duration is NotCached:
            self.music.cache_duration()
        if self.music.isvideo:
            self.async_videoclip = AsyncVideoclipGetter(
                str(self.music.realpath), self.app
            )
            if self.videoclip_threaded:
                thread = threading.Thread(target=self.async_videoclip.loop)
                self.async_videoclip.thread = thread
                thread.start()
            else:
                self.async_videoclip.load_container()
        if self.music.has_audio:
            if self.music.require_ffplay:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                self.async_audioplayer = AsyncFFPLAYAudioPlayer(self.app)
                thread = threading.Thread(target=self.async_audioplayer.loop)
                self.async_audioplayer.thread = thread
                thread.start()
            else:
                pygame.mixer.music.load(self.music.audiopath)
                pygame.mixer.music.play(0)
                pygame.mixer.music.set_endevent(MUSIC_ENDEVENT)
        else:
            pygame.mixer.music.set_endevent(0)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        pygame.mixer.music.set_volume(self.volume)
        self.music_play_time = pygame.time.get_ticks()
        self.app.discord_presence.update()
        self.app.music_controls.when_play()

    def end_music(self):
        self.need_low_fps = False
        if self.async_videoclip is not None:
            self.async_videoclip.alive = False
            if self.videoclip_threaded:
                self.async_videoclip.thread.join()
        if self.async_audioplayer is not None:
            self.async_audioplayer.alive = False
            self.async_audioplayer.thread.join()
        self.app.when_end_music()
        self.bg_effect = False
        if self.music is not None:
            self.app.add_to_history()
        if self.music in self.queue:
            self.queue.remove(self.music)
        self.music = None
        self.music_paused = False
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        if self.music_container is not None:
            self.music_container.close()
        self.async_videoclip = None
        self.async_audioplayer = None
        self.app.music_controls.when_end_music()

    def volume_up(self):
        self.volume += 0.05
        if self.volume > 1:
            self.volume = 1
        if self.async_audioplayer is not None:
            self.async_audioplayer.remake_pipe = True
            while self.async_audioplayer.remake_pipe:
                ...
        pygame.mixer.music.set_volume(self.volume)

    def volume_down(self):
        self.volume -= 0.05
        if self.volume < 0:
            self.volume = 0
        if self.async_audioplayer is not None:
            self.async_audioplayer.remake_pipe = True
            while self.async_audioplayer.remake_pipe:
                ...
        pygame.mixer.music.set_volume(self.volume)

    def music_auto_finish(self):
        if self.music_loops:
            self.play_music(self.music, self.music_index)
            return
        if len(self.queue) > 0:
            queueidx = 0
            if self.music in self.queue:
                queueidx = self.queue.index(self.music)
                self.queue.remove(self.music)
                if len(self.queue) > 0:
                    music = self.queue[min(queueidx, len(self.queue) - 1)]
                    self.play_music(
                        music, music.playlist.get_group_sorted_musics().index(music)
                    )
                    self.app.playlist_viewer.set_scroll_to_music()
                    return
        if self.shuffle and not self.music.require_ffplay:
            music_available = self.music.playlist.musiclist.copy()
            music_available.remove(self.music)
            new_music = random.choice(music_available)
            doscroll = (
                new_music.group is not self.music.group
                or new_music.group is None
                or new_music.group.mode == "v"
            )
            self.play_music(
                new_music,
                self.music.playlist.musiclist.index(new_music),
            )
            if doscroll:
                self.app.playlist_viewer.set_scroll_to_music(True)
            return
        self.skip_next(True, True)

    def skip_next(self, stop_if_end=False, consider_loop=False):
        if self.music.require_ffplay:
            self.end_music()
            return
        if len(self.music.playlist.musiclist) <= 0:
            if stop_if_end:
                self.end_music()
            return
        new_idx = self.music_index + 1
        if new_idx >= len(self.music.playlist.musiclist):
            if consider_loop and self.loops:
                new_idx = 0
            else:
                if stop_if_end:
                    self.end_music()
                return
        allmusics = self.music.playlist.get_group_sorted_musics()
        new_music = allmusics[new_idx]
        doscroll = (
            new_music.group is not self.music.group
            or new_music.group is None
            or new_music.group.mode == "v"
        )
        self.play_music(new_music, new_idx)
        if doscroll:
            self.app.playlist_viewer.set_scroll_to_music(True)

    def skip_previous(self):
        if self.music.require_ffplay:
            self.end_music()
            return
        if len(self.music.playlist.musiclist) <= 0:
            return
        new_idx = self.music_index - 1
        if new_idx < 0:
            return
        allmusics = self.music.playlist.get_group_sorted_musics()
        new_music = allmusics[new_idx]
        doscroll = (
            new_music.group is not self.music.group
            or new_music.group is None
            or new_music.group.mode == "v"
        )
        self.play_music(new_music, new_idx)
        if doscroll:
            self.app.playlist_viewer.set_scroll_to_music(True, -1)

    def rewind(self):
        self.play_music(self.music, self.music_index)

    def move_in_track(self, amount):
        if not self.music.pos_supported and self.music.duration in [
            None,
            NotCached,
        ]:
            return
        pos = self.get_music_pos()
        new_pos = pygame.math.clamp(pos + amount, 0, self.music.duration)
        if new_pos >= self.music.duration:
            if self.music_loops:
                new_pos = 0
            else:
                self.skip_next()
                return
        self.app.music_controls.slider.valuex = new_pos / self.music.duration
        self.set_music_pos(new_pos)
        self.update_videoclip_cover(new_pos)
        self.update_bg_effect()

    def forward_5(self):
        self.move_in_track(5)

    def previous_5(self):
        self.move_in_track(-5)

    def pause(self):
        if self.music_paused:
            self.music_paused = False
            if self.music.has_audio:
                if self.music.require_ffplay:
                    if self.async_audioplayer is not None:
                        self.async_audioplayer.remake_pipe = True
                        while self.async_audioplayer.remake_pipe:
                            ...
                else:
                    pygame.mixer.music.unpause()

        else:
            self.music_paused = True
            if self.music.has_audio:
                if self.music.require_ffplay:
                    if self.async_audioplayer is not None:
                        self.async_audioplayer.remake_pipe = True
                        while self.async_audioplayer.remake_pipe:
                            ...
                else:
                    pygame.mixer.music.pause()

        self.app.discord_presence.update()

    def update_bg_effect(self):
        self.bg_effect = False
        if (
            self.music is None
            or self.app.modal_state == "fullscreen"
            or self.app.super_fullscreen
            or not self.app.focused
            or self.async_videoclip is None
        ):
            return
        image = None
        smallest = float("inf")
        for rect in self.async_videoclip.rects:
            if rect.rect is None or not rect.active:
                continue
            size = rect.rect.w * rect.rect.h
            if size < smallest:
                image = rect.output
                smallest = size
        if image is None:
            return
        if self.music_paused:
            self.bg_effect = True
            return
        if isinstance(image, pygame.Surface):
            color = pygame.Color(pygame.transform.average_color(image))
            color.a = 40
            self.bg_effect = True
            self.app.bg_effect_image.fill(color)

    def update_videoclip_cover(self, pos_override=None):
        if self.music is None or self.async_videoclip is None:
            return
        self.async_videoclip.active = False
        self.async_videoclip.miniplayer_rect.active = (
            self.app.music_controls.minip.window is not None
        )
        self.async_videoclip.main_rect.active = True
        if self.app.music_controls.track_hover_pos is not None:
            pos_override = self.app.music_controls.track_hover_pos
        if not self.app.focused and self.app.music_controls.minip.window is None:
            return
        if self.music.duration in [None, NotCached]:
            return
        if self.music_paused and not pos_override:
            return
        if self.async_videoclip is not None:
            pos = pos_override if pos_override else self.get_music_pos()
            if pos >= self.music.duration:
                return
            try:
                self.async_videoclip.active = True
                self.async_videoclip.time = pos
                self.async_videoclip.framerate = self.app.target_framerate
                if not self.videoclip_threaded:
                    self.async_videoclip.update()
            except Exception:
                return

    def get_music_cover(self, focused=None):
        if focused is None:
            focused = self.app.focused
        cover = ICONS.music_cover
        if self.music.cover is not None:
            cover = self.music.cover
        return cover

    def change_volume(self, value):
        self.volume = pygame.math.clamp(value, 0, 1)
        if self.async_audioplayer is not None:
            self.async_audioplayer.remake_pipe = True
            while self.async_audioplayer.remake_pipe:
                ...
        pygame.mixer.music.set_volume(self.volume)

    def mute(self):
        if self.volume > 0:
            self.vol_before_mute = self.volume
            self.volume = 0
        else:
            self.volume = self.vol_before_mute
        if self.async_audioplayer is not None:
            self.async_audioplayer.remake_pipe = True
            while self.async_audioplayer.remake_pipe:
                ...
        pygame.mixer.music.set_volume(self.volume)

    def toggle_thread(self):
        getter = self.async_videoclip
        if getter is None or self.music is None:
            self.videoclip_threaded = not self.videoclip_threaded
            return
        if self.videoclip_threaded:
            getter.alive = False
            getter.close_on_kill = False
            getter.thread.join()
            getter.close_on_kill = True
            getter.remake_videoclip = True
        else:
            getter.first = True
            thread = threading.Thread(target=getter.loop)
            getter.alive = True
            getter.thread = thread
            getter.remake_videoclip = True
            thread.start()
        self.videoclip_threaded = not self.videoclip_threaded
