#!/usr/bin/env python3
"""
Script per scaricare le ultime estrazioni del Lotto italiano.
Eseguito da GitHub Actions 3 volte a settimana (mar/gio/sab).
Salva i dati in data/latest.json
"""
import requests, json, re, os, time
from datetime import datetime
from bs4 import BeautifulSoup

RUOTE = ['Bari','Cagliari','Firenze','Genova','Milano',
         'Napoli','Palermo','Roma','Torino','Venezia','Nazionale']

RUOTE_LOWER = {r.lower(): r for r in RUOTE}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
}

OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data', 'latest.json')

# ── UTILITÀ ──────────────────────────────────────────────────────────────────

def parse_date(s):
    s = s.strip()
    for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y','%d.%m.%Y','%d %m %Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%d/%m/%Y')
        except: pass
    # Prova formato "17 maggio 2026"
    mesi = {'gennaio':1,'febbraio':2,'marzo':3,'aprile':4,'maggio':5,'giugno':6,
            'luglio':7,'agosto':8,'settembre':9,'ottobre':10,'novembre':11,'dicembre':12}
    m = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', s.lower())
    if m:
        mese = mesi.get(m.group(2))
        if mese:
            try:
                return datetime(int(m.group(3)), mese, int(m.group(1))).strftime('%d/%m/%Y')
            except: pass
    return None

def normalize_ruota(s):
    s = s.strip().lower()
    return RUOTE_LOWER.get(s)

def is_valid_nums(nums):
    return (isinstance(nums, list) and len(nums) == 5 and
            all(isinstance(n, int) and 1 <= n <= 90 for n in nums))

