from ui.common import *
from ui.common.data import MusicData, NotCached, AsyncVideoclipGetter
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
        self.music_videoclip_cover = None
        self.last_videoclip_cover = None
        self.bg_effect = False

    @property
    def music_videoclip(self):
        if self.async_videoclip is None:
            return None
        return self.async_videoclip.videoclip

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
            pygame.mixer.music.set_pos(pos)

    def get_music_pos(self):
        return (
            self.music_play_offset
            + (pygame.time.get_ticks() - self.music_play_time) / 1000
        )

    def play_music(self, music: MusicData, idx):
        if music.pending:
            self.end_music()
            return
        self.need_low_fps = False
        if self.async_videoclip is not None:
            self.async_videoclip.alive = False
            if self.videoclip_threaded:
                self.async_videoclip.thread.join()
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
        self.music_videoclip_cover = None
        self.last_videoclip_cover = None
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
                self.async_videoclip.load_videoclip()
        if self.music.has_audio:
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
        self.app.when_end_music()
        self.bg_effect = False
        if self.music is not None:
            self.app.add_to_history()
        self.music = None
        self.music_paused = False
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        if self.music_videoclip is not None:
            self.music_videoclip.close()
        self.async_videoclip = None
        self.app.music_controls.when_end_music()

    def volume_up(self):
        self.volume += 0.05
        if self.volume > 1:
            self.volume = 1
        pygame.mixer.music.set_volume(self.volume)

    def volume_down(self):
        self.volume -= 0.05
        if self.volume < 0:
            self.volume = 0
        pygame.mixer.music.set_volume(self.volume)

    def music_auto_finish(self):
        if self.music_loops:
            self.play_music(self.music, self.music_index)
            return
        if self.shuffle:
            music_available = self.music.playlist.musiclist.copy()
            music_available.remove(self.state.music)
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
            if self.music.has_audio:
                pygame.mixer.music.unpause()
            self.music_paused = False
        else:
            if self.music.has_audio:
                pygame.mixer.music.pause()
            self.music_paused = True
        self.app.discord_presence.update()

    def update_bg_effect(self):
        self.bg_effect = False
        if self.music is None:
            return
        if self.app.modal_state == "fullscreen" or self.app.super_fullscreen:
            return
        if not self.app.focused:
            return
        image = self.music.cover
        if self.music_videoclip_cover is not None:
            image = self.music_videoclip_cover
            if self.async_videoclip.small_output is not None:
                image = self.async_videoclip.small_output
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
        self.music_videoclip_cover = None
        if self.music is None:
            return
        if self.async_videoclip is None:
            return
        if self.app.music_controls.track_hover_pos is not None:
            pos_override = self.app.music_controls.track_hover_pos
        if not self.app.focused and self.app.music_controls.minip.window is None:
            return
        if self.music.duration in [None, NotCached]:
            return
        if self.music_paused and not pos_override:
            self.music_videoclip_cover = self.last_videoclip_cover
            return
        if self.music_videoclip is not None:
            pos = pos_override if pos_override else self.get_music_pos()
            if pos >= self.music.duration:
                self.music_videoclip_cover = SURF
                return
            try:
                self.async_videoclip.active = True
                self.async_videoclip.time = pos
                self.async_videoclip.framerate = self.app.target_framerate
                if not self.videoclip_threaded:
                    self.async_videoclip.update()
                self.music_videoclip_cover = self.async_videoclip.output
            except Exception:
                return
            self.last_videoclip_cover = self.music_videoclip_cover

    def get_music_cover(self, focused=None):
        if focused is None:
            focused = self.app.focused
        cover = ICONS.music_cover
        if self.music.cover is not None:
            cover = self.music.cover
        if self.music_videoclip_cover is not None and focused:
            cover = self.music_videoclip_cover
        return cover

    def get_scaled_cover(self, cover, it: mili.Interaction, can_use_renderer=False):
        scaled = False
        current = (
            self.async_videoclip is not None
            and self.music_videoclip_cover is not None
            and not self.music_paused
            and (not USE_RENDERER or can_use_renderer)
        )
        if current:
            self.app.music_controls.videoclip_rects.append((0, it.data.rect))
            if it.data.rect.size in (out := self.async_videoclip.scaled_output):
                cover = out[it.data.rect.size]
                scaled = True
        return scaled, cover

    def change_volume(self, value):
        self.volume = pygame.math.clamp(value, 0, 1)
        pygame.mixer.music.set_volume(self.volume)

    def mute(self):
        if self.volume > 0:
            self.vol_before_mute = self.volume
            self.volume = 0
        else:
            self.volume = self.vol_before_mute
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
