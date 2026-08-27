"""
parse_user_inputs.sorting
==========================
Gemeinsame Sortier- und Deduplizierungs-Utilities.

Hash-basierte Deduplizierung mit:
  - MD5-Hash fuer exakte Duplikate
  - Shingling (k-Gramme) fuer Fuzzy-Matching
  - Jaccard-Aehnlichkeit fuer nahezu gleiche Eintraege
  - SimHash fuer grosse Textmengen
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime


def parse_date(s: str) -> datetime:
    """
    Parst Datumsstring zu datetime fuer robuste Sortierung.
    Unterstuetzt:
      - "%Y-%m-%d %H:%M"
      - "%Y-%m-%dT%H:%M:%S"
      - "%Y-%m-%dT%H:%M:%S.%f"
      - beliebige Strings mit fuehrendem Datumsteil
    """
    if not s or s == "?":
        return datetime.min

    # Direkt versuchen
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s[:len(fmt) + 5], fmt)
        except (ValueError, TypeError):
            continue

    # Substring-Suche: Datum am Anfang
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    return datetime.min


def sort_key_multi(item: dict) -> tuple:
    """
    Mehrstufiger Sortier-Key:
      1. Datum (praezise, neueste zuerst = negiert)
      2. Plattform (alphabetisch)
      3. Inhaltslaenge (laengste zuerst)
    """
    dt = parse_date(item.get("date", ""))
    platform = item.get("platform", item.get("source", ""))
    content_len = len(item.get("content", ""))

    return (
        dt,              # primär: Datum (aufsteigend -> neueste am Ende)
        platform,        # sekundär: Plattform alphabetisch
        -content_len,    # tertiär: Laengste Inputs zuerst (negiert)
    )


def merge_and_dedup(*input_lists: list[dict]) -> list[dict]:
    """
    Merged mehrere Input-Listen und dedupliziert.

    3-Stufen-Deduplizierung:
      1. MD5-Hash des normalisierten Inhalts (exakt)
      2. Shingle-Set fuer Jaccard-Aehnlichkeit (fuzzy)
      3. Session + erste 50 Zeichen (Fallback)

    Sortierung: Mehrstufig (Datum -> Plattform -> Laenge).
    """
    seen_hashes: set[str] = set()
    shingle_bands: dict[str, list[str]] = {}  # band -> [hash]
    unique: list[dict] = []

    for inp_list in input_lists:
        for inp in inp_list:
            content = inp.get("content", "")
            session = inp.get("session", "")

            if not content or len(content) < 5:
                continue

            # Stufe 1: Exakter MD5-Hash
            normalized = _normalize_for_hash(content)
            md5 = hashlib.md5(normalized.encode("utf-8")).hexdigest()
            if md5 in seen_hashes:
                continue

            # Stufe 2: Shingle-basierte Fuzzy-Deduplizierung
            if len(content) >= 20:
                is_fuzzy_dup = _check_fuzzy_duplicate(
                    content, shingle_bands, threshold=0.6
                )
                if is_fuzzy_dup:
                    continue

            # Stufe 3: Session + First-Chars Fallback
            # (fuer sehr kurze Inputs wo Shingles nicht funktionieren)
            if len(content) < 20:
                short_key = f"{session}:{normalized[:50]}"
                if short_key in seen_hashes:
                    continue
                seen_hashes.add(short_key)

            seen_hashes.add(md5)
            unique.append(inp)

    # Mehrstufig sortieren
    unique.sort(key=sort_key_multi)

    return unique


# ─── Hash-Funktionen ─────────────────────────────────────────────────────────

def _normalize_for_hash(text: str) -> str:
    """
    Normalisiert Text fuer exakten Hash-Vergleich.
    Entfernt Whitespace-Variationen, Gross/Klein, Sonderzeichen.
    """
    t = text.lower().strip()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r' +', ' ', t)
    return t


def _get_shingles(text: str, k: int = 3) -> set[str]:
    """
    Erzeugt k-Gramm-Shingles aus dem normalisierten Text.
    Shingles sind die Grundlage fuer Jaccard-Aehnlichkeit.
    """
    normalized = _normalize_for_hash(text)
    if len(normalized) < k:
        return {normalized}
    return {normalized[i:i+k] for i in range(len(normalized) - k + 1)}


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """
    Berechnet Jaccard-Aehnlichkeit zwischen zwei Shingle-Sets.
    0.0 = komplett verschieden, 1.0 = identisch.
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _simhash(shingles: set[str], bits: int = 64) -> int:
    """
    SimHash fuer schnelle Fingerprint-Vergleiche.
    Kompresse Darstellung eines Shingle-Sets als Bit-Vektor.
    """
    v = [0] * bits
    for shingle in shingles:
        h = int(hashlib.md5(shingle.encode("utf-8")).hexdigest(), 16)
        for i in range(bits):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(bits):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def _hamming_distance(hash_a: int, hash_b: int) -> int:
    """Berechnet Hamming-Distanz zwischen zwei Bit-Fingerprints."""
    return bin(hash_a ^ hash_b).count('1')


def _check_fuzzy_duplicate(
    content: str,
    shingle_bands: dict[str, list[str]],
    threshold: float = 0.6,
) -> bool:
    """
    Prueft ob ein Content ein fuzzy-Duplikat ist.

    Multi-Band LSH Strategie:
      1. SimHash berechnen
      2. In 4 verschiedene Bands listen (Multi-Probe)
      3. Hamming-Distanz mit Kandidaten pruefen
      4. Bei geringer Anzahl: Gegen ALLE gespeicherten Hashes pruefen
    """
    shingles = _get_shingles(content)
    if len(shingles) < 3:
        return False

    simhash = _simhash(shingles)

    # Multi-Band: 4 verschiedene Bands fuer bessere Trefferquote
    candidate_hashes = set()
    for shift in [0, 8, 16, 24]:
        band = str((simhash >> shift) % 256)
        if band in shingle_bands:
            candidate_hashes.update(shingle_bands[band])

    # Falls weniger als 50 Kandidaten: gegen ALLE Hashes pruefen
    if len(candidate_hashes) < 50:
        for hashes in shingle_bands.values():
            candidate_hashes.update(hashes)

    for candidate_hash in candidate_hashes:
        dist = _hamming_distance(simhash, candidate_hash)
        if dist <= 10:
            return True

    # In ALLE Bands speichern (Multi-Probe)
    for shift in [0, 8, 16, 24]:
        band = str((simhash >> shift) % 256)
        if band not in shingle_bands:
            shingle_bands[band] = []
        if simhash not in shingle_bands[band]:
            shingle_bands[band].append(simhash)

    # Band-Size begrenzen (Performance)
    for band in shingle_bands:
        if len(shingle_bands[band]) > 100:
            shingle_bands[band] = shingle_bands[band][-50:]

    return False


def sort_threads(threads: list, key: str = "date") -> list:
    """
    Sortiert Thread-Objekte nach dem angegebenen Schluessel.
    Unterstuetzt: "date", "platform", "title", "message_count".
    """
    def thread_sort_key(t):
        if key == "date":
            return parse_date(t.date)
        elif key == "platform":
            return (parse_date(t.date), t.platform)
        elif key == "title":
            return (parse_date(t.date), t.title.lower())
        elif key == "message_count":
            return (parse_date(t.date), -t.message_count)
        return parse_date(t.date)

    return sorted(threads, key=thread_sort_key)
