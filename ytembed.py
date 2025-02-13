import webview
import sys
import os

if "win" in sys.platform or os.name == "nt":
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "damusss.milimp_yt_embed.1.0"
    )

link = sys.argv[1]

window = webview.create_window(
    "MILIMP YT Embed",
    link,
    frameless=True,
    on_top=True,
)


def update():
    last = None
    while True:
        data = sys.stdin.readline().strip()
        if data == "kill":
            os.abort()
        if not data:
            continue
        if data == last:
            continue
        last = data
        if data == "show":
            window.on_top = True
            window.show()
            window.restore()
        elif data == "hide":
            window.on_top = False
            window.hide()
            window.minimize()
        elif data.startswith("newurl:"):
            url = data.removeprefix("newurl:")
            window.load_url(url)
        elif data.startswith("html:"):
            html = data.removeprefix("html:")
            window.load_html(html)
        elif data.startswith("nums"):
            data = data.removeprefix("nums")
            x, y, w, h = data.split(",")
            x, y, w, h = [float(v) for v in (x, y, w, h)]
            if w != window.width or h != window.height:
                window.resize(int(w), int(h))
            if x != window.x or h != window.y:
                window.move(int(x), int(y))


webview.start(
    update,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
