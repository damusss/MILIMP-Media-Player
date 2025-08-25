import io
import re
import json
import pygame
import signal
import shutil
import datetime
import webbrowser
import subprocess
import urllib.error
import urllib.request
from ui.common import *
from ui.common.data import YTVideoFormat, YTVideoResult, Playlist

if typing.TYPE_CHECKING:
    from ui.yt_search import YTSearchUI
    from ui.yt_menus.yt_download import YTDownloadUI
    from ui.yt_menus.yt_playlist import YTPlaylistUI
    from ui.playlist_viewer import PlaylistViewerUI

try:
    import youtubesearchpython as fast_yt_search
except ImportError:
    fast_yt_search = None


class YTPlaylistSyncAsync:
    def __init__(self, ui: "PlaylistViewerUI", playlist: "Playlist"):
        self.ui = ui
        self.playlist = playlist
        self.alive = False
        self.thread = None
        self.videos_to_download = []
        self.downloading = False
        self.force_quit = False
        self.process = None
        self.video_covers = {}
        self.downloading_video = None

    def sync_async(self):
        folder = f"{DATA_PATH}/yt_playlists/{self.playlist.name}"
        if not os.path.exists(folder):
            os.mkdir(folder)
        try:
            command = (
                f'yt-dlp --flat-playlist --dump-single-json "{self.playlist.yt_link}"'
            )
            print(f"EXECUTING FOREIGN COMMAND <{command}>")
            output = subprocess.check_output(
                command, creationflags=SUBPROCESS_FLAGS
            ).decode(errors="replace")
            obj = json.loads(output)
            metadata = save_playlist_metadata(
                obj, f"{DATA_PATH}/yt_playlists/{self.playlist.name}/{self.playlist.name}.json"
            )
            name = obj.get("title", self.playlist.yt_name)
            self.playlist.yt_name = name
            self.playlist.yt_metadata = metadata
            self.videos_to_download = list(metadata["videos"].values())
            if metadata["thumbnail"] is not None:
                cover = get_yt_cover_async(metadata["thumbnail"])
                if cover is not None:
                    self.playlist.cover = cover
        except Exception as e:
            notify_error(
                self.ui.app,
                f"Could not sync playlist '{self.playlist.yt_link}' because of exception '{e}'",
                hidden=True,
            )
            return
        while self.alive:
            if not self.downloading:
                if len(self.videos_to_download) <= 0:
                    self.alive = False
                    self.ui.app.notify(
                        NOTIF.CONFIRM,
                        f"YouTube Playlist '{self.playlist.yt_name}' finished syncing.",
                    )
                    return
                cur_ids = [music.yt_id for music in self.playlist.musiclist]
                for new_video in list(self.videos_to_download):
                    if new_video["id"] in cur_ids:
                        self.videos_to_download.remove(new_video)
                        print(f"Was already downloaded: {new_video['title']}")
                        continue
                    self.download_video(new_video)
                    break
            elif self.process is not None:
                returncode = self.process.poll()
                if returncode is not None:
                    self.videos_to_download.remove(self.downloading_video)
                    if returncode != 0:
                        notify_error(
                            self.ui.app,
                            f"Could not download {self.downloading_video['title']}",
                        )
                    self.downloading = False
                    self.downloading_video = None
                    self.ui.yt_need_refresh = True
        if self.force_quit:
            if sys.platform == "win32":
                subprocess.run(f"taskkill /F /T /PID {self.process.pid}", shell=True)
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            return
        self.ui.app.notify(
            ICONS.close,
            f"Syncing interrupted for YouTube Playlist '{self.playlist.yt_name}'",
        )

    def download_video(self, video):
        self.downloading = True
        self.downloading_video = video
        if video["thumbnail"] is not None:
            cover = get_yt_cover_async(video["thumbnail"])
            if cover is not None:
                self.video_covers[video["id"]] = cover
        command = f'yt-dlp -P "{DATA_PATH}/yt_playlists/{self.playlist.name}" {video["url"]}'
        print(f"Downloading {video['title']}")
        print(f"EXECUTING FOREIGN COMMAND <{command}>")
        self.process = subprocess.Popen(command, creationflags=SUBPROCESS_FLAGS)


