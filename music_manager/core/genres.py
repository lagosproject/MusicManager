from typing import Optional

GENRE_MAPPING = {
    "Reggaeton": ["reggaeton", "urbano latino", "trap latino", "perreo", "latin hip hop"],
    "Salsa": ["salsa", "timba", "guaguanco", "son montuno"],
    "Bachata": ["bachata", "dominican pop"],
    "Merengue": ["merengue", "dominican pop"]
}

def detect_genre_from_title(title: str) -> Optional[str]:
    """Detects if the title explicitly mentions a genre version."""
    if not title:
        return None
    t = title.lower()
    for genre in GENRE_MAPPING.keys():
        g = genre.lower()
        # Patterns like "Salsa Version", "Versión Salsa", "En Salsa", "Salsa Edit"
        if f"{g} version" in t or f"versión {g}" in t or f"en {g}" in t or f"{g} remix" in t:
            return genre
    return None
