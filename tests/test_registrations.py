from pyelternportal.registrations import parse_course_registrations


def test_registrations_distinguish_unavailable_from_empty():
    head = "<header><h2>Example school</h2></header><h2>Voranmeldung Intensivierungskurse</h2>"
    assert parse_course_registrations("<h2>Login</h2>") is None
    assert parse_course_registrations(head + "<form>Bitte anmelden</form>") is None
    assert parse_course_registrations(head + "<p>Keine Anmeldungen vorhanden</p>") == []
    html = (
        head
        + '<p>Für folgende Intensivierungskurse besteht eine Anmeldung:</p><h4 class="link_buchungen">Int_M_6a</h4>'
    )
    assert parse_course_registrations(html) == ["Int_M_6a"]
