from ui.common import *
from ui.common.data import MusicData

class MusicState:
    def __init__(self):
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
