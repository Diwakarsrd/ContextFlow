from contextflow.governance.pii import contains_pii, find_pii, redact_pii


def test_detects_email():
    assert contains_pii("contact me at alice@example.com")
    matches = find_pii("contact me at alice@example.com")
    assert any(m.kind == "email" for m in matches)


def test_detects_ssn():
    assert contains_pii("SSN: 123-45-6789")


def test_detects_valid_credit_card_but_not_random_digits():
    # 4111111111111111 is a well-known Luhn-valid test Visa number.
    assert contains_pii("card: 4111 1111 1111 1111")
    # A random 16-digit run that fails the Luhn check should not match.
    assert not contains_pii("order number 1234567812345678")


def test_detects_aws_key():
    assert contains_pii("AKIAABCDEFGHIJKLMNOP")


def test_no_false_positive_on_plain_text():
    assert not contains_pii("The migration is planned for Q4.")


def test_redact_replaces_matches():
    redacted = redact_pii("Email me: alice@example.com please")
    assert "alice@example.com" not in redacted
    assert "[REDACTED:EMAIL]" in redacted
