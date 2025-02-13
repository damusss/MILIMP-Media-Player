import io
import re
import shutil
import pygame
import subprocess
import urllib.error
import urllib.request
from ui.common import *
from ui.common.data import YTVideoFormat, YTVideoResult

if typing.TYPE_CHECKING:
    from ui.yt_search import YTSearchUI
    from ui.yt_menus.yt_download import YTDownloadUI

try:
    import youtubesearchpython as fast_yt_search
except ImportError:
    fast_yt_search = None


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


def download_thumbail_async(video: "YTVideoResult", ui: "YTSearchUI", error_img):
    try:
        file_path = f"data/yt_temp/{video.thumbnail}.png"
        image = get_yt_image_async(file_path, video.thumb_url)
        ui.downloading_thumbs.remove(video.thumbnail)
        ui.thubnails[video.thumbnail] = image
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        pygame.error,
        ValueError,
    ) as e:
        print(f"Could not download '{video.thumb_url}': '{e}'")
        ui.downloading_thumbs.remove(video.thumbnail)
        ui.thubnails[video.thumbnail] = error_img


def download_channel_quick_async(video: "YTVideoResult", ui: "YTSearchUI", error_img):
    try:
        file_path = f"data/yt_temp/channel_{video.channel_id}.png"
        image = get_yt_image_async(file_path, video.quick_pfp_url)
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = image
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        pygame.error,
        ValueError,
    ) as e:
        print(f"Could not download profile picture of '{video.channel_url}': '{e}'")
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = error_img


def save_thumbnail_async(video: "YTVideoResult"):
    try:
        filename = f"data/yt_downloads/thumbnail_{video.title_fn}.png"
        get_yt_image_async(filename, video.hd_thumb_url)
        print(f"Downloaded thumbnail to '{filename}'")
    except (urllib.error.URLError, urllib.error.HTTPError, pygame.error, ValueError):
        ...


def download_channel_async(video: "YTVideoResult", ui: "YTSearchUI", error_img):
    if video.quick_pfp_url is not None:
        download_channel_quick_async(video, ui, error_img)
        return
    try:
        file_path = f"data/yt_temp/channel_{video.channel_id}.jpg"
        if os.path.exists(file_path):
            image = pygame.image.load(file_path)
        else:
            command = f'yt-dlp -o "data/yt_temp/channel_{video.channel_id}" --write-thumbnail --playlist-items 0 {video.channel_url}'
            print(f"EXECUTING FOREIGN COMMAND <{command}>")
            subprocess.run(command)
            image = pygame.image.load(file_path).convert_alpha()
        image = mili.fit_image(
            ((0, 0), image.size), image, ready_border_radius=image.width / 2
        )
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = image
    except (pygame.error,) as e:
        print(f"Could not download profile picture of '{video.channel_url}': '{e}'")
        ui.downloading_channels.remove(video.channel_id)
        ui.channel_covers[video.channel_id] = error_img


def search_videos_fast_async(ui: "YTSearchUI", query):
    try:
        result = fast_yt_search.VideosSearch(query, limit=ui.fetch_amount).result()[
            "result"
        ]
    except Exception as e:
        ui.search_error = f"unexpected error: '{e}'"
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
    if len(ui.video_results) < ui.fetch_amount:
        ui.fetch_amount = len(ui.video_results)


def search_videos_ytdlp_async(ui: "YTSearchUI", query):
    format_str = "%(title)s<TITLESEP>{'id': '%(id)s', 'url': '%(url)s', 'views': '%(view_count)s', 'channel': '%(channel)s', 'channel_id': '%(channel_id)s', 'channel_url': '%(channel_url)s', 'duration': '%(duration)s', 'live_status': '%(live_status)s', 'globality': '%(availability)s'}"
    command = f'yt-dlp "ytsearch{ui.fetch_amount}:{query}" --flat-playlist --print "{format_str}" --extractor-args "youtube:music"'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        output = subprocess.check_output(command).decode(errors="replace")
    except subprocess.CalledProcessError as e:
        ui.search_error = f"subprocess error: '{e.output}'"
        ui.searching = False
        ui.searching_more = False
        return
    except Exception as e:
        ui.search_error = f"unexpected error: '{e}'"
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
            print(f"SEARCH ERROR: {e}")
            continue
    ui.video_results = res
    ui.searching = False
    ui.searched = True
    ui.searching_more = False


def check_ffmpeg():
    dep = shutil.which("ffmpeg")
    if dep is None:
        pygame.display.message_box(
            "Missing Dependency 'ffmpeg'",
            "Merging audio and video tracks relies on the ffmpeg binary dependency that must be downloaded and possibly added to PATH. You can download the latest EXE from 'https://www.ffmpeg.org/download.html'.",
            "error",
            None,
            ("Understood",),
        )
        return None
    try:
        command = "ffmpeg -version"
        print(f"EXECUTING FOREIGN COMMAND <{command}>")
        output = subprocess.check_output(command, text=True)
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
    filename = f"data/yt_downloads/{video.channel_fn}_{video.title_fn}"
    delete_yt_if_exists(filename + ".webm")
    command = f'yt-dlp -o "{filename}" {video.url}'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        subprocess.run(command)
    except subprocess.CalledProcessError:
        ...
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
    filename = f"data/yt_downloads/{vidname}_{fmt.id}{extra}.{fmt.ext}"
    delete_yt_if_exists(filename)
    command = f'yt-dlp -o "{filename}" -f {fmt.id} {video.url}'
    print(f"EXECUTING FOREIGN COMMAND <{command}>")
    try:
        subprocess.run(command)
    except subprocess.CalledProcessError:
        ...
    if not internal:
        ui.downloading -= 1


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
    prefix = "data/yt_downloads/"
    almostifle = f"{prefix}{video.channel_fn}_{video.title_fn}_{vid.id}-{aud.id}."
    filename = f"{almostifle}mkv"
    invid = f"{prefix}{video.id}_{vid.id}.{vid.ext}"
    inaud = f"{prefix}{video.id}_{aud.id}.{aud.ext}"
    delete_yt_if_exists(filename)
    command = f'ffmpeg -i "{invid}" -i "{inaud}" -c:v copy -c:a copy "{filename}"'
    try:
        print(f"EXECUTING FOREIGN COMMAND <{command}>")
        subprocess.run(command, check=True)
        try:
            newin = filename
            filename = f"{almostifle}mp4"
            delete_yt_if_exists(filename)
            command = f'ffmpeg -i "{newin}" -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k "{filename}"'
            print(f"EXECUTING FOREIGN COMMAND <{command}>")
            subprocess.run(command)
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
            command,
        ).decode(errors="replace")
    except subprocess.CalledProcessError as e:
        dui.error = f"subprocess error: '{e}'"
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
