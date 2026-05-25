# 🎱 Lotto Prediction Engine — PWA

App installabile su qualsiasi telefono (Android, iPhone) e computer.
Aggiornamento automatico delle estrazioni 3 volte a settimana.

---

## 📱 Come installare sul telefono

### Android (Brave / Chrome)
1. Apri il sito nel browser
2. Tap sui 3 puntini in alto a destra
3. Seleziona "Aggiungi a schermata Home"
4. Conferma — l'app appare come icona sul telefono

### iPhone (Safari)
1. Apri il sito in Safari
2. Tap sull'icona Condividi (quadrato con freccia)
3. Seleziona "Aggiungi a schermata Home"
4. Conferma

---

## 🚀 Come mettere online (gratis, 15 minuti)

### Step 1 — Crea account GitHub
Vai su https://github.com e registrati gratis.

### Step 2 — Crea repository
- Clicca "+ New repository"
- Nome: `lottoprediction` (o quello che vuoi)
- Spunta "Public"
- Clicca "Create repository"

### Step 3 — Carica i file
Trascina TUTTI i file di questa cartella nel repository GitHub.
(oppure usa GitHub Desktop: https://desktop.github.com)

### Step 4 — Attiva GitHub Pages
- Vai in Settings → Pages
- Source: "Deploy from branch" → main → / (root)
- Clicca Save
- Dopo 2 minuti l'app è online su: https://TUONOME.github.io/lottoprediction

### Step 5 — Attiva aggiornamenti automatici
- Vai nella tab "Actions" del repository
- Clicca "I understand my workflows, go ahead and enable them"
- GitHub eseguirà automaticamente lo script ogni martedì, giovedì e sabato

---

## 📂 Struttura dei file

```
lottopwa/
├── index.html          ← App principale (PWA)
├── manifest.json       ← Configurazione PWA
├── sw.js               ← Service Worker (offline + cache)
├── icon-192.png        ← Icona telefono
├── icon-512.png        ← Icona splash screen
├── data/
│   └── latest.json     ← Estrazioni aggiornate automaticamente
├── scripts/
│   └── fetch_lotto.py  ← Script di scraping
└── .github/
    └── workflows/
        └── update_lotto.yml  ← Automazione GitHub Actions
```

---

## 💾 I tuoi dati storici

Carica i tuoi anni di dati (2015-2026) con il pulsante "+ Carica estrazioni".
Vengono salvati nel telefono e NON si perdono.
Il sistema automatico aggiunge solo le nuove estrazioni.

---

## 💰 Versione Premium

Per aggiungere pagamenti e piani Free/Premium:
1. Registrati su https://lemonsqueezy.com
2. Crea un prodotto "Abbonamento mensile" a 7.99 euro
3. Contatta lo sviluppatore per l'integrazione

---

## ⚠️ Note legali

Questo software è SOLO uno strumento di analisi statistica.
Non garantisce vincite. Il Gioco del Lotto è un gioco d'azzardo.
**Numero Verde Gioco Responsabile: 800 274 274**