class YTPlaylistSyncAsyncOLD:
    def __init__(self, ui, playlist: "Playlist"):
        self.ui = ui
        self.playlist = playlist
        self.alive = False
        self.thread = None
        self.last_line = ""

    def sync_async(self):
        self.sync_title_async()
        folder = f"{DATA_PATH}/yt_playlists/{self.playlist.name}"
        if not os.path.exists(folder):
            os.mkdir(folder)
        command = f'yt-dlp -P "{folder}" "{self.playlist.yt_link}"'
        print(f"EXECUTING FOREIGN COMMAND <{command}>")
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
        while self.alive:
            if self.process.poll() is not None:
                self.alive = False
            self.last_line = self.process.stdout.readline().strip()
        if sys.platform == "win32":
            subprocess.run(f"taskkill /F /T /PID {self.process.pid}", shell=True)
        else:
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        self.process.wait()
        self.thread = None
        self.last_line = ""

    def sync_title_async(self):
        try:
            command = (
                f'yt-dlp --flat-playlist --dump-single-json "{self.playlist.yt_link}"'
            )
            print(f"EXECUTING FOREIGN COMMAND <{command}>")
            output = subprocess.check_output(
                command, creationflags=SUBPROCESS_FLAGS
            ).decode(errors="replace")
            obj = json.loads(output)
            with open("temp.json", "w") as file:
                json.dump(obj, file)
            name = obj.get("title", self.playlist.yt_name)
            if name != self.playlist.yt_name:
                self.playlist.yt_name = name
        except Exception as e:
            notify_error(
                self.ui.app,
                f"Could not sync playlist name of '{self.playlist.yt_link}' because of exception '{e}'",
                hidden=True,
            )


def save_playlist_metadata(raw: dict, path):
    meta = {
        "id": raw.get("id", None),
        "name": raw.get("title", None),
        "availability": raw.get("availability", "unavailable"),
        "description": raw.get("description", ""),
        "sync_date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "modified_date": raw.get("modified_date", None),
        "views": raw.get("view_count", None),
        "count": raw.get("playlist_count", None),
        "channel_name": raw.get("channel", None),
        "channel_id": raw.get("channel_id", None),
        "channel_url": raw.get("channel_url", None),
        "thumbnail": None,
        "videos": {},
    }
    biggest_thumbnail = None
    biggest_size = 0
    for thumbnail in raw.get("thumbnails", []):
        size = thumbnail.get("width", 0) * thumbnail.get("height", 0)
        if size > biggest_size:
            biggest_size = size
            biggest_thumbnail = thumbnail.get("url", None)
    meta["thumbnail"] = biggest_thumbnail
    for entry in raw.get("entries", []):
        entry: dict
        id_ = entry.get("id", None)
        url = entry.get("url", None)
        if id_ is None or url is None:
            continue
        video = {
            "id": id_,
            "url": url,
            "title": entry.get("title", None),
            "duration": entry.get("duration", None),
            "channel_id": entry.get("channel_id", None),
            "channel_name": entry.get("channel", None),
            "channel_url": entry.get("channel_url", None),
            "views": entry.get("view_count", None),
            "thumbnail": None,
        }
        biggest_thumbnail = None
        biggest_size = 0
        for thumbnail in entry.get("thumbnails", []):
            size = thumbnail.get("width", 0) * thumbnail.get("height", 0)
            if size > biggest_size:
                biggest_size = size
                biggest_thumbnail = thumbnail.get("url", None)
        video["thumbnail"] = biggest_thumbnail
        meta["videos"][id_] = video
    with open(path, "w") as mfile:
        json.dump(meta, mfile)
    return meta


