from ui.common import *
import tkinter.filedialog as filedialog


class MILIMPAskDataPath(mili.GenericApp):
    def __init__(self):
        pygame.init()
        self.desktop = pygame.Vector2(pygame.display.get_desktop_sizes()[0])
        super().__init__(
            pygame.Window(
                "Choose MILIMP Data Path",
                (self.desktop.x / 2.5, self.desktop.y / 2),
                borderless=True,
            ),
            start_style={"pad": 0},
        )
        ICONS.load()
        self.mili.default_styles(
            text={
                "sysfont": False,
                "name": "appdata/ytfont.ttf",
                "growx": True,
                "growy": True,
                "cache": "auto",
            },
            rect={"border_radius": 0},
        )
        self.window.set_icon(ICONS.playlist_cover)
        self.path = pygame.system.get_pref_path(PREF_ORG, PREF_APP)
        self.writable = True

    def ui(self):
        self.mili.rect({"color": (BORDER_CV / 5,) * 3, "border_radius": 0})
        self.mili.rect(
            {
                "color": (BORDER_CV,) * 3,
                "outline": 1,
                "draw_above": True,
                "border_radius": 0,
            }
        )
        size = 30
        self.ui_top_bar(size)
        with self.mili.begin(None, {"resizey": True, "fillx": True, "pad": 0}) as cont:
            self.mili.text_element(
                "Choose the writable folder where MILIMP will save settings, covers, conversions, downloads and playlists.\nThe preferred system path is selected by default.\nYou won't see this message again.\nAfter you confirm, restart the application.",
                {
                    "size": 20,
                    "align": "left",
                    "color": (220,) * 3,
                    "font_align": "left",
                    "wraplen": self.window.size[0],
                    "slow_grow": True,
                },
                None,
                {"fillx": True},
            )
            perc = 85
            with self.mili.begin(
                None,
                {
                    "resizey": True,
                    "fillx": f"{perc}",
                    "default_align": "center",
                    "align": "center",
                },
            ):
                self.mili.text_element(
                    "Data Path:",
                    {
                        "size": 21,
                    },
                    None,
                )
                with self.mili.element(None, {"fillx": True}):
                    self.mili.rect({"color": (BORDER_CV / 3,) * 3})
                    self.mili.rect(
                        {
                            "color": (BORDER_CV,) * 3 if self.writable else "red",
                            "outline": 1,
                            "draw_above": True,
                        }
                    )
                    self.mili.text(
                        self.path,
                        {
                            "size": 20,
                            "align": "left",
                            "font_align": "left",
                            "wraplen": mili.percentage(perc - 5, self.window.size[0]),
                            "slow_grow": True,
                        },
                    )
                with self.mili.begin(
                    None, {"resizex": True, "resizey": True, "axis": "x"}
                ):
                    self.ui_button(ICONS.upload, self.action_path)
                    self.ui_button(ICONS.refresh, self.action_default)
                    self.ui_button(ICONS.confirm, self.action_confirm)
        height = size + cont.data.rect.h
        if self.window.size[1] != height:
            self.window.size = (self.window.size[0], height)
            self.window.position = (
                self.window.position[0],
                self.desktop.y / 2 - height / 2,
            )
        mili.InteractionCursor.apply()

    def ui_button(self, icon, action):
        size = 60
        with self.mili.element((0, 0, size, size)) as btn:
            self.mili.image(icon, {"alpha": cond(self, btn, 200, 255, 180)})
            mili.InteractionCursor.update(btn)
            if btn.left_clicked:
                action()

    def check_writable(self):
        try:
            with open(os.path.join(self.path, "writable.test"), "w") as file:
                file.write("Testing if the folder is writable")
            os.remove(os.path.join(self.path, "writable.test"))
            self.writable = True
        except OSError:
            self.writable = False

    def action_path(self):
        path = filedialog.askdirectory()
        if not path:
            return
        self.path = path
        self.check_writable()

    def action_default(self):
        self.path = pygame.system.get_pref_path(PREF_ORG, PREF_APP)
        self.check_writable()

    def action_confirm(self):
        if not self.writable:
            pygame.display.message_box(
                "Path not writable",
                "The app needs a writable folder to store data. The selected folder isn't writable. Choose a different one.",
                "error",
                buttons=["Understood"],
            )
            return
        with open("data_path", "w") as file:
            file.write(self.path)
        self.quit()

    def ui_top_bar(self, size):
        with self.mili.begin(
            (0, 0, 0, size),
            {
                "fillx": True,
                "pad": 0,
                "spacing": 0,
                "axis": "x",
                "default_align": "center",
            },
        ):
            self.mili.rect(
                {
                    "border_radius": 0,
                    "color": (BORDER_CV / 3,) * 3,
                }
            )
            self.mili.text_element(
                self.window.title,
                {
                    "size": 18,
                    "color": (200,) * 3,
                    "align": "left",
                    "font_align": "left",
                },
                None,
                {"fillx": True},
            )
            with self.mili.element((0, 0, size, size)) as el:
                color = (BORDER_CV / 3,) * 3
                if el.hovered:
                    color = (200, 0, 0)
                if el.left_pressed:
                    color = (80, 0, 0)
                self.mili.rect({"color": color})
                self.mili.image(ICONS.close)
                if el.left_clicked:
                    self.quit()
                mili.InteractionCursor.update(el)

    def can_interact(self):
        return True
