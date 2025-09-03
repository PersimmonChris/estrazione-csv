import json
import csv
from pathlib import Path

MAX_LEVELS = 3
STRIP_TOKENS = {"Root", "Home"}

def normalize_path(cat: str) -> str | None:
    """Normalize a single category path string to max 3 levels.
    - Split on '|', trim spaces for each segment
    - Drop empty segments and tokens like 'Root'/'Home'
    - Truncate to MAX_LEVELS
    - Return None if nothing remains
    """
    if not isinstance(cat, str):
        return None
    parts = [p.strip() for p in cat.split('|')]
    parts = [p for p in parts if p and p not in STRIP_TOKENS]
    if not parts:
        return None
    if len(parts) > MAX_LEVELS:
        parts = parts[:MAX_LEVELS]
    return '|'.join(parts)

def read_categories_from_csv(path: str) -> list[str]:
    """Read Categories_IT column from a ; separated CSV without requiring pandas."""
    cats: list[str] = []
    with open(path, 'r', encoding='utf-8', newline='') as f:
        sniffer = csv.Sniffer()
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.excel
        dialect.delimiter = ';'
        # If the sample detects header, ok; otherwise assume header present as provided
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            val = row.get('Categories_IT')
            if val is not None:
                cats.append(val)
    return cats


def estrai_categorie_uniche():
    # Percorso del file CSV
    file_csv = 'jollysoftair.csv'
    
    # Verifica che il file esista
    if not Path(file_csv).exists():
        print("❌ File CSV non trovato!")
        print("Assicurati che jollysoftair.csv sia nella stessa cartella")
        return
    
    try:
        # Leggi solo la colonna Categories_IT
        print("📖 Lettura del file CSV...")
        valori = read_categories_from_csv(file_csv)
        
        # Estrai valori univoci
        print("🔍 Estrazione valori unici e normalizzazione...")
        # Unici come lista
        valori_univoci = list(dict.fromkeys(str(v) for v in valori if v is not None))

        anomalie = []
        out_set: set[str] = set()
        for raw in valori_univoci:
            raw_stripped = raw.strip()
            if not raw_stripped:
                continue
            # Check and collect anomalies (> MAX_LEVELS levels)
            raw_parts = [p.strip() for p in raw_stripped.split('|') if p.strip()]
            if len(raw_parts) > MAX_LEVELS:
                anomalie.append(raw_stripped)
            norm = normalize_path(raw_stripped)
            if norm:
                out_set.add(norm)

        valori_puliti = sorted(out_set)

        # Salva in JSON
        with open('categorie_uniche.json', 'w', encoding='utf-8') as f:
            json.dump(valori_puliti, f, ensure_ascii=False, indent=2)

        print(f"✅ Fatto! Trovate {len(valori_puliti)} categorie uniche normalizzate (max {MAX_LEVELS} livelli)")
        print("📁 File salvato come: categorie_uniche.json")
        
        # Mostra anteprima
        print("\n📋 Anteprima prime 10 categorie:")
        for i, cat in enumerate(valori_puliti[:10]):
            print(f"  {i+1}. {cat}")

        if anomalie:
            print(f"\n⚠️  Rilevate {len(anomalie)} voci con più di {MAX_LEVELS} livelli nel CSV (mostro le prime 10):")
            for a in anomalie[:10]:
                print(f"   - {a}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    estrai_categorie_uniche()
