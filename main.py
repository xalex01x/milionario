import tkinter as tk
import random
import time
from pathlib import Path

from domande import DOMANDE
from config import LETTERE, PREMI, IMMAGINI

try:
    import cv2
    from PIL import Image, ImageTk
except ImportError as exc:
    raise SystemExit(
        "Installa le librerie necessarie con:\n"
        "pip install opencv-python pillow"
    ) from exc


# =========================================================
# CONFIGURAZIONE
# =========================================================

CARTELLA_ASSETS = Path(__file__).resolve().parent / "assets"
FONT = "ICT Conduit"

# =========================================================
# GIOCO
# =========================================================

class Milionario:

    BG = "#06152b"
    BLUE = "#073b80"
    BLUE_DARK = "#092b59"
    GOLD = "#ffb21c"
    WHITE = "#ffffff"
    GREEN = "#28a745"
    YELLOW = "#ffe500"
    ORANGE = "#ff8c00"

    def __init__(self, root):
        self.root = root
        self.root.title("Chi vuol essere milionario")
        self.root.configure(bg=self.BG)
        self.root.attributes("-fullscreen", True)

        self.canvas = tk.Canvas(
            root,
            highlightthickness=0,
            bg=self.BG
        )
        self.canvas.pack(fill="both", expand=True)

        self.cap = cv2.VideoCapture(0)
        self.photo = None

        # Immagini originali e immagini ridimensionate.
        self.assets = {}
        self.asset_cache = {}

        self.load_assets()

        self.level = 0
        self.selected = 0

        # ladder: schermata iniziale con la scalata
        # question: visualizzazione della domanda
        # result: visualizzazione del risultato
        # finished: vittoria finale
        self.state = "ladder"

        self.current_question = None
        self.current_prize_index = 0

        self.question_pool = DOMANDE.copy()
        random.shuffle(self.question_pool)

        self.blink_on = True
        self.last_blink = time.monotonic()

        self.root.bind("<Key>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.draw_loop()
        self.blink_loop()

    # =====================================================
    # CARICAMENTO DELLE IMMAGINI
    # =====================================================

    def load_assets(self):
        """
        Le immagini devono essere nella cartella assets/,
        situata accanto a main.py.

        assets/
            domanda.png
            risposta.png
            corretta.png
            errata_yellow.png
            errata_orange.png
        """

        for nome, filename in IMMAGINI.items():
            path = CARTELLA_ASSETS / filename

            try:
                with Image.open(path) as image:
                    self.assets[nome] = image.convert("RGBA")

            except FileNotFoundError:
                print(f"ATTENZIONE: immagine non trovata: {path}")

            except Exception as exc:
                print(f"Errore nel caricamento di {path}: {exc}")

    def draw_image(self, nome, x1, y1, x2, y2, fallback_color):
        """
        Disegna un'immagine come sfondo del testo.
        Se l'immagine manca, usa un rettangolo di fallback.
        Le immagini ridimensionate vengono memorizzate in cache.
        """

        width = max(1, int(x2 - x1))
        height = max(1, int(y2 - y1))

        original = self.assets.get(nome)

        if original is None:
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=fallback_color,
                outline=self.WHITE,
                width=2
            )
            return

        cache_key = (nome, width, height)

        if cache_key not in self.asset_cache:
            resized = original.resize(
                (width, height),
                Image.Resampling.LANCZOS
            )

            self.asset_cache[cache_key] = ImageTk.PhotoImage(resized)

        image = self.asset_cache[cache_key]

        self.canvas.create_image(
            x1, y1,
            image=image,
            anchor="nw"
        )

    # =====================================================
    # UTILITÀ
    # =====================================================

    def money(self, value):
        return f"{value:,}".replace(",", ".")

    def selected_letter(self):
        return LETTERE[self.selected]

    def close(self):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

        self.root.destroy()

    def webcam_frame(self):
        width = max(1, self.root.winfo_width())
        height = max(1, self.root.winfo_height())

        if self.cap is not None and self.cap.isOpened():
            ok, frame = self.cap.read()

            if ok:
                frame = cv2.flip(frame, 1)
                frame = cv2.resize(frame, (width, height))

                # La webcam resta naturale, senza il filtro a rete.
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                return Image.fromarray(frame)

        return Image.new(
            "RGB",
            (width, height),
            (5, 15, 35)
        )

    # =====================================================
    # DISEGNO PRINCIPALE
    # =====================================================

    def draw_loop(self):
        try:
            image = self.webcam_frame()
            self.photo = ImageTk.PhotoImage(image)

            self.canvas.delete("all")

            self.canvas.create_image(
                0, 0,
                image=self.photo,
                anchor="nw"
            )

            width, height = image.size

            if self.state == "ladder":
                # La scalata appare soltanto nella schermata iniziale
                # e quando si torna dal risultato.
                self.draw_ladder_side(width, height)

            elif self.state in ("question", "result"):
                # La scalata scompare durante domanda e risultato.
                self.draw_question(width, height)

            elif self.state == "finished":
                self.draw_finished(width, height)

        except tk.TclError:
            return
        x1 = image.width - 210
        x2 = image.width - 50
        y1 = image.height - 210
        y2 = image.height - 50
        self.draw_image("canale_5", x1, y1, x2, y2, self.BLUE)
        self.root.after(33, self.draw_loop)

    # =====================================================
    # SCALATA INIZIALE
    # =====================================================

    def draw_ladder_side(self, width, height):
        panel_x1 = width * 0.76
        panel_x2 = width * 0.98

        top = height * 0.10
        bottom = height * 0.87
        row_height = (bottom - top) / len(PREMI)

        self.canvas.create_text(
            (panel_x1 + panel_x2) / 2,
            height * 0.045,
            text="MONTEPREMI",
            fill=self.WHITE,
            font=(FONT, max(14, int(height * 0.022)), "bold")
        )

        # Premio massimo in alto, premio minimo in fondo.
        for i, prize in enumerate(reversed(PREMI)):
            actual_index = len(PREMI) - 1 - i

            y1 = top + i * row_height
            y2 = y1 + row_height - 3

            achieved = actual_index < self.level
            current = (
                actual_index == self.level
                and self.level < len(PREMI)
            )

            if achieved:
                fill = self.GREEN
                text_color = self.WHITE
            elif current:
                fill = self.GOLD
                text_color = self.BG
            else:
                fill = self.BLUE_DARK
                text_color = self.WHITE

            self.canvas.create_rectangle(
                panel_x1, y1,
                panel_x2, y2,
                fill=fill,
                outline="#c6dcff",
                width=2
            )

            self.canvas.create_text(
                panel_x1 + 10,
                (y1 + y2) / 2,
                text=str(actual_index + 1),
                fill=text_color,
                anchor="w",
                font=(FONT, max(10, int(row_height * 0.32)), "bold")
            )

            self.canvas.create_text(
                panel_x2 - 8,
                (y1 + y2) / 2,
                text=self.money(prize),
                fill=text_color,
                anchor="e",
                font=(FONT, max(10, int(row_height * 0.29)), "bold")
            )

        won = PREMI[self.level - 1] if self.level > 0 else 0

        # self.canvas.create_text(
        #     (panel_x1 + panel_x2) / 2,
        #     height * 0.92,
        #     text=f"VINTI: € {self.money(won)}",
        #     fill=self.WHITE,
        #     font=(FONT, max(11, int(height * 0.019)), "bold")
        # )

        # self.canvas.create_text(
        #     width * 0.38,
        #     height * 0.70,
        #     text="CHI VUOL ESSERE MILIONARIO",
        #     fill=self.WHITE,
        #     font=(FONT, max(24, int(height * 0.045)), "bold")
        # )

        # self.canvas.create_text(
        #     width * 0.38,
        #     height * 0.78,
        #     text="PREMI SPAZIO O INVIO PER INIZIARE",
        #     fill=self.GOLD,
        #     font=(FONT, max(13, int(height * 0.023)), "bold")
        # )

        # self.canvas.create_text(
        #     width * 0.38,
        #     height * 0.85,
        #     text="La webcam è lo sfondo del gioco",
        #     fill=self.WHITE,
        #     font=(FONT, max(11, int(height * 0.018)))
        # )

    # =====================================================
    # DOMANDA E RISPOSTE CON SFONDI IMMAGINE
    # =====================================================

    def draw_question(self, width, height):
        question = self.current_question

        if question is None:
            return

        center_x = width / 2
        content_width = width * 0.96

        # -------------------------------------------------
        # DOMANDA - SFONDO A TUTTA LARGHEZZA
        # -------------------------------------------------

        question_top = height * 0.55
        question_bottom = height * 0.70

        self.draw_image("domanda", 0, question_top, width, question_bottom, self.BLUE)

        self.canvas.create_text(
            center_x,
            (question_top + question_bottom) / 2,
            text=question.domanda,
            fill=self.WHITE,
            width=content_width,
            justify="center",
            font=(FONT, max(15, int(height * 0.025)), "bold"),
        )

        # -------------------------------------------------
        # RISPOSTE - DUE COLONNE LARGHE
        # -------------------------------------------------

        answers = [question.A, question.B, question.C, question.D]

        answer_left = width  * 0 # 0.02
        answer_right = width *  1 # 0.98
        answer_gap = width * 0 # 0.02

        answer_width = (answer_right - answer_left - answer_gap) / 2

        answers_top = height * 0.725
        row_height = height * 0.075
        gap_y = height * 0.018

        for i, (letter, answer) in enumerate(zip(LETTERE, answers)):
            row, column = divmod(i, 2)

            # Coordinate orizzontali
            x1 = answer_left + column * (answer_width + answer_gap)
            x2 = x1 + answer_width

            # Coordinate verticali: invariate
            y1 = answers_top + row * (row_height + gap_y)
            y2 = y1 + row_height

            # Sfondo predefinito
            text_color = self.WHITE
            background = "risposta_blu"

            # Colori nella schermata del risultato
            if self.state == "result":
                if letter == question.corretta:
                    if self.blink_on:
                        background = "risposta_verde"
                    else:
                        background = "risposta_arancio"

                elif letter == self.selected_letter():
                    background = "risposta_blu"
                    text_color = "#111111"

            # Sfondo della risposta
            self.draw_image(background, x1, y1, x2, y2, self.BLUE)

            # Bordo dorato sulla risposta selezionata
            if self.state == "question" and i == self.selected:
                self.canvas.create_rectangle(
                    x1 + 2, y1 + 2, x2 - 2, y2 - 2, fill="", outline=self.GOLD, width=4
                )

            # Lettera della risposta
            self.canvas.create_text(
                x1 + 50,
                (y1 + y2) / 2,
                text=f"{letter}:",
                fill=self.ORANGE,
                anchor="w",
                font=(FONT, max(13, int(height * 0.022)), "bold"),
            )

            # Testo della risposta
            self.canvas.create_text(
                x1 + 100,
                (y1 + y2) / 2,
                text=answer,
                fill=text_color,
                anchor="w",
                width=answer_width - 85,
                font=(FONT, max(12, int(height * 0.020))),
            )

        # -------------------------------------------------
        # ISTRUZIONI IN BASSO
        # -------------------------------------------------

        if self.state == "question":
            hint = "FRECCE O A/B/C/D: SELEZIONA   •   INVIO: CONFERMA"

        else:
            if self.selected_letter() == question.corretta:
                hint = "RISPOSTA CORRETTA!"
            else:
                hint = f"RISPOSTA ERRATA — " f"QUELLA CORRETTA ERA {question.corretta}"

            hint += "   •   SPAZIO/INVIO: TORNA ALLA SCALATA"

        self.canvas.create_text(
            center_x,
            height * 0.94,
            text=hint,
            fill=self.WHITE,
            width=content_width,
            justify="center",
            font=(FONT, max(11, int(height * 0.017)), "bold"),
        )

    # =====================================================
    # VITTORIA FINALE
    # =====================================================

    def draw_finished(self, width, height):
        center_x = width / 2
        center_y = height / 2

        self.canvas.create_text(
            center_x,
            center_y - 70,
            text="COMPLIMENTI!",
            fill=self.GOLD,
            font=(FONT, max(30, int(height * 0.07)), "bold")
        )

        self.canvas.create_text(
            center_x,
            center_y,
            text=f"HAI VINTO € {self.money(PREMI[-1])}",
            fill=self.WHITE,
            font=(FONT, max(24, int(height * 0.045)), "bold")
        )

        self.canvas.create_text(
            center_x,
            center_y + 75,
            text="Premi ESC per uscire",
            fill=self.WHITE,
            font=(FONT, 16)
        )

    # =====================================================
    # LOGICA DEL GIOCO
    # =====================================================

    def next_question(self):
        if self.level >= len(PREMI):
            self.state = "finished"
            return

        if not self.question_pool:
            self.question_pool = DOMANDE.copy()
            random.shuffle(self.question_pool)

        self.current_question = self.question_pool.pop()
        self.current_prize_index = self.level
        self.selected = 0
        self.state = "question"

    def reveal_answer(self):
        if self.state != "question":
            return

        self.state = "result"
        self.blink_on = True
        self.last_blink = time.monotonic()

        if self.selected_letter() == self.current_question.corretta:
            # Il premio aumenta solamente in caso di risposta corretta.
            self.level += 1

    def back_to_ladder(self):
        if self.state != "result":
            return

        if self.level >= len(PREMI):
            self.state = "finished"
        else:
            self.state = "ladder"
            self.current_question = None

    # =====================================================
    # TASTIERA
    # =====================================================

    def on_key(self, event):
        key = event.keysym.lower()
        char = (event.char or "").lower()

        if key == "escape":
            self.close()
            return

        if self.state == "ladder":
            if key in ("space", "return", "kp_enter"):
                self.next_question()
            return

        if self.state == "finished":
            return

        if self.state == "question":

            if key in ("left", "up"):
                self.selected = (self.selected - 1) % 4

            elif key in ("right", "down"):
                self.selected = (self.selected + 1) % 4

            elif char in ("a", "b", "c", "d"):
                self.selected = LETTERE.index(char.upper())

            elif key in ("return", "kp_enter"):
                self.reveal_answer()

            return

        if self.state == "result":
            if key in ("space", "return", "kp_enter"):
                self.back_to_ladder()

    # =====================================================
    # ANIMAZIONE RISPOSTA
    # =====================================================

    def blink_loop(self):
        if self.state == "result":
            now = time.monotonic()

            if now - self.last_blink >= 0.35:
                self.blink_on = not self.blink_on
                self.last_blink = now

        self.root.after(100, self.blink_loop)


# =========================================================
# AVVIO
# =========================================================

def main():
    root = tk.Tk()
    Milionario(root)
    root.mainloop()


if __name__ == "__main__":
    main()
