import mili
import pygame
import functools
from ui.common import Keybinds


class UIEntryline:
    def __init__(self, placeholder="Enter text...", target_files=True):
        self.text = ""
        self.cursor = 0
        self.placeholder = placeholder
        self.cursor_on = True
        self.cursor_time = pygame.time.get_ticks()
        self.target_files = target_files

    def set_text(self, text):
        self.text = text
        self.cursor = len(text)

    def add(self, char):
        left, right = self.text[: self.cursor], self.text[self.cursor :]
        self.text = left + char + right
        self.cursor += len(char)

    def remove(self):
        if self.cursor > 0:
            left, right = self.text[: self.cursor], self.text[self.cursor :]
            self.text = left[:-1] + right
            self.cursor -= 1

    def canc(self):
        if self.cursor <= len(self.text):
            left, right = self.text[: self.cursor], self.text[self.cursor :]
            self.text = left[: self.cursor] + right[1:]

    def move(self, dir):
        self.cursor += dir
        if self.cursor < 0:
            self.cursor = 0
        if self.cursor > len(self.text):
            self.cursor = len(self.text)

    def event(self, event):
        if event.type == pygame.TEXTINPUT:
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                return
            if self.target_files and event.text in [
                "<",
                ">",
                ":",
                '"',
                "/",
                "\\",
                "|",
                "?",
                "*",
                ".",
            ]:
                return
            self.set_cursor_on()
            self.add(event.text)
        if event.type == pygame.KEYDOWN:
            if Keybinds.check("erase_input", event):
                self.text = ""
                self.cursor = 0
            else:
                self.set_cursor_on()
                if event.key == pygame.K_LEFT:
                    self.move(-1)
                elif event.key == pygame.K_RIGHT:
                    self.move(1)
                elif event.key == pygame.K_BACKSPACE:
                    self.remove()
                elif event.key == pygame.K_DELETE:
                    self.canc()
                if event.mod & pygame.KMOD_CTRL:
                    if event.key == pygame.K_c:
                        pygame.scrap.put_text(self.text.strip())
                    elif event.key == pygame.K_v:
                        txt = pygame.scrap.get_text().replace("\n", "")
                        if self.target_files:
                            txt = "".join(
                                char
                                for char in txt
                                if txt
                                not in [
                                    "<",
                                    ">",
                                    ":",
                                    '"',
                                    "/",
                                    "\\",
                                    "|",
                                    "?",
                                    "*",
                                    ".",
                                ]
                            )
                        self.set_cursor_on()
                        self.add(txt)

    def update(self, app):
        app.input_stolen = True
        if pygame.time.get_ticks() - self.cursor_time >= 350:
            self.cursor_on = not self.cursor_on
            self.cursor_time = pygame.time.get_ticks()

    def set_cursor_on(self):
        self.cursor_on = True
        self.cursor_time = pygame.time.get_ticks()

    def draw_cursor(self, csize, offset, canva, element_data, rect):
        if not self.cursor_on:
            return
        curs = rect.h / 1.5
        xpos = rect.x + csize - offset + 5
        if offset != 0:
            xpos += 5
        pygame.draw.line(
            canva,
            (255,) * 3,
            (xpos, rect.y + rect.h / 2 - curs / 2),
            (xpos, rect.y + rect.h / 2 + curs / 2),
        )

    def ui(self, mili_: mili.MILI, rect, style, mult, bgcol=20, outlinecol=40):
        with mili_.begin(
            rect,
            style | {"axis": "x"},
        ) as data:
            rect = data.data.rect
            mili_.rect({"color": (bgcol,) * 3, "border_radius": 0})
            mili_.rect(
                {
                    "color": (outlinecol,) * 3,
                    "outline": 1,
                    "border_radius": 0,
                    "draw_above": True,
                }
            )

            txtocursor = self.text[: self.cursor]
            size = mili_.text_size(txtocursor, {"size": mult(20)})
            offsetx = size.x - (rect.w - 15)
            if offsetx < 0:
                offsetx = 0

            if mili_.element(
                (0, 0, 0, 0),
                {
                    "align": "center",
                    "offset": (-offsetx, 0),
                    "post_draw_func": functools.partial(
                        self.draw_cursor, size.x, offsetx
                    ),
                    "blocking": None,
                },
            ):
                text = self.text
                if len(self.text) == 1:
                    text = f"{text} "
                mili_.text(
                    text if self.text else self.placeholder,
                    {"color": (255 if self.text else 120,) * 3, "size": mult(20)},
                )
