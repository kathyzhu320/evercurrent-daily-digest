from dataclasses import replace
import pytest
from src.faithfulness import check_faithfulness


def source(messages, id):
    return next(m for m in messages if m.message_id == id)

@pytest.mark.parametrize('id,summary', [
    ('M005', 'Driver chip MD-4820-X lead time is 12 weeks.'),
    ('M006', 'Driver chip MD-4820-X lead time is 20 weeks.'),
    ('M009', 'Battery BP-2400 rev B at 24V measured 61 C.'),
    ('M012', 'Power board PB-4800 voltage is 24V with firmware v2.1.'),
    ('M028', 'Error code E204 was reproduced with motor driver v2.1.'),
    ('M015', 'Milestone date is 10/29.'),
    ('M025', 'Chassis manufacturing yield is 92%.')])
def test_supported_identifiers_pass(messages, id, summary):
    result = check_faithfulness(summary, (source(messages, id),))
    assert result.ok, result.unsupported
    assert result.checked_count > 0

@pytest.mark.parametrize('id,summary,fragment', [
    ('M005', 'Driver chip MD-4820-X lead time is 21 weeks.', '21weeks'),
    ('M009', 'Battery BP-2400 rev D measured 61 C.', 'REV D'),
    ('M012', 'Power board PB-4999 voltage is 24V.', 'PB-4999'),
    ('M015', 'Milestone date is 10/30.', '10/30'),
    ('M009', 'Battery pack is at 24A.', '24A'),
    ('M025', 'Chassis yield is 97%.', '97%'),
    ('M028', 'Error code E999 was reproduced.', 'E999'),
    ('M025', 'There were 999 rejected parts.', '999')])
def test_unsupported_identifiers_fail(messages, id, summary, fragment):
    result = check_faithfulness(summary, (source(messages, id),))
    assert not result.ok
    assert any(fragment in item for item in result.unsupported)


def test_authorized_scope_not_global_dataset(messages):
    public = source(messages, 'M017')
    private = source(messages, 'M015')
    summary = 'Milestone validation schedule date is 10/29.'
    assert not check_faithfulness(summary, (public,)).ok
    assert check_faithfulness(summary, (public, private)).ok


def test_empty_summary_or_source_fails(messages):
    assert not check_faithfulness('', (source(messages, 'M005'),)).ok
    assert not check_faithfulness('12 weeks', ()).ok
