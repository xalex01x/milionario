# Milionario

## Installazione

Per poter eseguire questo gioco bisogna che python sia installato.
Fatto ciò, creare una nuova `venv`:

- `python.exe -m venv venv`
- `cd \path\alla\cartella\del\progetto`
- `.\venv\Scripts\Activate` (Windows) oppure `source .\venv\bin\activate` (Linux)

Installare tutti i moduli necessari via:

- `pip install -e .`

Eseguire con:

- `python.exe .\main.py`

## Configurazione

File `domande.py`:

- `DOMANDE`: aggiungi nuove domande qui.

File `config.py`:

- `CAMERA_INDEX`: indice che identifica una webcam (lasciare a `0` se ne esite una sola).
- `PREMI`: aggiungi nuovi premi qui. Deve esserci un premio per ogni domanda.
- `IMMAGINI`: dizionario che contiene le immagini del progetto.

## Esempio

Aggiungiamo questa domanda:

```python
DOMANDE = [
    Domanda(
            "Questo è il quesito!",
            "RispostaA",
            "RispostaB",
            "RispostaC",
            "RispostaD",
            "C",
            "NomeImmagine",
        ),
]
```

- `"Questo è il quesito!"`: domanda
- `"RispostaA", "RispostaB", "RispostaC", "RispostaD"`: opzioni
- `"C"`: risposta corretta
- `"NomeImmagine"`: immagine relativa alla domanda. Lasciare a `None` se non è necessaria.

Nel caso volessimo aggiungere un'immagine ad una domanda:

```python
IMMAGINI = {
    "domanda": "blue.png",
    "risposta_blu": "blue.png",
    "risposta_verde": "verde.png",
    "risposta_arancio": "arancio.png",
    "canale_5": "canale_5.png",
    "sfondo_scalata": "sfondo_scalata.png",
    "logo": "logo.png",
    # Aggiungila così
    "NomeImmagine": "nome_file_immagine_dentro_cartella_assets.png",
}
```

## Controlli

- `A` `B` `C` `D` o le `freccette` per navigare le domande.
- `Invio` per confermare.
- `Esc` per lasciare il gioco.
