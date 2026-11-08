"""Protocol regression tests moved out of Home Assistant."""

from datetime import date
from unittest.mock import patch

import aiohttp

from pyelternportal.client import PortalClient


async def test_portal_parsing_links() -> None:
    """Download-Links von Briefen und Nachrichten-Anhänge werden erkannt."""
    from pyelternportal.student import Student

    async with aiohttp.ClientSession() as s:
        p = PortalClient(s, "demo", "", "")
        p._student = Student("1", "Max Muster (6c)")
        html = (
            "<table><tr><td>#7</td><td id='empf_77'>Empfang noch nicht bestätigt.</td></tr>"
            "<tr><td colspan='2'><a href='aktuelles/get_file/?repo=77&csrf=abc' onclick='eb_bestaetigung(77);' "
            "class='link_nachrichten' target='_blank'><h4>Wandertag</h4> 30.09.2026 12:01</a>"
            "<br /><span style='font-size: 8pt;'>Klasse/n: 6c</span><br />Bitte Rückmeldung.</td></tr></table>"
        )
        await p.async_letter_parse(html)
        assert p._letter_links == {"77": "aktuelles/get_file/?repo=77&csrf=abc"}
        assert p._student.letters[0].new is True
        detail = (
            '<div class="ui grid" id="message-thread-grid">'
            '<div class="row"><div><strong>Betreff:</strong></div><div><strong>Schulaufgabe</strong></div></div>'
            '<div class="row"><div><strong>Frau Huber:</strong><br/>(30.09.2026)</div>'
            '<div><div class="ui segment">Anbei die Ergebnisse.<br/>'
            '<a href="meldungen/get_file/?f=55&amp;csrf=x">Ergebnis.pdf</a></div></div></div></div>'
        )
        subj, body, atts = p._parse_message_detail(detail)
        assert subj == "Schulaufgabe"
        assert "Anbei die Ergebnisse" in body and "Frau Huber" in body
        assert atts[0].name == "Ergebnis.pdf" and "f=55" in atts[0].href


async def test_portal_parsing_timetable_substitutions() -> None:
    """Stundenplan mit Uhrzeiten, Vertretungsplan mit Entfall, Raumänderung, altem Fach."""
    from pyelternportal.client import parse_substitutions, parse_timetable
    from pyelternportal.demo import DEMO_HTML_LESSON

    plan = parse_timetable(DEMO_HTML_LESSON)
    first = plan[0]
    assert first == {
        "weekday": 1,
        "lesson": "1",
        "start": "08:10",
        "end": "08:55",
        "subject": "Ku",
        "room": "OG2_24",
    }
    assert {x["weekday"] for x in plan} == {1, 2, 3, 4, 5}
    res = parse_substitutions(_SUBST_HTML.format(d0="05.10.2026", d1="06.10.2026"))
    assert res["available"] and len(res["days"]) == 2
    e1, e2, e3 = res["days"][0]["entries"]
    assert (
        e1["subject"] == "D" and e1["old_subject"] == "M" and e1["kind"] == "vertretung"
    )
    assert e2["lesson"] == "5-6"
    assert e2["kind"] == "entfall"
    assert e3["kind"] == "raum"
    assert res["days"][1] == {"date": "2026-10-06", "entries": []}
    assert parse_substitutions("<html><body>Login</body></html>")["available"] is False


