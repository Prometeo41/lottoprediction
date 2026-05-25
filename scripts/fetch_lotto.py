#!/usr/bin/env python3
"""
Script per scaricare le ultime estrazioni del Lotto italiano.
Viene eseguito da GitHub Actions 3 volte a settimana.
Salva i dati in data/latest.json
"""
import requests, json, re, os
from datetime import datetime
from bs4 import BeautifulSoup

RUOTE = ['Bari','Cagliari','Firenze','Genova','Milano',
         'Napoli','Palermo','Roma','Torino','Venezia','Nazionale']

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9',
}

OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'data', 'latest.json')

def load_existing():
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'draws': [], 'last_update': None}

def save(data):
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_date(s):
    """Converte vari formati data in GG/MM/AAAA"""
    for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y','%d.%m.%Y'):
        try:
            return datetime.strptime(s.strip(), fmt).strftime('%d/%m/%Y')
        except: pass
    return None

def fetch_from_lottomatica():
    """Prova a scaricare da Lottomatica"""
    draws = []
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        # Prima richiesta per cookie
        s.get('https://www.lottomatica.it/', timeout=10)
        r = s.get('https://www.lottomatica.it/lotterie/lotto/risultati', timeout=15)
        if r.status_code != 200:
            print(f"Lottomatica: HTTP {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, 'lxml')

        # Cerca tabella risultati
        # Struttura tipica: data, ruota, 5 numeri
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td','th'])
                if len(cells) >= 7:
                    texts = [c.get_text(strip=True) for c in cells]
                    # Prova a parsare: data, concorso, ruota, n1, n2, n3, n4, n5
                    date = parse_date(texts[0]) if texts else None
                    if date and len(texts) >= 7:
                        try:
                            nums = [int(texts[i]) for i in range(3,8)]
                            if all(1 <= n <= 90 for n in nums):
                                ruota = texts[2].strip().capitalize()
                                if ruota in RUOTE:
                                    draws.append({
                                        'date': date,
                                        'concorso': int(texts[1]) if texts[1].isdigit() else 0,
                                        'ruota': ruota,
                                        'nums': nums
                                    })
                        except: pass

        # Cerca anche dati in formato JSON incorporato nella pagina
        json_matches = re.findall(r'"date"\s*:\s*"([^"]+)".*?"numbers"\s*:\s*\[([^\]]+)\]', r.text)
        for date_str, nums_str in json_matches:
            date = parse_date(date_str)
            if date:
                try:
                    nums = [int(n.strip()) for n in nums_str.split(',')]
                    if len(nums) == 5 and all(1 <= n <= 90 for n in nums):
                        print(f"  JSON trovato: {date} {nums}")
                except: pass

        print(f"Lottomatica: trovate {len(draws)} estrazioni")
    except Exception as e:
        print(f"Lottomatica errore: {e}")
    return draws

def fetch_from_adm():
    """Prova a scaricare dal sito ADM (governo italiano)"""
    draws = []
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        r = s.get('https://www.adm.gov.it/portale/monopoli/giochi/gioco-del-lotto/risultati-delle-estrazioni', timeout=15)
        if r.status_code != 200:
            print(f"ADM: HTTP {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, 'lxml')
        print(f"ADM: OK {len(r.text)} chars")

        # Cerca dati strutturati nella pagina ADM
        # La struttura varia, prova diverse strategie
        for tag in soup.find_all(['div','span','td'], class_=re.compile(r'(numero|estraz|ruota|lotto)', re.I)):
            text = tag.get_text(strip=True)
            if text.isdigit() and 1 <= int(text) <= 90:
                pass  # raccolta numeri

    except Exception as e:
        print(f"ADM errore: {e}")
    return draws

def fetch_from_alternative():
    """Fonti alternative"""
    draws = []
    urls = [
        'https://www.gioconews.it/lotto/',
        'https://www.estrazionelotto.it/',
        'https://www.superenalotto.net/lotto/estrazioni',
    ]
    for url in urls:
        try:
            s = requests.Session()
            s.headers.update(HEADERS)
            r = s.get(url, timeout=12)
            if r.status_code != 200:
                continue
            if 'Napoli' not in r.text and 'napoli' not in r.text:
                continue

            soup = BeautifulSoup(r.text, 'lxml')
            print(f"Fonte alternativa OK: {url} ({len(r.text)} chars)")

            # Strategia generica: cerca tutti i numeri vicino ai nomi delle ruote
            for ruota in RUOTE:
                # Cerca elemento con nome della ruota
                el = soup.find(string=re.compile(ruota, re.I))
                if el:
                    parent = el.parent
                    # Cerca i 5 numeri vicini
                    for _ in range(5):  # sali nella gerarchia
                        parent = parent.parent if parent else None
                        if not parent: break
                        nums_found = re.findall(r'\b([1-9]|[1-8]\d|90)\b', parent.get_text())
                        if len(nums_found) >= 5:
                            try:
                                nums = [int(n) for n in nums_found[:5]]
                                # Cerca la data vicina
                                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', parent.get_text())
                                if date_match:
                                    draws.append({
                                        'date': date_match.group(1),
                                        'concorso': 0,
                                        'ruota': ruota,
                                        'nums': nums
                                    })
                            except: pass
                            break

            if draws:
                print(f"  Trovate {len(draws)} estrazioni da {url}")
                break
        except Exception as e:
            print(f"  {url}: {e}")

    return draws

def main():
    print(f"=== Aggiornamento Lotto {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")

    existing = load_existing()
    old_draws = existing.get('draws', [])
    seen = set(f"{d['date']}|{d['ruota']}" for d in old_draws)

    new_draws = []

    # Prova le fonti in ordine
    for fetch_fn in [fetch_from_lottomatica, fetch_from_adm, fetch_from_alternative]:
        result = fetch_fn()
        if result:
            new_draws = result
            break

    if not new_draws:
        print("NESSUNA FONTE DISPONIBILE - dati non aggiornati")
        # Aggiorna solo il timestamp
        existing['last_update'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        existing['status'] = 'Aggiornamento fallito - nessuna fonte disponibile'
        save(existing)
        return

    # Aggiungi solo le nuove estrazioni
    added = []
    for d in new_draws:
        k = f"{d['date']}|{d['ruota']}"
        if k not in seen:
            added.append(d)
            seen.add(k)

    all_draws = old_draws + added
    result = {
        'draws': all_draws,
        'last_update': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'status': f'OK - {len(added)} nuove estrazioni aggiunte ({len(all_draws)} totali)',
        'total': len(all_draws)
    }
    save(result)
    print(f"=== FINE: +{len(added)} nuove, {len(all_draws)} totali ===")

if __name__ == '__main__':
    main()
