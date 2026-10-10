import tkinter as tk
import random
import time
from dataclasses import dataclass

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

PREMI = [
    10_000,
    20_000,
    30_000,
    50_000,
    70_000,
    100_000,
    150_000,
    200_000,
    300_000,
    1_000_000,
]

LETTERE = ("A", "B", "C", "D")


@dataclass
class Domanda:
    domanda: str
    A: str
    B: str
    C: str
    D: str
    corretta: str


DOMANDE = [
    Domanda(
        "Quale pianeta è noto come Pianeta Rosso?",
        "Venere", "Marte", "Giove", "Mercurio", "B"
    ),
    Domanda(
        "Quanti lati ha un esagono?",
        "Cinque", "Sette", "Sei", "Otto", "C"
    ),
    Domanda(
        "Qual è la capitale del Portogallo?",
        "Lisbona", "Madrid", "Porto", "Siviglia", "A"
    ),
    Domanda(
        "Chi ha dipinto la Gioconda?",
        "Caravaggio", "Raffaello", "Michelangelo",
        "Leonardo da Vinci", "D"
    ),
    Domanda(
        "Quale gas assorbono principalmente le piante nella fotosintesi?",
        "Ossigeno", "Azoto", "Anidride carbonica", "Idrogeno", "C"
    ),
    Domanda(
        "In quale continente si trova il deserto del Sahara?",
        "Africa", "Asia", "Oceania", "America del Sud", "A"
    ),
    Domanda(
        "Qual è il simbolo chimico dell'oro?",
        "Ag", "Au", "Fe", "Or", "B"
    ),
    Domanda(
        "Quanti minuti ci sono in tre ore?",
        "120", "150", "180", "210", "C"
    ),
    Domanda(
        "Chi scrisse I promessi sposi?",
        "Giovanni Verga", "Italo Calvino",
        "Giosuè Carducci", "Alessandro Manzoni", "D"
    ),
    Domanda(
        "Quale di questi è un mammifero?",
        "Squalo", "Delfino", "Trota", "Polpo", "B"
    ),
    Domanda(
        "Qual è la capitale del Canada?",
        "Toronto", "Vancouver", "Ottawa", "Montréal", "C"
    ),
    Domanda(
        "Quale strumento misura la pressione atmosferica?",
        "Barometro", "Termometro", "Anemometro", "Igrometro", "A"
    ),
    Domanda(
        "In quale anno è caduto il Muro di Berlino?",
        "1987", "1989", "1991", "1993", "B"
    ),
    Domanda(
        "Qual è il numero primo più piccolo?",
        "0", "1", "2", "3", "C"
    ),
    Domanda(
        "Quale oceano è il più grande?",
        "Atlantico", "Indiano", "Artico", "Pacifico", "D"
    ),
]


# =========================================================
# GIOCO
# =========================================================