def get_playlist_name_async(playlist_ui: "YTPlaylistUI"):
    command = f'yt-dlp --flat-playlist --dump-single-json "{playlist_ui.playlist_url}"'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        output = subprocess.check_output(
            command, creationflags=SUBPROCESS_FLAGS
        ).decode(errors="replace")
        obj = json.loads(output)
        playlist_ui.error = None
        playlist_ui.playlist_name = obj.get(
            "title", playlist_ui.playlist_url.split("playlist?list=")[-1]
        )
        playlist_ui.playlist_meta = obj
        playlist_ui.yt_searching = False
    except subprocess.CalledProcessError as e:
        playlist_ui.error = notify_error(
            playlist_ui.app, f"subprocess error: '{e.output}'", hidden=True
        )
        playlist_ui.yt_searching = False
        return
    except Exception as e:
        playlist_ui.error = notify_error(
            playlist_ui.app, f"unexpected error: '{e}'", hidden=True
        )
        playlist_ui.yt_searching = False
        return


def get_yt_image_async(file_path, url):
    if os.path.exists(file_path):
        image = pygame.image.load(file_path)
    else:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                raise ValueError
            image_data = response.read()
        image_file = io.BytesIO(image_data)
        image = pygame.image.load(image_file).convert_alpha()
        pygame.image.save(image, file_path)
    return image


def get_yt_cover_async(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                return
            image_data = response.read()
        image_file = io.BytesIO(image_data)
        image = pygame.image.load(image_file).convert_alpha()
    except Exception:
        return
    return image


def download_thumbail_async(video: "YTVideoResult", ui: "YTSearchUI", error_img):
    try:
        file_path = f"{DATA_PATH}/yt_temp/{video.thumbnail}.png"
        image = get_yt_image_async(file_path, video.thumb_url)
        ui.downloading_thumbs.remove(video.thumbnail)
        ui.thubnails[video.thumbnail] = image
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        pygame.error,
        ValueError,
    ) as e:
        notify_error(
            ui.app, f"Could not download '{video.thumb_url}': '{e}'", hidden=True
        )
        ui.downloading_thumbs.remove(video.thumbnail)
        ui.thubnails[video.thumbnail] = error_img


def download_channel_quick_async(video: "YTVideoResult", ui: "YTSearchUI", error_img):
    try:
        file_path = f"{DATA_PATH}/yt_temp/channel_{video.channel_id}.png"
        image = get_yt_image_async(file_path, video.quick_pfp_url)
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = image
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        pygame.error,
        ValueError,
    ) as e:
        notify_error(
            ui.app,
            f"Could not download profile picture of '{video.channel_url}': '{e}'",
            hidden=True,
        )

        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = error_img


def save_thumbnail_async(video: "YTVideoResult", ui: "YTSearchUI"):
    try:
        filename = f"{DATA_PATH}/yt_downloads/thumbnail_{video.title_fn}.png"
        get_yt_image_async(filename, video.hd_thumb_url)
        ui.app.notify(NOTIF.DOWNLOAD, f"Downloaded thumbnail to '{filename}'")
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        pygame.error,
        ValueError,
    ) as e:
        notify_error(f"Could not save thumbnail {video.hd_thumb_url}: {e}")


def download_channel_async(video: "YTVideoResult", ui: "YTSearchUI", error_img):
    if video.quick_pfp_url is not None:
        download_channel_quick_async(video, ui, error_img)
        return
    if video.channel_id == "NA":
        notify_error(
            ui.app,
            f"Could not download profile picture of '{video.channel_url}' because the channel ID is unknown",
            hidden=True,
        )
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = error_img
        return
    try:
        file_path = f"{DATA_PATH}/yt_temp/channel_{video.channel_id}.jpg"
        if os.path.exists(file_path):
            image = pygame.image.load(file_path)
        else:
            command = f'yt-dlp -o "{DATA_PATH}/yt_temp/channel_{video.channel_id}" --write-thumbnail --playlist-items 0 {video.channel_url}'
            print(f"EXECUTING FOREIGN COMMAND <{command}>")
            subprocess.run(command, creationflags=SUBPROCESS_FLAGS)
            image = pygame.image.load(file_path).convert_alpha()
        image = mili.fit_image(
            ((0, 0), image.size), image, filters=[(mili.round_image)]
        )
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = image
    except (pygame.error,) as e:
        notify_error(
            ui.app,
            f"Could not download profile picture of '{video.channel_url}': '{e}'",
            hidden=True,
        )
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = error_img


