import datetime

from apps.legal.service import msa_today

UTC = datetime.timezone.utc


def test_msa_day_rolls_over_at_3am_eastern():
    # Winter (EST, UTC-5): 3am Eastern is 08:00 UTC
    assert msa_today(datetime.datetime(2026, 12, 12, 7, 59, tzinfo=UTC)) == datetime.date(2026, 12, 11)
    assert msa_today(datetime.datetime(2026, 12, 12, 8, 0, tzinfo=UTC)) == datetime.date(2026, 12, 12)
    # Summer (EDT, UTC-4): 3am Eastern is 07:00 UTC
    assert msa_today(datetime.datetime(2026, 7, 12, 6, 59, tzinfo=UTC)) == datetime.date(2026, 7, 11)
    assert msa_today(datetime.datetime(2026, 7, 12, 7, 0, tzinfo=UTC)) == datetime.date(2026, 7, 12)