class MilionarioWebcam:

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

        self.cap = cv2.VideoCapture(0)

        self.canvas = tk.Canvas(
            root,
            highlightthickness=0,
            bg=self.BG
        )
        self.canvas.pack(fill="both", expand=True)

        self.photo = None

        self.level = 0
        self.selected = 0

        # ladder: scalata iniziale
        # question: domanda
        # result: risultato della risposta
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

    # -----------------------------------------------------
    # UTILITÀ
    # -----------------------------------------------------

    def money(self, value):
        return f"{value:,}".replace(",", ".")

    def close(self):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

        self.root.destroy()

    def selected_letter(self):
        return LETTERE[self.selected]

    def webcam_frame(self):
        width = max(1, self.root.winfo_width())
        height = max(1, self.root.winfo_height())

        if self.cap is not None and self.cap.isOpened():
            ok, frame = self.cap.read()

            if ok:
                frame = cv2.flip(frame, 1)
                frame = cv2.resize(frame, (width, height))

                # Sfondo scurito per rendere leggibili le grafiche.
                frame = cv2.convertScaleAbs(
                    frame,
                    alpha=0.55,
                    beta=-15
                )

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                return Image.fromarray(frame)

        return Image.new(
            "RGB",
            (width, height),
            (5, 15, 35)
        )

    # -----------------------------------------------------
    # DISEGNO PRINCIPALE
    # -----------------------------------------------------

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

            # Velo scuro trasparente sulla webcam.
            self.canvas.create_rectangle(
                0, 0, width, height,
                fill="#020817",
                stipple="gray50",
                outline=""
            )

            if self.state == "ladder":
                # La scalata appare soltanto nella schermata iniziale
                # e quando si torna dal risultato.
                self.draw_ladder_side(width, height)

            elif self.state in ("question", "result"):
                # Durante la domanda e il risultato la scalata
                # scompare completamente. Le grafiche occupano
                # la larghezza dello schermo nella parte inferiore.
                self.draw_question(width, height)

            elif self.state == "finished":
                self.draw_finished(width, height)

        except tk.TclError:
            return

        self.root.after(33, self.draw_loop)

    # -----------------------------------------------------
    # SCALATA INIZIALE
    # -----------------------------------------------------

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
            font=("Arial", max(14, int(height * 0.022)), "bold")
        )

        # Il premio più alto è in cima, quello più basso in fondo.
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
                text_color = "#06152b"
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
                font=("Arial", max(10, int(row_height * 0.32)), "bold")
            )

            self.canvas.create_text(
                panel_x2 - 8,
                (y1 + y2) / 2,
                text=self.money(prize),
                fill=text_color,
                anchor="e",
                font=("Arial", max(10, int(row_height * 0.29)), "bold")
            )

        won = PREMI[self.level - 1] if self.level > 0 else 0

        self.canvas.create_text(
            (panel_x1 + panel_x2) / 2,
            height * 0.92,
            text=f"VINTI: € {self.money(won)}",
            fill=self.WHITE,
            font=("Arial", max(11, int(height * 0.019)), "bold")
        )

        self.canvas.create_text(
            width * 0.38,
            height * 0.70,
            text="CHI VUOL ESSERE MILIONARIO",
            fill=self.WHITE,
            font=("Arial", max(24, int(height * 0.045)), "bold")
        )

        self.canvas.create_text(
            width * 0.38,
            height * 0.78,
            text="PREMI SPAZIO O INVIO PER INIZIARE",
            fill=self.GOLD,
            font=("Arial", max(13, int(height * 0.023)), "bold")
        )

        self.canvas.create_text(
            width * 0.38,
            height * 0.85,
            text="La webcam è lo sfondo del gioco",
            fill=self.WHITE,
            font=("Arial", max(11, int(height * 0.018)))
        )

    # -----------------------------------------------------
    # DOMANDA E RISPOSTE: PARTE INFERIORE DELLO SCHERMO
    # -----------------------------------------------------

    def draw_question(self, width, height):
        question = self.current_question

        if question is None:
            return

        # Le grafiche partono in basso, lasciando libera la parte
        # superiore per la webcam. Non viene disegnata la scalata.
        left = width * 0.035
        right = width * 0.965
        center_x = (left + right) / 2
        content_width = right - left

        question_top = height * 0.55
        question_bottom = height * 0.70

        prize = PREMI[self.current_prize_index]
        question_number = self.current_prize_index + 1

        self.canvas.create_rectangle(
            left, question_top,
            right, question_bottom,
            fill=self.BLUE,
            outline="#d6e6ff",
            width=3
        )

        self.canvas.create_text(
            center_x,
            (question_top + question_bottom) / 2,
            text=f"DOMANDA {question_number}  •  € {self.money(prize)}\n\n{question.domanda}",
            fill=self.WHITE,
            width=content_width * 0.94,
            justify="center",
            font=("Arial", max(15, int(height * 0.025)), "bold")
        )

        answers = [
            question.A,
            question.B,
            question.C,
            question.D
        ]

        gap_x = width * 0.018
        column_width = (content_width - gap_x) / 2

        answers_top = height * 0.725
        row_height = height * 0.075
        gap_y = height * 0.018

        for i, (letter, answer) in enumerate(zip(LETTERE, answers)):
            row, column = divmod(i, 2)

            x1 = left + column * (column_width + gap_x)
            x2 = x1 + column_width

            y1 = answers_top + row * (row_height + gap_y)
            y2 = y1 + row_height

            fill = self.BLUE
            outline = "#c7d9f2"
            text_color = self.WHITE

            if self.state == "result":
                if letter == question.corretta:
                    # La risposta corretta rimane verde.
                    fill = self.GREEN
                    outline = "#d8ffe1"

                elif letter == self.selected_letter():
                    # La risposta sbagliata lampeggia giallo/arancione.
                    if self.blink_on:
                        fill = self.YELLOW
                        outline = self.ORANGE
                    else:
                        fill = self.ORANGE
                        outline = self.YELLOW

                    text_color = "#171717"

            elif i == self.selected:
                # Risposta attualmente selezionata.
                fill = "#d87500"
                outline = self.GOLD

            self.canvas.create_rectangle(
                x1, y1,
                x2, y2,
                fill=fill,
                outline=outline,
                width=3
            )

            self.canvas.create_text(
                x1 + 15,
                (y1 + y2) / 2,
                text=f"{letter}:",
                fill=text_color,
                anchor="w",
                font=("Arial", max(13, int(height * 0.022)), "bold")
            )

            self.canvas.create_text(
                x1 + 65,
                (y1 + y2) / 2,
                text=answer,
                fill=text_color,
                anchor="w",
                width=column_width - 85,
                font=("Arial", max(12, int(height * 0.020)))
            )

        if self.state == "question":
            hint = "FRECCE O A/B/C/D: SELEZIONA   •   INVIO: CONFERMA"
        else:
            if self.selected_letter() == question.corretta:
                hint = "RISPOSTA CORRETTA!"
            else:
                hint = (
                    f"RISPOSTA ERRATA — "
                    f"QUELLA CORRETTA ERA {question.corretta}"
                )

            hint += "   •   SPAZIO/INVIO: TORNA ALLA SCALATA"

        self.canvas.create_text(
            center_x,
            height * 0.94,
            text=hint,
            fill=self.WHITE,
            width=content_width,
            justify="center",
            font=("Arial", max(11, int(height * 0.017)), "bold")
        )

    # -----------------------------------------------------
    # VITTORIA FINALE
    # -----------------------------------------------------

    def draw_finished(self, width, height):
        center_x = width / 2
        center_y = height / 2

        self.canvas.create_text(
            center_x,
            center_y - 70,
            text="COMPLIMENTI!",
            fill=self.GOLD,
            font=("Arial", max(30, int(height * 0.07)), "bold")
        )

        self.canvas.create_text(
            center_x,
            center_y,
            text=f"HAI VINTO € {self.money(PREMI[-1])}",
            fill=self.WHITE,
            font=("Arial", max(24, int(height * 0.045)), "bold")
        )

        self.canvas.create_text(
            center_x,
            center_y + 75,
            text="Premi ESC per uscire",
            fill=self.WHITE,
            font=("Arial", 16)
        )

    # -----------------------------------------------------
    # LOGICA DEL GIOCO
    # -----------------------------------------------------

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
            # Il premio sale esclusivamente con una risposta corretta.
            self.level += 1

    def back_to_ladder(self):
        if self.state != "result":
            return

        if self.level >= len(PREMI):
            self.state = "finished"
        else:
            self.state = "ladder"
            self.current_question = None

    # -----------------------------------------------------
    # TASTIERA
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # ANIMAZIONE RISPOSTA ERRATA
    # -----------------------------------------------------

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
    MilionarioWebcam(root)
    root.mainloop()


if __name__ == "__main__":
    main()