def search_videos_fast_async(ui: "YTSearchUI", query):
    try:
        result = fast_yt_search.VideosSearch(query, limit=ui.fetch_amount).result()[
            "result"
        ]
    except Exception as e:
        ui.search_error = notify_error(ui.app, f"unexpected error: '{e}'")
        ui.searching = False
        ui.searching_more = False
    if ui.search_canceled:
        ui.searching = False
        ui.searching_more = False
        return
    res = []
    for entry in result:
        if entry["type"] != "video":
            continue
        vid = entry["id"]
        url = entry["link"]
        title = entry["title"]
        duration = entry["duration"]
        views = "".join(
            [char for char in entry["viewCount"]["text"] if char.isdecimal()]
        )

        channel = entry["channel"]["name"]
        channel_id = entry["channel"]["id"]
        channel_url = entry["channel"]["link"]
        try:
            channel_pfp = entry["channel"]["thumbnails"][0]["url"]
        except Exception as e:
            print(e)
            channel_pfp = None
        result = YTVideoResult(
            title,
            vid,
            url,
            views,
            channel,
            channel_id,
            channel_url,
            duration,
            "NA",
            "NA",
            THUMBNAILS[ui.thumb_method],
            ui.thumb_method,
            None,
            None,
            channel_pfp,
        )
        res.append(result)
    ui.video_results = res
    ui.searching = False
    ui.searched = True
    ui.searching_more = False
    ui.last_search = query
    if len(ui.video_results) < ui.fetch_amount:
        ui.fetch_amount = len(ui.video_results)


def search_videos_ytdlp_async(ui: "YTSearchUI", query):
    # https://music.youtube.com/playlist?list=PLPVoTF-tbIz7gL9yoImXLg_-9-_Hx2zdM
    format_str = "%(title)s<TITLESEP>{'id': '%(id)s', 'url': '%(url)s', 'views': '%(view_count)s', 'channel': '%(channel)s', 'channel_id': '%(channel_id)s', 'channel_url': '%(channel_url)s', 'duration': '%(duration)s', 'live_status': '%(live_status)s', 'globality': '%(availability)s'}"
    query_str = f'"ytsearch{ui.fetch_amount}:{query}"'
    extra_url = ""
    if "playlist?list=" in query:
        query_str = ""
        extra_url = query
    command = f'yt-dlp {query_str} --flat-playlist --print "{format_str}" --extractor-args "youtube:music" {extra_url}'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        output = subprocess.check_output(
            command, creationflags=SUBPROCESS_FLAGS
        ).decode(errors="replace")
    except subprocess.CalledProcessError as e:
        ui.search_error = notify_error(
            ui.app, f"subprocess error: '{e.output}'", hidden=True
        )
        ui.searching = False
        ui.searching_more = False
        return
    except Exception as e:
        ui.search_error = notify_error(ui.app, f"unexpected error: '{e}'", hidden=True)
        ui.searching = False
        ui.searching_more = False
        return
    if ui.search_canceled:
        ui.searching = False
        ui.searching_more = False
        return
    res = []
    dicts = output.split("\n")
    for dstr in dicts:
        try:
            title, odata = dstr.split("<TITLESEP>")
            data = eval(odata)
            video = YTVideoResult(
                title,
                data["id"],
                data["url"],
                data["views"],
                data["channel"],
                data["channel_id"],
                data["channel_url"],
                data["duration"],
                data["live_status"],
                data["globality"],
                THUMBNAILS[ui.thumb_method],
                ui.thumb_method,
            )
            if video.live_status not in ["not_live", "NA"]:
                continue
            if video.globality not in ["public", "NA"]:
                continue
            print(f"Search Result: {title} {data}")
            res.append(video)
        except Exception as e:
            notify_error(ui.app, f"SEARCH ERROR: {e}", hidden=True)
            continue
    ui.video_results = res
    ui.searching = False
    ui.searched = True
    ui.searching_more = False
    ui.last_search = query