def test_clean_appointment_title() -> None:
    """Termintitel mit Uhrzeit kommen als HTML aus dem Portal (#24)."""
    from pyelternportal.client import clean_appointment_title

    assert clean_appointment_title("14:00 - 16:00<br />5: Lernwerkstatt") == (
        "5: Lernwerkstatt",
        "14:00",
        "16:00",
    )
    assert clean_appointment_title("8:30 - 9:15<br>Elternabend<br>") == (
        "Elternabend",
        "08:30",
        "09:15",
    )
    assert clean_appointment_title("19.00 Uhr<br/>Info &amp; Austausch") == (
        "Info & Austausch",
        "19:00",
        None,
    )
    assert clean_appointment_title("Wandertag<br />Klassen 5–7") == (
        "Wandertag Klassen 5–7",
        None,
        None,
    )
    assert clean_appointment_title("<b>SA</b> in Deutsch (Mü)") == (
        "SA in Deutsch (Mü)",
        None,
        None,
    )
    assert clean_appointment_title("SA in Deutsch (Mü)") == (
        "SA in Deutsch (Mü)",
        None,
        None,
    )
    assert clean_appointment_title("8.30 Uhr Gottesdienst") == (
        "8.30 Uhr Gottesdienst",
        None,
        None,
    )
    assert clean_appointment_title("25:00 - 26:00<br />Ungültig") == (
        "25:00 - 26:00 Ungültig",
        None,
        None,
    )
    assert clean_appointment_title(None) == ("", None, None)
    # Datum mit Punkt ist keine Uhrzeit, mit „Uhr“ oder als Spanne schon
    assert clean_appointment_title("12.10<br />Wandertag") == (
        "12.10 Wandertag",
        None,
        None,
    )
    assert clean_appointment_title("8.30 - 9.15<br />Elternsprechtag") == (
        "Elternsprechtag",
        "08:30",
        "09:15",
    )
    # Maskierte Tags und echtes „<“ als Zeichen
    assert clean_appointment_title("Info &lt;b&gt;neu&lt;/b&gt;") == (
        "Info neu",
        None,
        None,
    )
    assert clean_appointment_title("Nachschrift bei Note &lt; 3") == (
        "Nachschrift bei Note < 3",
        None,
        None,
    )
    # Erneutes Bereinigen ändert nichts (gespeicherte Titel)
    for raw in (
        "14:00 - 16:00<br />A &amp; B",
        "Info &lt;b&gt;neu&lt;/b&gt;",
        "Note &lt; 3",
        "12.10<br />Wandertag",
    ):
        once = clean_appointment_title(raw)[0]
        assert clean_appointment_title(once)[0] == once


def test_parse_teachers() -> None:
    """Stundenplankürzel aus den Schulinformationen; Seite ohne Abschnitt -> None."""
    from pyelternportal.client import parse_teachers

    assert parse_teachers(_TEACHERS_HTML) == {
        "Kurz": "Karla Kurzweil",
        "Lang": "Lena Lang-Weilig",
    }
    assert parse_teachers("<div id='asam_content'><h3>Wer macht Was</h3></div>") is None
    table = "<h3>Stundenplankürzel der Lehrkräfte</h3><table><tr><th>Kürzel</th><th>Name</th></tr><tr><td>Mü</td><td>Maria Müller</td></tr></table>"
    assert parse_teachers(table) == {"Mü": "Maria Müller"}


def test_parse_substitutions_five_and_six_columns() -> None:
    """Vertretungsplan mit 5 Spalten (ohne Fach) und mit 6 Spalten (Fach durchgestrichen)."""
    from pyelternportal.client import parse_substitutions

    five = """<div id="asam_content"><div class='main_center'>
      <div class='list bold full_width text_center'>Di., 29.09.2026 - KW 40</div>
      <table class='table'>
        <tr class='vp_plan_head'><td>Std.</td><td>Betrifft.</td><td>Vertretung</td><td>Raum</td><td>Info</td></tr>
        <tr class='liste_grau'><td>3.</td><td>Bz</td><td>Sf</td><td>B003</td><td>Vertretung</td></tr>
        <tr class='liste_weiss'><td>5.</td><td>Mü</td><td>&nbsp;</td><td></td><td>entfällt</td></tr>
      </table></div></div>"""
    days = parse_substitutions(five)["days"]
    assert [d["date"] for d in days] == ["2026-09-29"]
    first, second = days[0]["entries"]
    assert first == {
        "lesson": "3",
        "teacher": "Bz",
        "substitute": "Sf",
        "subject": "",
        "old_subject": None,
        "room": "B003",
        "info": "Vertretung",
        "kind": "vertretung",
    }
    assert second["kind"] == "entfall" and second["room"] == ""

    six = """<div id="asam_content"><div class='main_center'>
      <div class='list bold full_width text_center'>Mi., 07.10.2026 - KW 41</div>
      <table class='table'>
        <tr class='vp_plan_head'><td>Std.</td><td>Betrifft.</td><td>Vertretung</td><td>Fach</td><td>Raum</td><td>Info</td></tr>
        <tr class=''><td colspan='6'>Keine Vertretungen für 8b</td></tr>
      </table>
      <div class='list bold full_width text_center'>Do., 08.10.2026 - KW 41</div>
      <table class='table'>
        <tr class='vp_plan_head'><td>Std.</td><td>Betrifft.</td><td>Vertretung</td><td>Fach</td><td>Raum</td><td>Info</td></tr>
        <tr class='liste_grau'><td>1.</td><td>Abc</td><td>&nbsp;</td><td>C</td><td>1</td><td>entfällt</td></tr>
        <tr class='liste_grau'><td>3.</td><td>Abc</td><td>Xyz</td>
          <td><span style='text-decoration: line-through;'>&nbsp;M&nbsp;</span> PuG</td><td>2</td><td>verlegt</td></tr>
      </table></div></div>"""
    days = parse_substitutions(six)["days"]
    assert [d["date"] for d in days] == ["2026-10-07", "2026-10-08"]
    assert days[0]["entries"] == []
    cancel, moved = days[1]["entries"]
    assert cancel["subject"] == "C" and cancel["kind"] == "entfall"
    assert (
        moved["subject"] == "PuG"
        and moved["old_subject"] == "M"
        and moved["substitute"] == "Xyz"
    )


