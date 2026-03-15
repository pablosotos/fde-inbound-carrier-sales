import csv
from pathlib import Path
from typing import List, Optional
from .models import Load

DATA_FILE = Path(__file__).resolve().parent.parent / "loads.csv"

def load_all() -> List[Load]:
    loads = []
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["loadboard_rate"] = float(row["loadboard_rate"])
            row["weight"] = float(row["weight"])
            row["num_of_pieces"] = int(row["num_of_pieces"])
            row["miles"] = float(row["miles"])
            loads.append(Load(**row))
    return loads

def search_loads(origin: Optional[str] = None,
                 destination: Optional[str] = None,
                 equipment_type: Optional[str] = None) -> List[Load]:
    loads = load_all()
    results = []
    for load in loads:
        if origin and load.origin.lower() != origin.lower():
            continue
        if destination and load.destination.lower() != destination.lower():
            continue
        if equipment_type and load.equipment_type.lower() != equipment_type.lower():
            continue
        results.append(load)
    return results