def check_ffmpeg():
    dep = shutil.which("ffmpeg")
    if dep is None:
        btn = pygame.display.message_box(
            "Missing Dependency 'ffmpeg'",
            "Merging audio and video tracks relies on the ffmpeg binary dependency that must be downloaded and possibly added to PATH. You can download the latest EXE from 'https://www.ffmpeg.org/download.html'.",
            "error",
            None,
            ("Understood", "Open Link"),
        )
        if btn == 1:
            webbrowser.open("https://www.ffmpeg.org/download.html")
        return None
    try:
        command = "ffmpeg -version"
        print(f"EXECUTING FOREIGN COMMAND <{command}>")
        output = subprocess.check_output(
            command, text=True, creationflags=SUBPROCESS_FLAGS
        )
        res = None
        for letter in output:
            if letter.isdecimal():
                return int(letter)
        return res
    except subprocess.CalledProcessError:
        return None
    return True


def download_yt_default_async(
    ui: "YTSearchUI", video: "YTVideoResult", fmt: "YTVideoFormat"
):
    filename = f"{DATA_PATH}/yt_downloads/{video.channel_fn}_{video.title_fn}"
    delete_yt_if_exists(filename + ".webm")
    command = f'yt-dlp -o "{filename}" {video.url}'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        subprocess.run(command, creationflags=SUBPROCESS_FLAGS)
        ui.app.notify(NOTIF.DOWNLOAD, f"Video downloaded succesfully at '{filename}'")
    except subprocess.CalledProcessError as e:
        notify_error(ui.app, str(e))
    ui.downloading -= 1


def download_yt_async(
    ui: "YTSearchUI", video: "YTVideoResult", fmt: "YTVideoFormat", internal=False
):
    if internal:
        vidname = f"{video.id}"
    else:
        vidname = f"{video.channel_fn}_{video.title_fn}"
    extra = ""
    if fmt.type == "audio" and not internal and fmt.ext == "webm":
        extra = "novideo"
    filename = f"{DATA_PATH}/yt_downloads/{vidname}_{fmt.id}{extra}.{fmt.ext}"
    delete_yt_if_exists(filename)
    command = f'yt-dlp -o "{filename}" -f {fmt.id} {video.url}'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        subprocess.run(command, creationflags=SUBPROCESS_FLAGS)
        ui.app.notify(NOTIF.DOWNLOAD, f"Video downloaded succesfully at '{filename}'")
    except subprocess.CalledProcessError as e:
        notify_error(ui.app, str(e))
    if not internal:
        ui.downloading -= 1


def download_playlist_async(ui: "YTPlaylistUI"):
    folder = f"{DATA_PATH}/yt_downloads/{ui.playlist_name}"
    if not os.path.exists(folder):
        os.mkdir(folder)
    command = f'yt-dlp -P "{folder}" "{ui.playlist_url}"'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        subprocess.run(command, creationflags=SUBPROCESS_FLAGS)
        ui.app.notify(NOTIF.DOWNLOAD, f"Playlist downloaded succesfully at '{folder}'")
    except subprocess.CalledProcessError as e:
        notify_error(ui.app, str(e))
    ui.parent.downloading_playlist = None


