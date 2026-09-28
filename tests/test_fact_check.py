from app.profile.fact_check import BLOCK, WARN, check_text, verified_numbers


def rules(result):
    return {(v.severity, v.rule) for v in result.violations}


def test_verified_text_passes(profile):
    text = ("Head of Design Management since 2022, responsible for 12 residential projects "
            "totalling 90,000+ sqm in Riyadh, aligned with Vision 2030. Previously led a team of 8 engineers.")
    result = check_text(text, profile)
    assert result.passed, result.violations
    assert not result.violations


def test_invented_number_is_blocked(profile):
    result = check_text("Delivered 25 projects across the Kingdom.", profile)
    assert not result.passed
    assert (BLOCK, "unverified_number") in rules(result)


def test_private_numbers_are_not_whitelisted(profile):
    numbers = verified_numbers(profile)
    assert "7777" not in numbers and "9999" not in numbers and "1234" not in numbers
    assert "90000" in numbers and "2022" in numbers


def test_currency_and_money_are_blocked(profile):
    result = check_text("Managed a portfolio worth SAR 60 million.", profile)
    assert (BLOCK, "financial_data") in rules(result)
    assert check_text("Budget of $5M", profile).passed is False
    assert check_text("قيمة المشروع 5 ريال", profile).passed is False


def test_financial_metric_with_number_blocks_without_number_warns(profile):
    assert (BLOCK, "financial_metric") in rules(check_text("Achieved an IRR of 18%.", profile))
    soft = check_text("I take an ROI-aware approach to design.", profile)
    assert soft.passed
    assert (WARN, "financial_metric") in rules(soft)


def test_forbidden_phrase_is_blocked(profile):
    result = check_text("Served as design director for the portfolio.", profile)
    assert (BLOCK, "forbidden_phrase") in rules(result)


def test_unheld_credential_is_blocked(profile):
    assert (BLOCK, "unverified_credential") in rules(check_text("An experienced PMP professional.", profile))
    assert (BLOCK, "unverified_credential") in rules(check_text("Holds an MBA from a leading school.", profile))
    assert check_text("Completed a Project Management Diploma.", profile).passed


def test_allowed_standard_names(profile):
    assert check_text("Works to ISO 19650 and Vision 2030 goals.", profile).passed