def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def load_existing():
    if os.path.exists(OUT_FILE):
        try:
            with open(OUT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {'draws': [], 'last_update': None}

def save(data):
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── FONTE 1: IL TROVATORE ─────────────────────────────────────────────────────

def fetch_iltrovatore():
    """iltrovatore.it — tabella pulita: Data | Concorso | Ruota | N1..N5"""
    draws = []
    try:
        s = make_session()
        r = s.get('https://www.iltrovatore.it/lotto/archivio.php', timeout=15)
        if r.status_code != 200:
            print(f"  iltrovatore: HTTP {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, 'lxml')
        for tr in soup.find_all('tr'):
            tds = [td.get_text(strip=True) for td in tr.find_all('td')]
            if len(tds) < 8: continue
            date = parse_date(tds[0])
            if not date: continue
            ruota = normalize_ruota(tds[2])
            if not ruota: continue
            try:
                nums = [int(tds[i]) for i in range(3, 8)]
                conc = int(tds[1]) if tds[1].isdigit() else 0
            except: continue
            if is_valid_nums(nums):
                draws.append({'date': date, 'concorso': conc, 'ruota': ruota, 'nums': nums})
        print(f"  iltrovatore: {len(draws)} estrazioni")
    except Exception as e:
        print(f"  iltrovatore errore: {e}")
    return draws

# ── FONTE 2: ESTRAZIONE LOTTO (HTML semplice) ─────────────────────────────────

def fetch_estrazionelotto():
    """estrazionelotto.it — cerca tabelle con classi note"""
    draws = []
    urls_to_try = [
        'https://www.estrazionelotto.it/',
        'https://www.estrazionelotto.it/estrazioni-lotto-oggi/',
        'https://www.estrazionedellotto.it/',
    ]
    for url in urls_to_try:
        try:
            s = make_session()
            r = s.get(url, timeout=15)
            if r.status_code != 200 or 'Napoli' not in r.text:
                continue
            soup = BeautifulSoup(r.text, 'lxml')
            # Cerca data del concorso
            date_tag = soup.find(string=re.compile(r'\d{2}/\d{2}/\d{4}'))
            date = parse_date(date_tag.strip()) if date_tag else None
            if not date:
                # Cerca data nel titolo o heading
                for tag in soup.find_all(['h1','h2','h3','title','p']):
                    m = re.search(r'(\d{2}/\d{2}/\d{4})', tag.get_text())
                    if m:
                        date = m.group(1)
                        break
            if not date: continue
            # Cerca numero concorso
            conc = 0
            m = re.search(r'concorso\s+(?:n[°\.]?\s*)?(\d+)', r.text, re.I)
            if m: conc = int(m.group(1))
            # Cerca ogni ruota
            for ruota in RUOTE:
                el = soup.find(string=re.compile(r'\b' + ruota + r'\b', re.I))
                if not el: continue
                parent = el.parent
                for _ in range(6):
                    if not parent: break
                    text = parent.get_text()
                    nums_found = re.findall(r'\b([1-9]|[1-8]\d|90)\b', text)
                    if len(nums_found) >= 5:
                        try:
                            nums = [int(n) for n in nums_found[:5]]
                            if is_valid_nums(nums):
                                draws.append({'date': date, 'concorso': conc,
                                              'ruota': ruota, 'nums': nums})
                        except: pass
                        break
                    parent = parent.parent
            if draws:
                print(f"  estrazionelotto ({url}): {len(draws)} estrazioni")
                return draws
        except Exception as e:
            print(f"  estrazionelotto {url}: {e}")
    return draws

# ── FONTE 3: LOTTOMATICA (con session + cookie) ───────────────────────────────

def fetch_lottomatica():
    """Prova lottomatica con sessione completa"""
    draws = []
    try:
        s = make_session()
        # Warm-up
        s.get('https://www.lottomatica.it/', timeout=10)
        time.sleep(1)
        r = s.get('https://www.lottomatica.it/lotterie/lotto/risultati-delle-estrazioni', timeout=15)
        if r.status_code != 200:
            print(f"  lottomatica: HTTP {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, 'lxml')
        # Cerca data
        date = None
        for tag in soup.find_all(['time','span','div','p']):
            t = tag.get_text(strip=True)
            d = parse_date(t)
            if d:
                date = d
                break
        # Cerca JSON nel sorgente (Next.js / React)
        json_match = re.search(r'"draws"\s*:\s*(\[.*?\])', r.text, re.S)
        if json_match:
            try:
                arr = json.loads(json_match.group(1))
                for item in arr:
                    d = parse_date(item.get('date',''))
                    ruota = normalize_ruota(item.get('wheel',''))
                    nums = item.get('numbers') or item.get('nums', [])
                    if d and ruota and is_valid_nums(nums):
                        draws.append({'date': d, 'concorso': item.get('draw', 0),
                                      'ruota': ruota, 'nums': nums})
            except: pass
        if not draws and date:
            # Cerca numeri vicino ai nomi delle ruote
            for ruota in RUOTE:
                el = soup.find(string=re.compile(ruota, re.I))
                if not el: continue
                parent = el.parent
                for _ in range(5):
                    if not parent: break
                    nums_found = re.findall(r'\b([1-9]|[1-8]\d|90)\b', parent.get_text())
                    if len(nums_found) >= 5:
                        try:
                            nums = [int(n) for n in nums_found[:5]]
                            if is_valid_nums(nums):
                                draws.append({'date': date, 'concorso': 0,
                                              'ruota': ruota, 'nums': nums})
                        except: pass
                        break
                    parent = parent.parent
        print(f"  lottomatica: {len(draws)} estrazioni")
    except Exception as e:
        print(f"  lottomatica errore: {e}")
    return draws

# ── FONTE 4: ADM GOV.IT ──────────────────────────────────────────────────────

def fetch_adm():
    """ADM (governo italiano) — cerca dati strutturati"""
    draws = []
    try:
        s = make_session()
        r = s.get('https://www.adm.gov.it/portale/monopoli/giochi/gioco-del-lotto/risultati-delle-estrazioni',
                  timeout=15)
        if r.status_code != 200:
            print(f"  ADM: HTTP {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, 'lxml')
        # Cerca tabelle
        for table in soup.find_all('table'):
            for tr in table.find_all('tr'):
                tds = [td.get_text(strip=True) for td in tr.find_all(['td','th'])]
                if len(tds) < 7: continue
                date = parse_date(tds[0])
                if not date: continue
                ruota = normalize_ruota(tds[2] if len(tds) > 2 else tds[1])
                if not ruota: continue
                start = 3 if len(tds) > 7 else 2
                try:
                    nums = [int(tds[i]) for i in range(start, start+5)]
                    if is_valid_nums(nums):
                        draws.append({'date': date, 'concorso': 0, 'ruota': ruota, 'nums': nums})
                except: continue
        print(f"  ADM: {len(draws)} estrazioni")
    except Exception as e:
        print(f"  ADM errore: {e}")
    return draws

# ── FONTE 5: LOTTOCASA / WINLOT / ALTRI ──────────────────────────────────────

def fetch_other():
    """Fonti minori — parsing generico"""
    draws = []
    urls = [
        'https://www.lottocasa.it/estrazioni-lotto-oggi/',
        'https://www.winlot.it/estrazioni-lotto/',
        'https://estrazioni-lotto.it/',
        'https://www.lottopiù.it/',
    ]
    for url in urls:
        try:
            s = make_session()
            r = s.get(url, timeout=12)
            if r.status_code != 200: continue
            text = r.text
            if 'Napoli' not in text and 'napoli' not in text: continue
            soup = BeautifulSoup(text, 'lxml')
            # Data
            date = None
            for m in re.finditer(r'(\d{2}/\d{2}/\d{4})', text):
                date = m.group(1)
                break
            if not date: continue
            # Concorso
            conc = 0
            mc = re.search(r'concorso\s+(?:n[°.]?\s*)?(\d+)', text, re.I)
            if mc: conc = int(mc.group(1))
            # Ruote
            for ruota in RUOTE:
                el = soup.find(string=re.compile(r'\b' + ruota + r'\b', re.I))
                if not el: continue
                parent = el.parent
                for _ in range(6):
                    if not parent: break
                    nums_found = re.findall(r'\b([1-9]|[1-8]\d|90)\b', parent.get_text())
                    if len(nums_found) >= 5:
                        try:
                            nums = [int(n) for n in nums_found[:5]]
                            if is_valid_nums(nums):
                                draws.append({'date': date, 'concorso': conc,
                                              'ruota': ruota, 'nums': nums})
                        except: pass
                        break
                    parent = parent.parent
            if draws:
                print(f"  other ({url}): {len(draws)} estrazioni")
                return draws
        except Exception as e:
            print(f"  {url}: {e}")
    return draws

# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print(f"=== Aggiornamento Lotto {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")
    existing = load_existing()
    old_draws = existing.get('draws', [])
    seen = set(f"{d['date']}|{d['ruota']}" for d in old_draws)

    new_draws = []
    sources = [
        ('iltrovatore',   fetch_iltrovatore),
        ('lottomatica',   fetch_lottomatica),
        ('estrazionelotto', fetch_estrazionelotto),
        ('adm',           fetch_adm),
        ('other',         fetch_other),
    ]

    errors = []
    for name, fn in sources:
        print(f"\n→ Tentativo: {name}")
        try:
            result = fn()
            if result and len(result) >= 10:  # almeno 10 ruote
                new_draws = result
                print(f"✅ Fonte OK: {name} ({len(result)} righe)")
                break
            elif result:
                print(f"⚠️ Fonte parziale: {name} ({len(result)} righe)")
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"❌ {name}: {e}")

    if not new_draws:
        print("\n❌ NESSUNA FONTE — dati invariati")
        existing['last_update'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        existing['status'] = 'Aggiornamento fallito - nessuna fonte disponibile. Errori: ' + '; '.join(errors)
        save(existing)
        return

    # Aggiunge solo le estrazioni non ancora presenti
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
        'status': f'OK - {len(added)} nuove estrazioni ({len(all_draws)} totali)',
        'total': len(all_draws)
    }
    save(result)
    print(f"\n=== FINE: +{len(added)} nuove, {len(all_draws)} totali ===")

if __name__ == '__main__':
    main()