def merge_yt_async(
    ui: "YTSearchUI",
    video: "YTVideoResult",
    fmt1: "YTVideoFormat",
    fmt2: "YTVideoFormat",
):
    aud, vid = fmt1, fmt2
    if aud.type == "video":
        aud, vid = fmt2, fmt1
    download_yt_async(ui, video, aud, True)
    download_yt_async(ui, video, vid, True)
    prefix = f"{DATA_PATH}/yt_downloads/"
    almostifle = f"{prefix}{video.channel_fn}_{video.title_fn}_{vid.id}-{aud.id}."
    filename = f"{almostifle}mkv"
    invid = f"{prefix}{video.id}_{vid.id}.{vid.ext}"
    inaud = f"{prefix}{video.id}_{aud.id}.{aud.ext}"
    delete_yt_if_exists(filename)
    command = f'ffmpeg -i "{invid}" -i "{inaud}" -c:v copy -c:a copy "{filename}"'
    try:
        print(f"EXECUTING FOREIGN COMMAND <{command}>")
        subprocess.run(command, check=True, creationflags=SUBPROCESS_FLAGS)
        try:
            newin = filename
            filename = f"{almostifle}mp4"
            delete_yt_if_exists(filename)
            command = f'ffmpeg -i "{newin}" -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k "{filename}"'
            print(f"EXECUTING FOREIGN COMMAND <{command}>")
            subprocess.run(command, creationflags=SUBPROCESS_FLAGS)
            ui.app.notify(
                NOTIF.DOWNLOAD,
                f"Video downloaded and merged succesfully at '{filename}'",
            )
        except subprocess.CalledProcessError:
            delete_yt_if_exists(filename)
    except subprocess.CalledProcessError:
        delete_yt_if_exists(filename)
    delete_yt_if_exists(invid)
    delete_yt_if_exists(inaud)
    ui.downloading -= 1


def get_yt_formats_async(ui: "YTSearchUI", dui: "YTDownloadUI", video: "YTVideoResult"):
    command = f"yt-dlp --list-formats {video.url}"
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        output = subprocess.check_output(
            command, creationflags=SUBPROCESS_FLAGS
        ).decode(errors="replace")
    except subprocess.CalledProcessError as e:
        dui.error = notify_error(ui.app, f"subprocess error: '{e}'", hidden=True)
        dui.formats = []
        dui.getting_formats = False
        return
    if ui.modal_state == "none":
        dui.getting_formats = False
        return
    formats = [YTVideoFormat(-1, "full", "webm", None, None, None, None, True)]
    for line in output.split("\n"):
        if not line.strip():
            continue
        if (
            line.startswith("[youtube]")
            or line.startswith("[info]")
            or line.startswith("ID")
            or line.startswith("-")
        ):
            continue
        fmt = parse_format_async(line)
        if fmt is not None:
            formats.append(fmt)
    formats = sorted(
        formats, key=lambda f: ({"full": 0, "audio": 1, "video": 2}[f.type])
    )
    dui.getting_formats = False
    dui.formats = formats
    video.formats = formats


def parse_format_async(string):
    string = re.sub(r"\s+", " ", string.strip())
    if "images" in string:
        return None
    if "unknown" in string:
        return None
    print(f"[FORMAT] {string}")
    fmttype = "full"
    if "audio only" in string:
        fmttype = "audio"
        string = string.replace("audio only", "")
    if "video only" in string:
        fmttype = "video"
        string = string.replace("video only", "")
    ssplit = string.split(" ")
    id_ = ssplit[0]
    ext = ssplit[1]
    res = None
    if fmttype != "audio":
        res = ssplit[2]
    fps = None
    filesize = None
    if ssplit[3].isdecimal() and fmttype != "audio":
        fps = ssplit[3]
    bsplit = string.split("|")
    middle_data = ""
    if len(bsplit) >= 2:
        fsdata = bsplit[1].replace("~", "").strip()
        onenum = False
        for letter in fsdata:
            if letter.isdecimal():
                onenum = True
        if " " in fsdata and onenum:
            filesize = fsdata.split(" ")[0]
            middle_data = fsdata.replace(filesize, "").strip() + "; "
    middle_data += bsplit[-1].strip()
    extra_data = f"FID:{id_}; {middle_data}"
    return YTVideoFormat(id_, fmttype, ext, res, fps, filesize, extra_data)


def delete_yt_if_exists(path):
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            ...