async def test_blackboard_rich_text_and_attachments() -> None:
    """Text und mehrere Anhänge funktionieren unabhängig von ihrer Position."""
    from pyelternportal.client import _stable_id
    from pyelternportal.student import Student

    today = date.today()
    stamp = today.strftime("%d.%m.%Y")
    async with aiohttp.ClientSession() as session:
        portal = PortalClient(session, "demo", "", "")
        portal._student = Student("1", "Anna Muster (6c)")
        markup = f"""<div id="asam_content"><div class="grid"><div class="grid-item"><div class="well">
          <p>eingestellt am {stamp} 08:00:00</p><h4>Nachrichten der Schulleitung</h4>
          <div><p>Liebe Eltern,<br>bitte beachten Sie:</p><p>Der Elternabend beginnt um 19 Uhr.</p></div>
          <div>Anhänge: <a href="aktuelles/get_file/?repo=17&amp;csrf=first">Info.pdf</a>
          <a href="aktuelles/get_file/?repo=18&amp;csrf=first" title="Programm.pdf herunterladen">📎</a>
          <a href="aktuelles/get_file/?repo=17&amp;csrf=first">Info.pdf</a></div>
          <a href="https://example.org/info">Weitere Informationen</a>
          <script>doNotIncludeThis()</script>
        </div></div></div></div>"""
        await portal.async_blackboard_parse(markup)
        item = portal._collect_items()[0]
        assert item.uid == portal._uid(
            "schwarzes_brett", _stable_id(today, "Nachrichten der Schulleitung")
        )
        assert "Liebe Eltern,\nbitte beachten Sie:" in item.body
        assert "Der Elternabend beginnt um 19 Uhr." in item.body
        assert "Weitere Informationen" in item.body
        assert "doNotIncludeThis" not in item.body and "eingestellt am" not in item.body
        assert len(item.attachments) == 2
        assert item.attachments[0].name == "Info.pdf"
        await portal.async_blackboard_parse(markup.replace("csrf=first", "csrf=second"))
        assert portal._collect_items()[0].version == item.version
        await portal.async_blackboard_parse(markup.replace("repo=17", "repo=19"))
        assert portal._collect_items()[0].version != item.version
        # Die erkannten Anhänge gehen durch denselben Sitzungs-Download wie Elternbriefe.
        from unittest.mock import AsyncMock

        pdf = b"%PDF-1.4 synthetic attachment payload"
        response = AsyncMock()
        response.status = 200
        response.headers = {"Content-Type": "application/pdf"}
        response.content_length = len(pdf)
        response.read.return_value = pdf
        context = AsyncMock()
        context.__aenter__.return_value = response
        with patch.object(session, "get", return_value=context) as request:
            await portal._download_item(item)
        assert request.call_count == 2 and len(item.files) == 2
        assert all(
            f.content == pdf and f.content_type == "application/pdf" for f in item.files
        )
        await portal.async_blackboard_parse('<div id="asam_content"></div>')
        assert not portal._collect_items()  # keine Aushänge vom vorigen Kind übernehmen


