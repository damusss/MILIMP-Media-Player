# MILI Music Player

A MILI UI demo featuring a rich music player.<br>
[MILI Github](https://github.com/damusss/mili), [MILI PyPI](https://pypi.org/project/mili-ui/)

# Features

-   Perks

    -   Tooltips
    -   Modern, fast, responsive UI (split screen for wide windows)
    -   30/60 FPS, Power saving, Async loading/processing
    -   Custom titlebar/borders
    -   Rich Discord presence
    -   History
    -   Keybinds

-   Playlists (load from folder, rename, delete, reorder, upload/generate cover, search)

    -   Playlist Groups (collapsable, horizontal/vertical layout)

-   Musics (add, rename, delete, reorder, move to playlist, show in explorer, convert to MP3)

    -   **Audio and Video**: MP4, WEBM, AVI, MKV, MOV, FLV, WMV, M4V, 3GP, MPEG, MPG, OGV, MTS, TS

    -   **Audio Only**: MP3, WAV, OGG, FLAC, OPUS, WV, MOD, AIFF, AAC, M4A, WMA, ALAC, AMR, AU, SND, MPC, TTA, CAF

    -   **Unsupported Track Positioning**: WAV, OPUS, WV, AIFF

-   Controls
    -   Pause, Volume/mute, Next/previous/auto-next, Rewind
    -   Background effects
    -   Loop (playlist/music), Shuffle
    -   Miniplayer
    -   Video player (+ maximized/fullscreen)

The file extension must always match the music format.
Due to SDL limitations only a subset of the supported formats can be played directly, the rest will have a copy converted to MP3.
Videos must have an associated audio track to be valid.

# Special Gestures

-   Hold the mouse wheel button and scroll to reorder playlists and musics (hold shift to move faster)
-   Click on the currently playing track's cover/video to jump to the track in the playlist
-   Hover a playlist's cover or the currently playing track's cover/video for a fraction of a second to view it in full screen
-   Middle click the playing track's video cover to set the frame as the music cover in the playlist. Delete the cover file from the data/music_covers folder to revert
-   Hold shift while hovering the currently playing track's slider to view the video frame at that position

# Keyboard Shortcuts

Keybinds are configurable in the settings.
The only reserved keys are **ENTER** and the media control buttons.
The only allowed modifier is **CTRL**.
Note that the volume buttons do not change the app's volume. It is advised to let them only modify the system's volume.

-   **ESCAPE**: Back
-   **ENTER**: Confirm
-   **S**: Toggle settings
-   **F11**: Toggle music maximize
-   **TAB**: Toggle player extra controls
-   **UP**/**KP 8**: Volume up
-   **DOWN**/**KP 2**: Volume down
-   **SPACE**/**ENTER**/**KP ENTER**/**AUDIO PLAY**: Play/pause music
-   **LEFT**/**KP 4**/**AUDIO PREVIOUS**: Previous track
-   **RIGHT**/**KP 6**/**AUDIO NEXT**: Next track
-   **CTRL** + **LEFT**/**CTRL** + **KP 4**: Back 5 seconds
-   **CTRL** + **RIGHT**/**CTRL** + **KP 6**: Skip 5 seconds
-   **CTRL** + **Q**: Quit
-   **CTRL** + **A**: New playlist/Add music
-   **CTRL** + **S**: Save
-   **CTRL** + **H**: Open history
-   **CTRL** + **K**: Open keybindings
-   **CTRL** + **F**: Toggle playlist search
-   **CTRL** + **BACKSPACE**: Erase input field
-   **CTRL** + **C**: Toggle change cover
-   **CTRL** + **E**: End music
-   **CTRL** + **R**: Rewind music
-   **CTRL** + **D**: Toggle miniplayer
-   **CTRL** + **F11**: Toggle music fullscreen
-   **CTRL** + **L**: Minimize window
-   **CTRL** + **M**: Maximize window
-   **PAGE UP**/**KP 9**: Scroll up
-   **PAGE DOWN**/**KP 3**: Scroll down

# Building/Running

On Windows, one can package and run the executable using the `build_windows.py` script (requires `PyInstaller`).

It is adviced to run the following commands after configuring a virtual environment.
Make sure to be in the folder where the main file is located, then:

```
pip install -r requirements.txt
py MusicPlayer.py
```

You can use the `health_check.py` script to check for unused files in the data folder. Use the `--remove` argument to delete them automatically. The script is also run when the music player starts.

User data is not stored in `AppData` or equivalent, rather in the `data/` folder where the main file is in.

# Hidden Settings

There are 2 settings that can only be accessed in the `data/settings.json` file.

-   `"strip_youtube_id"`: Downloaded videos from youtube might have an ID in square brackets at the end of the filename. If this setting is set to `true`, such pattern will be stripped from the display name.
-   `taskbar_height`: When this number is different from 0, when the custom titlebar is enabled, it ensures the taskbar is still visible when the window gets maximized. A common value for it is `30`. Only works if the taskbar is at the bottom. A (default) value of 0 will result in fullscreen maximized.

# Dependencies

-   `pygame-ce` >= 2.5.2 (music, windowing, input, rendering backend)
-   `mili-ui` >= 1.0.0 (UI backend)
-   `moviepy` >= 1.0.3 (video/audio converter/reader)
-   **[optional]** `pypresence` >= 4.3.0 (Discord presence)

# Codebase Notice

The codebase currently follows the following conventions (they are not hard rules):

-   `__init__` and `init(_*)` methods are called once.
-   Every method starting with `ui_` is only responsible for organizing and rendering the UI components. The main `ui` function of each UI component is split in several subfunctions for ease of readibility.
-   Every method starting with `action_` is almost certainly a callback that is _only_ called following a user UI interaction, and never called from anywhere else.
-   Methods starting with `get_`, despite the name, are usually called within the same class to change internal states without returning anything.
-   Every normal method is used internally by the class and usually by external classes to manage the states.
