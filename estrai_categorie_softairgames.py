import csv
from pathlib import Path
from typing import Iterable


def read_unique_categories(path: Path, column: str = "Categoria") -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    seen = set()
    order: list[str] = []
    # Handle BOM and leading blank lines robustly
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter=';')
        header: list[str] | None = None
        for row in reader:
            # Skip completely empty rows
            if not row or all(not str(cell).strip() for cell in row):
                continue
            header = [h.strip() for h in row]
            break
        if not header:
            raise ValueError("Intestazione non trovata nel CSV (file vuoto?)")
        if column not in header:
            raise ValueError(
                f"Colonna '{column}' non trovata. Disponibili: {header}"
            )
        idx = header.index(column)
        for row in reader:
            if not row:
                continue
            # Ensure row has enough columns
            if idx >= len(row):
                continue
            raw = row[idx]
            val = str(raw).strip()
            if not val:
                continue
            if val not in seen:
                seen.add(val)
                order.append(val)
    return order


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Estrai elenco unico di categorie dalla colonna 'Categoria'")
    ap.add_argument("csv_path", type=Path, help="Percorso al CSV con delimitatore ';'")
    ap.add_argument("--col", dest="col", default="Categoria", help="Nome della colonna categorie (default: Categoria)")
    args = ap.parse_args()

    cats = read_unique_categories(args.csv_path, args.col)
    for c in cats:
        print(c)


if __name__ == "__main__":
    main()