async def test_blackboard_original_layout_and_missing_date() -> None:
    from pyelternportal.demo import DEMO_HTML_BLACKBOARD
    from pyelternportal.student import Student

    async with aiohttp.ClientSession() as session:
        portal = PortalClient(session, "demo", "", "")
        portal._student = Student("1", "Anna Muster (6c)")
        await portal.async_blackboard_parse(DEMO_HTML_BLACKBOARD)
        item = portal._collect_items()[0]
        assert item.body == "Medienpädagogik"
        assert len(item.attachments) == 1
        await portal.async_blackboard_parse("""<div id="asam_content"><div class="grid"><div class="grid-item">
          <div class="well"><h4>Ohne Datum</h4><div>Wichtiger Text</div></div>
          <div class="well"><p>eingestellt am 01.01.2000 00:00:00</p><h4>Alt</h4><p>Archiv</p></div>
        </div></div></div>""")
        assert len(portal._collect_items()) == 1
        assert portal._collect_items()[0].sent is None
        assert portal._collect_items()[0].body == "Wichtiger Text"


async def test_timetable_regular_teachers_from_child_table() -> None:
    """Use personal course memberships, without guessing intensive teachers."""
    from pyelternportal.client import parse_timetable

    html = """<div id="asam_content"><div class="table-responsive"><table>
      <tr><td>1.<br>08.00 - 08.45</td>
        <td><span><span>M<br>N115</span></span></td>
        <td>L/F<br>226/227</td><td>PhÜ/ChÜ<br>037/207</td>
        <td>MInt<br>N115</td><td>Unbekannt<br>123</td></tr>
      <tr><td>2.<br>08.45 - 09.30</td><td>Sm/Sw<br>TH/TH</td>
        <td>NuT<br>N115</td><td></td><td></td><td></td></tr>
    </table></div><table>
      <tr><td colspan="2"><b>Lehrkräfte von Anna Beispiel</b></td></tr>
      <tr><td colspan="2"><b>Ganze Klasse</b></td></tr>
      <tr><td>Mathematik</td><td>Maria Muster</td></tr>
      <tr><td>Latein</td><td>Lena Lang</td></tr>
      <tr><td>Französisch</td><td>Fritz Frei</td></tr>
      <tr><td>Sport</td><td>Sara Sommer</td></tr>
      <tr><td>Sport</td><td>Stefan Sport</td></tr>
      <tr><td>Natur und Technik</td><td>Nora Natur</td></tr>
      <tr><td>Natur und Technik</td><td>Ingo Info</td></tr>
      <tr><td colspan="2"><b>Geteilte Klassen</b></td></tr>
      <tr><td>8_L_8AB_LAN, Latein</td><td>Lena Lang</td></tr>
      <tr><td>8_PhÜ_8AB_KUR, Physik</td><td>Paul Probe</td></tr>
      <tr><td>8_ChÜ_8AB_CHE, Chemie</td><td>Clara Chemie</td></tr>
      <tr><td colspan="2"><b>Schülergruppen</b></td></tr>
      <tr><td>MInt</td><td>Falsche Zuordnung</td></tr>
    </table></div>"""
    plan = {(x["weekday"], x["lesson"]): x for x in parse_timetable(html)}
    assert plan[1, "1"]["teacher"] == "Maria Muster"
    assert plan[2, "1"]["teacher"] == "Lena Lang"
    assert plan[3, "1"]["teacher"] == "Paul Probe, Clara Chemie"
    assert "teacher" not in plan[4, "1"]  # no base-subject inference for MInt
    assert "teacher" not in plan[5, "1"]
    assert "teacher" not in plan[1, "2"]  # ambiguous whole-class sports list
    assert "teacher" not in plan[2, "2"]  # two teachers for the same subject
    # Exact course codes do support intensive lessons when supplied by the portal.
    html = html.replace("8_L_8AB_LAN, Latein", "8_MInt_8AB_LAN, Mathematik")
    plan = {(x["weekday"], x["lesson"]): x for x in parse_timetable(html)}
    assert plan[4, "1"]["teacher"] == "Lena Lang"
    assert plan[1, "1"]["teacher"] == "Maria Muster"
    # Without the child table, retain the original timetable fields unchanged.
    assert all(
        "teacher" not in x
        for x in parse_timetable(
            html.split("</table></div>")[0] + "</table></div></div>"
        )
    )


