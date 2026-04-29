import sys
from pathlib import Path
import json
from datetime import datetime, timedelta, date

proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))

from src.tools.schedule_store import ScheduleStore
from src.tools.schedule_utils import parse_events_from_text, format_events_for_date, parse_date_expression


def make_sample_ics(today: date) -> str:
    tomorrow = today + timedelta(days=1)
    t1 = today.strftime("%Y%m%dT090000")
    t2 = tomorrow.strftime("%Y%m%dT140000")
    ics = f"""
BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:{t1}
DTEND:{t1}
SUMMARY:数学
LOCATION:教室A
END:VEVENT
BEGIN:VEVENT
DTSTART:{t2}
DTEND:{t2}
SUMMARY:物理
LOCATION:教室B
END:VEVENT
END:VCALENDAR
"""
    return ics


def main():
    today = date.today()
    ics = make_sample_ics(today)
    events = parse_events_from_text(ics)
    assert len(events) == 2, "parse failed"

    db = ScheduleStore(str(proj_root / 'data' / 'test_schedules.db'))
    db.init_db()
    sid = db.save_schedule('tester', 'sample', events)
    print('saved schedule id', sid)

    evs = db.get_events('tester')
    assert len(evs) >= 2

    lines_today = format_events_for_date(evs, today)
    print('today events:', lines_today)
    assert any('数学' in l for l in lines_today)

    # parse natural language
    d = parse_date_expression('今天')
    assert d == today

    print('All schedule tests passed')


if __name__ == '__main__':
    main()
