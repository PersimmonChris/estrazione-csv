import argparse
import csv
import re
from pathlib import Path
from typing import Iterable


DEFAULT_BLACKLIST = [
    "Katane", "Armeria", "Spade", "Home", "Pugnali", "Balestre",
    "Mattoncini Sluban", "Modellini Militari", "Pistole a salve",
    "Accessori Archi / Balestre", "DARDI", "FRECCE", "Archi",
    "Coltelli butterfly", "Coltelli tascabili", "Coltelli caccia/survival",
    "Coltelli lama fissa", "COMBO PACK", "CUSTOM UPGRADE",
    "Coltelli da lancio", "Multitool / Forbici Trauma", "ANFIBI/SCARPE",
    "INTIMO TERMICO", "ASSEMBLATI", "CUSTOM ESTETICA", "Vip Club",
    "Gift Card Addon no delete", "Caricatori a salve", "Collimatori",
    "TACHYON - STATUS", "Armi/spray peperoncino", "NIKK SAKK CUSTOM",
    "Biglie per fionda", "PERFECT ROSSI", "FUCILI E PISTOLE USATI",
    "STARTER KIT", "SGW CUSTOM", "USATO", "FUCILI ELETTRICI ECO",
]


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def load_blacklist(blist: Iterable[str]) -> set[str]:
    normed = set()
    for b in blist:
        b = str(b).strip()
        if not b:
            continue
        normed.add(normalize(b))
    return normed


def read_header(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f, delimiter=";")
        for row in r:
            if not row or all(not str(c).strip() for c in row):
                continue
            return [c.strip() for c in row]
    return []


def count_non_blacklisted_rows(csv_path: Path, column: str, blacklist: set[str]):
    header = read_header(csv_path)
    if not header:
        raise ValueError("Intestazione non trovata nel CSV")
    if column not in header:
        raise ValueError(f"Colonna '{column}' non trovata. Disponibili: {header}")
    idx = header.index(column)

    total = 0
    blacklisted = 0
    empty_or_missing = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f, delimiter=";")
        # Skip to first non-empty row (header already consumed by read_header)
        header_consumed = False
        for row in r:
            if not row or all(not str(c).strip() for c in row):
                continue
            header_consumed = True
            break
        # Iterate remaining rows
        for row in r:
            # skip empty lines
            if not row or all(not str(c).strip() for c in row):
                continue
            total += 1
            if idx >= len(row):
                empty_or_missing += 1
                continue
            cat_raw = row[idx]
            cat = str(cat_raw).strip()
            if not cat:
                empty_or_missing += 1
                continue
            if normalize(cat) in blacklist:
                blacklisted += 1

    non_blacklisted = total - blacklisted
    return {
        "total_rows": total,
        "blacklisted_rows": blacklisted,
        "non_blacklisted_rows": non_blacklisted,
        "empty_or_missing_categoria": empty_or_missing,
    }


def main():
    ap = argparse.ArgumentParser(description="Conta righe non in blacklist per la colonna 'Categoria'")
    ap.add_argument("csv_path", type=Path, help="Percorso al CSV (delimitatore ';')")
    ap.add_argument("--col", dest="col", default="Categoria", help="Nome colonna (default: Categoria)")
    ap.add_argument("--blacklist-file", type=Path, help="File con categorie blacklist (una per riga)")
    args = ap.parse_args()

    bl = list(DEFAULT_BLACKLIST)
    if args.blacklist_file:
        if not args.blacklist_file.exists():
            raise FileNotFoundError(f"Blacklist file non trovato: {args.blacklist_file}")
        extra = [l.strip() for l in args.blacklist_file.read_text(encoding="utf-8").splitlines()]
        bl.extend([e for e in extra if e])
    bl_set = load_blacklist(bl)

    stats = count_non_blacklisted_rows(args.csv_path, args.col, bl_set)

    total = stats["total_rows"]
    blk = stats["blacklisted_rows"]
    kept = stats["non_blacklisted_rows"]
    missing = stats["empty_or_missing_categoria"]
    pct_blk = (blk / total * 100) if total else 0.0
    pct_keep = (kept / total * 100) if total else 0.0

    print(f"Totale righe (escl. header): {total}")
    print(f"In blacklist: {blk} ({pct_blk:.1f}%)")
    print(f"Non in blacklist: {kept} ({pct_keep:.1f}%)")
    if missing:
        print(f"Categoria mancante/vuota: {missing}")


if __name__ == "__main__":
    main()

