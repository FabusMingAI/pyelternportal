"""Parse the optional course-registration page without submitting forms."""

import re

import bs4


def parse_course_registrations(
    html: str, parser: str = "html.parser"
) -> list[str] | None:
    """None means unavailable/unrecognized, [] means explicitly no registrations."""
    soup = bs4.BeautifulSoup(html, parser)
    if not any(
        "Voranmeldung Intensivierungskurse" in h.get_text(" ", strip=True)
        for h in soup.find_all("h2")
    ):
        return None
    text = soup.get_text(" ", strip=True)
    courses = [h.get_text(" ", strip=True) for h in soup.select("h4.link_buchungen")]
    if "Für folgende Intensivierungskurse besteht eine Anmeldung" in text and courses:
        return list(dict.fromkeys(courses))
    if soup.find("form"):
        return None
    if re.search(
        r"(?:keine Anmeldungen|keine Anmeldung|nicht angemeldet|keine Intensivierungskurse)",
        text,
        re.IGNORECASE,
    ):
        return []
    return None  # An open booking form is not a complete participation list.
