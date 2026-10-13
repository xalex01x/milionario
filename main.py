import tkinter as tk
import random
import time
from pathlib import Path
import pygame

from domande import DOMANDE
from config import LETTERE, PREMI, IMMAGINI

try:
    import cv2
    from PIL import Image, ImageTk
except ImportError as exc:
    raise SystemExit(
        "Installa le librerie necessarie con:\n" "pip install opencv-python pillow"
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

        self.canvas = tk.Canvas(root, highlightthickness=0, bg=self.BG)
        self.canvas.pack(fill="both", expand=True)
        pygame.mixer.init()

        # Effetti sonori e musica di sottofondo
        self.audio = {
            "loop": pygame.mixer.Sound(str(CARTELLA_ASSETS / "music_loop.mp3")),
            "corretta": pygame.mixer.Sound(str(CARTELLA_ASSETS / "music_correct.mp3")),
            "sbagliata": pygame.mixer.Sound(str(CARTELLA_ASSETS / "music_wrong.mp3")),
            "definitiva": pygame.mixer.Sound(
                str(CARTELLA_ASSETS / "music_definitive.mp3")
            ),
        }

        # Canali indipendenti
        self.loop_channel = pygame.mixer.Channel(0)
        self.sfx_channel = pygame.mixer.Channel(2)

        # La sigla iniziale viene riprodotta come musica in streaming
        pygame.mixer.music.load(str(CARTELLA_ASSETS / "music_intro.mp3"))
        pygame.mixer.music.set_volume(1.0)

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
        # intro: intro
        self.state = "intro"

        self.current_question = None
        self.current_prize_index = 0

        self.audio_transition_pending = False
        self.audio_transition_id = None

        self.question_pool = DOMANDE.copy()
        # random.shuffle(self.question_pool)

        self.blink_on = True
        self.last_blink = time.monotonic()

        self.root.bind("<Key>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        pygame.mixer.music.play()
        self.draw_loop()
        self.blink_loop()

    # =====================================================
    # MUSICA
    # =====================================================

    def start_loop(self):
        """Avvia il loop se non è già in riproduzione."""
        if not self.loop_channel.get_busy():
            self.loop_channel.play(self.audio["loop"], loops=-1)

    def stop_loop(self):
        """Interrompe la musica di sottofondo."""
        self.loop_channel.stop()

    def play_effect(self, name):
        """Interrompe il loop e riproduce un effetto sonoro."""
        self.stop_loop()
        self.sfx_channel.stop()
        self.sfx_channel.play(self.audio[name])

    def needs_final_confirmation(self):
        """Le domande da 100.000 € in su richiedono due Invii."""
        return self.level < len(PREMI) and PREMI[self.level] >= 100000

    def schedule_audio_transition(self, channel, callback):
        """Esegue callback quando termina l'audio."""

        self.audio_transition_pending = True

        def check_audio():
            if not channel.get_busy():
                self.audio_transition_pending = False
                self.audio_transition_id = None
                callback()
            else:
                self.audio_transition_id = self.root.after(100, check_audio)

        self.audio_transition_id = self.root.after(100, check_audio)

    def cancel_audio_transition(self):
        """Annulla un cambio schermata programmato."""

        if self.audio_transition_id is not None:
            self.root.after_cancel(self.audio_transition_id)
            self.audio_transition_id = None

        self.audio_transition_pending = False

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
        area_w = max(1, int(x2 - x1))
        area_h = max(1, int(y2 - y1))

        original = self.assets.get(nome)

        if original is None:
            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=fallback_color, outline=self.WHITE, width=2
            )
            return

        # Fattore di scala: l'immagine entra interamente nell'area
        scale = min(area_w / original.width, area_h / original.height)

        new_w = max(1, int(original.width * scale))
        new_h = max(1, int(original.height * scale))

        cache_key = (nome, new_w, new_h)

        if cache_key not in self.asset_cache:
            resized = original.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.asset_cache[cache_key] = ImageTk.PhotoImage(resized)

        image = self.asset_cache[cache_key]

        # Centra l'immagine nell'area
        pos_x = x1 + (area_w - new_w) / 2
        pos_y = y1 + (area_h - new_h) / 2

        self.canvas.create_image(pos_x, pos_y, image=image, anchor="nw")

    # =====================================================
    # UTILITÀ
    # =====================================================

    def money(self, value):
        return f"{value:,}".replace(",", ".")

    def selected_letter(self):
        return LETTERE[self.selected]

    def close(self):
        self.cancel_audio_transition()
        self.stop_loop()
        pygame.mixer.music.stop()

        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

        pygame.mixer.quit()
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

        return Image.new("RGB", (width, height), (5, 15, 35))

    # =====================================================
    # DISEGNO PRINCIPALE
    # =====================================================

    def draw_loop(self):
        try:
            if self.state == "intro":
                self.canvas.delete("all")
                self.canvas.configure(bg="black")

                width = max(1, self.root.winfo_width())
                height = max(1, self.root.winfo_height())

                self.canvas.create_rectangle(
                    0, 0, width, height, fill="black", outline="black"
                )
                center_x = width / 2
                center_y = height / 2
                logo_size = 800
                x1 = (center_x - (logo_size / 2)) - 50
                x2 = (center_x + (logo_size / 2)) + 50
                y1 = center_y - logo_size / 2
                y2 = center_y + logo_size / 2
                self.draw_image("logo", x1, y1, x2, y2, self.BLUE)

                # self.canvas.create_text(
                #     width / 2,
                #     height * 0.80,
                #     text="PREMI INVIO PER INIZIARE",
                #     fill=self.GOLD,
                #     font=(FONT, max(16, int(height * 0.025)), "bold"),
                # )

                self.root.after(33, self.draw_loop)
                return

            image = self.webcam_frame()
            self.photo = ImageTk.PhotoImage(image)

            self.canvas.delete("all")

            self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

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
        # Dimensioni dello sfondo della scalata
        panel_x1 = width * 0.60
        panel_x2 = width + 1  # * 0.98
        panel_top = height * 0  # * 0.08
        panel_bottom = height  # * 0.89

        # Un solo sfondo per tutta la scalata
        self.draw_image(
            "sfondo_scalata",
            panel_x1,
            panel_top,
            panel_x2,
            panel_bottom,
            self.BLUE_DARK,
        )

        # Titolo
        self.canvas.create_text(
            (panel_x1 + panel_x2) / 2,
            panel_top + height * 0.025,
            text="VITTORIA",
            fill=self.WHITE,
            font=(FONT, max(14, int(height * 0.022)), "bold"),
        )

        # Spazio interno per i valori
        values_top = panel_top + height * 0.065
        values_bottom = panel_bottom - height * 0.015
        row_height = (values_bottom - values_top) / len(PREMI)

        # Premio massimo in alto, minimo in fondo
        for i, prize in enumerate(reversed(PREMI)):
            actual_index = len(PREMI) - 1 - i
            y = values_top + i * row_height + row_height / 2

            achieved = actual_index < self.level
            current = actual_index == self.level and self.level < len(PREMI)

            if achieved:
                text_color = self.ORANGE
            elif current:
                text_color = self.GOLD
            else:
                text_color = self.WHITE

            # Numero del livello
            self.canvas.create_text(
                panel_x1 + (panel_x2 - panel_x1) * 0.12,
                y,
                text=str(actual_index + 1),
                fill=text_color,
                anchor="center",
                font=(FONT, max(10, int(row_height * 0.48)), "bold"),
            )

            # Importo
            self.canvas.create_text(
                panel_x2 - (panel_x2 - panel_x1) * 0.08,
                y,
                text=self.money(prize),
                fill=text_color,
                anchor="e",
                font=(FONT, max(10, int(row_height * 0.44)), "bold"),
            )

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

        question_top = height * 0.60
        question_bottom = height * 0.75

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

        answer_left = width * 0  # 0.02
        answer_right = width * 1  # 0.98
        answer_gap = width * 0  # 0.02

        answer_width = (answer_right - answer_left - answer_gap) / 2

        answers_top = height * 0.775
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
        # IMMAGINI DOMANDA
        # -------------------------------------------------

        if question.immagine is not None:
            self.draw_image(
                question.immagine, width / 2, 0, width, question_top - 50, self.BLUE
            )

        # -------------------------------------------------
        # ISTRUZIONI IN BASSO
        # -------------------------------------------------

        # if self.state == "question":
        #     if self.awaiting_final_confirmation:
        #         hint = "RISPOSTA DEFINITIVA — PREMI INVIO PER CONFERMARE"
        #     elif self.needs_final_confirmation():
        #         hint = "FRECCE O A/B/C/D: SELEZIONA • INVIO: RISPOSTA DEFINITIVA"
        #     else:
        #         hint = "FRECCE O A/B/C/D: SELEZIONA • INVIO: CONFERMA"
        # else:
        #     hint = "SPAZIO/INVIO: TORNA ALLA SCALATA"

        # self.canvas.create_text(
        #     center_x,
        #     height * 0.94,
        #     text=hint,
        #     fill=self.WHITE,
        #     width=content_width,
        #     justify="center",
        #     font=(FONT, max(11, int(height * 0.017)), "bold"),
        # )

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
            font=(FONT, max(30, int(height * 0.07)), "bold"),
        )

        self.canvas.create_text(
            center_x,
            center_y,
            text=f"HAI VINTO € {self.money(PREMI[-1])}",
            fill=self.WHITE,
            font=(FONT, max(24, int(height * 0.045)), "bold"),
        )

        self.canvas.create_text(
            center_x,
            center_y + 75,
            text="Premi ESC per uscire",
            fill=self.WHITE,
            font=(FONT, 16),
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
        # Music
        self.awaiting_final_confirmation = False
        self.start_loop()

    def reveal_answer(self):
        if self.state != "question":
            return

        if self.audio_transition_pending:
            return

        # Domande da 100.000 € in su:
        # primo Invio = risposta definitiva.
        if self.needs_final_confirmation():
            if not self.awaiting_final_confirmation:
                self.awaiting_final_confirmation = True
                self.play_effect("definitiva")
                return

        is_correct = self.selected_letter() == self.current_question.corretta

        self.state = "result"
        self.blink_on = True
        self.last_blink = time.monotonic()

        if is_correct:
            self.level += 1
            self.play_effect("corretta")
        else:
            self.play_effect("sbagliata")

        # La schermata del risultato resta visibile
        # fino alla fine del suono.
        self.schedule_audio_transition(self.sfx_channel, self.back_to_ladder)

    def back_to_ladder(self):
        if self.state != "result":
            return

        self.stop_loop()
        self.sfx_channel.stop()
        self.awaiting_final_confirmation = False

        if self.level >= len(PREMI):
            self.state = "finished"
            # Riproduce nuovamente la sigla alla vittoria
            pygame.mixer.music.play()
        else:
            self.state = "ladder"
            self.current_question = None

    # =====================================================
    # TASTIERA
    # =====================================================

    def on_key(self, event):
        key = event.keysym.lower()
        char = (event.char or "").lower()

        # ESC esce sempre dal gioco
        if key == "escape":
            self.close()
            return

        # SCHERMATA INTRO: primo Invio
        if self.state == "intro":
            if key in ("return", "kp_enter"):
                pygame.mixer.music.stop()
                self.start_loop()
                self.state = "ladder"
            return

        # SCALATA: Invio apre la domanda successiva
        if self.state == "ladder":
            if key in ("space", "return", "kp_enter"):
                self.next_question()
            return

        # SCHERMATA DI VITTORIA FINALE
        if self.state == "finished":
            return

        # SCHERMATA DELLA DOMANDA
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

        # SCHERMATA DEL RISULTATO
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