async def test_timetable_course_codes_resolve_teacher_initials() -> None:
    from pyelternportal.client import parse_timetable

    html = """<div id="asam_content"><div class="table-responsive"><table>
    <tr><td>1.<br>08.00 - 08.45</td><td>Inf<br>A1</td><td>NuT<br>A2</td><td></td><td></td><td></td></tr>
    </table></div><table>
    <tr><td colspan="2"><b>Lehrkräfte von Beispiel</b></td></tr>
    <tr><td colspan="2">Ganze Klasse</td></tr>
    <tr><td>Natur und Technik</td><td>Karla Kurz</td></tr>
    <tr><td>Natur und Technik</td><td>K. Kurz</td></tr>
    <tr><td colspan="2">Geteilte Klassen</td></tr>
    <tr><td>6_NuTBio_6A_KUR, Natur und Technik</td><td>Karla Kurz</td></tr>
    <tr><td>6_NuTInf_6A_KUR, Natur und Technik</td><td>K. Kurz</td></tr>
    </table></div>"""
    assert [l["teacher"] for l in parse_timetable(html)] == ["Karla Kurz", "Karla Kurz"]
    html = html.replace("6_NuTInf_6A_KUR", "6_NuTInf_6A_AND")
    assert [l["teacher"] for l in parse_timetable(html)] == ["K. Kurz", "Karla Kurz"]


_SUBST_HTML = """
<div id="asam_content"><div class="main_center">
<div class="list bold full_width text_center">Mo., {d0} - KW 41</div>
<table class="table"><tbody>
<tr class="vp_plan_head"><td>Std.</td><td>Betrifft</td><td>Vertretung</td><td>Fach</td><td>Raum</td><td>Info</td></tr>
<tr><td>3.</td><td>Huber</td><td>Maier</td><td><span style="text-decoration: line-through;">&nbsp;M&nbsp;</span> D</td><td>104</td><td></td></tr>
<tr><td>5.-6.</td><td>Huber</td><td>---</td><td>E</td><td></td><td>entfällt</td></tr>
<tr><td>2.</td><td>Kurz</td><td></td><td>B</td><td>N12</td><td>Raumänderung</td></tr>
</tbody></table>
<div class="list bold full_width text_center">Di., {d1} - KW 41</div>
<table class="table"><tbody>
<tr class="vp_plan_head"><td>Std.</td><td>Betrifft</td><td>Vertretung</td><td>Fach</td><td>Raum</td><td>Info</td></tr>
<tr><td colspan="6">Keine Vertretungen</td></tr>
</tbody></table>
<div>Stand: 05.10.2026 07:15</div>
</div></div>
"""


_TEACHERS_HTML = """<div id="asam_content">
<div class="row m_bot"><div class="col-md-4"></div><div class="col-md-8"><h3>Wer macht Was</h3></div></div>
<div class="row m_bot"><div class="col-md-4"><b>Schulkürzel</b></div><div class="col-md-6">BSP</div></div>
<div class="row m_bot"><div class="col-md-4"></div><div class="col-md-8"><h3>Stundenplankürzel der Lehrkräfte</h3></div></div>
<div class="row m_bot"><div class="col-md-4"><div class="text-right hidden-xs hidden-sm"><b>Kurz</b></div><div class="hidden-md hidden-lg"><b>Kurz</b></div></div><div class="col-md-6">Karla   Kurzweil</div></div>
<div class="row m_bot"><div class="col-md-4"><div class="text-right hidden-xs hidden-sm"><b>Lang</b></div><div class="hidden-md hidden-lg"><b>Lang</b></div></div><div class="col-md-6">Lena Lang-Weilig</div></div>
<div class="row m_bot"><div class="col-md-4"></div><div class="col-md-8"><h3>Sonstiges</h3></div></div>
<div class="row m_bot"><div class="col-md-4"><b>X</b></div><div class="col-md-6">gehört nicht dazu</div></div>
</div>"""
