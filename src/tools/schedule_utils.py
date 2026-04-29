from __future__ import annotations
import os
import re
from datetime import datetime, date, timedelta
from typing import Optional


def try_parse_ics(ics_text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    vevents = re.split(r"END:VEVENT", ics_text, flags=re.IGNORECASE)
    for block in vevents:
        if "BEGIN:VEVENT" not in block.upper():
            continue
        ev = block + "END:VEVENT"
        def extract(tag: str) -> Optional[str]:
            m = re.search(rf"{tag}:(.+)", ev)
            return m.group(1).strip() if m else None

        dtstart = extract("DTSTART")
        dtend = extract("DTEND")
        summary = extract("SUMMARY") or "(无标题)"
        location = extract("LOCATION") or ""

        def norm(dt: Optional[str]) -> Optional[str]:
            if not dt:
                return None
            s = dt.strip()
            s = s.replace("Z", "+00:00")
            for fmt in ("%Y%m%dT%H%M%S%z", "%Y%m%dT%H%M%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(s, fmt).isoformat()
                except Exception:
                    continue
            return s

        # handle RRULE (simple weekly BYDAY) expansion
        rrule = extract_rrule(ev)
        if rrule:
            # compute occurrences within horizon
            try:
                base = None
                if dtstart:
                    from datetime import datetime as _dt

                    for fmt in ("%Y%m%dT%H%M%S%z", "%Y%m%dT%H%M%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                        try:
                            base = _dt.strptime(dtstart, fmt)
                            break
                        except Exception:
                            continue
                if base is None:
                    # fallback: keep original
                    events.append({"start": norm(dtstart), "end": norm(dtend), "summary": summary, "location": location})
                else:
                    horizon_days = int(os.getenv("SCHEDULE_RRULE_HORIZON_DAYS", "3650"))
                    occs = expand_rrule(base, rrule, days_horizon=horizon_days)
                    dur = None
                    if dtend:
                        try:
                            end_dt = None
                            for fmt in ("%Y%m%dT%H%M%S%z", "%Y%m%dT%H%M%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                                try:
                                    end_dt = _dt.strptime(dtend, fmt)
                                    break
                                except Exception:
                                    continue
                            if end_dt is not None:
                                dur = end_dt - base
                        except Exception:
                            dur = None
                    for oc in occs:
                        st = oc.isoformat()
                        ed = (oc + dur).isoformat() if dur else None
                        events.append({"start": st, "end": ed, "summary": summary, "location": location})
            except Exception:
                events.append({"start": norm(dtstart), "end": norm(dtend), "summary": summary, "location": location})
        else:
            events.append({"start": norm(dtstart), "end": norm(dtend), "summary": summary, "location": location})
    return events


def extract_rrule(block: str) -> str | None:
    m = re.search(r"RRULE:(.+)", block, flags=re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip()


def expand_rrule(dtstart, rrule_str: str, days_horizon: int = 120):
    # Very small RRULE support: FREQ=WEEKLY;BYDAY=MO,TU
    parts = {p.split("=")[0].upper(): p.split("=")[1] for p in rrule_str.split(";") if "=" in p}
    freq = parts.get("FREQ", "").upper()
    byday = parts.get("BYDAY", "").split(",") if parts.get("BYDAY") else []
    until = parts.get("UNTIL")
    # map BYDAY tokens to isoweekday (1=Mon..7=Sun)
    map_day = {"MO":1,"TU":2,"WE":3,"TH":4,"FR":5,"SA":6,"SU":7}
    target_weekdays = [map_day.get(x.upper()) for x in byday if x]
    from datetime import timedelta, datetime

    # Compute stopping date (if UNTIL exists) to avoid expanding forever.
    until_dt = None
    if until:
        # UNTIL is commonly formatted as YYYYMMDD[T]HHMMSS[Z]
        s = until.strip().replace("Z", "+00:00")
        # Try a couple of common patterns; if timezone mismatch happens it's fine to ignore UNTIL.
        for fmt in ("%Y%m%dT%H%M%S%z", "%Y%m%dT%H%M%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
            try:
                until_dt = datetime.strptime(s, fmt)
                break
            except Exception:
                continue

    results = []
    if freq == "WEEKLY" and target_weekdays:
        horizon_date = dtstart + timedelta(days=days_horizon)
        if until_dt is not None:
            # If UNTIL parse succeeded, pick the earlier of the two bounds.
            try:
                # Avoid naive/aware datetime comparison errors.
                if getattr(dtstart, "tzinfo", None) is None and getattr(until_dt, "tzinfo", None) is not None:
                    until_dt = until_dt.replace(tzinfo=None)
                elif getattr(dtstart, "tzinfo", None) is not None and getattr(until_dt, "tzinfo", None) is None:
                    until_dt = until_dt.replace(tzinfo=dtstart.tzinfo)
                horizon_date = min(horizon_date, until_dt)
            except Exception:
                pass
        cur = dtstart
        # iterate days until horizon
        while cur <= horizon_date:
            if cur.isoweekday() in target_weekdays and cur >= dtstart:
                results.append(cur)
            cur = cur + timedelta(days=1)
    else:
        # fallback: only DTSTART
        results.append(dtstart)
    return results


def parse_events_from_text(text: str) -> list[dict[str, str]]:
    text = text.strip()
    # Common case: plain ICS text.
    if text.upper().startswith("BEGIN:VCALENDAR"):
        return try_parse_ics(text)
    # Some share pages wrap the ICS inside HTML/extra text; extract the first VCALENDAR block.
    m = re.search(r"BEGIN:VCALENDAR[\s\S]*?END:VCALENDAR", text, flags=re.IGNORECASE)
    if m:
        return try_parse_ics(m.group(0))
    try:
        import json
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            # Be tolerant to wrappers.
            for key in ("events", "schedule", "items", "data"):
                val = obj.get(key)
                if isinstance(val, list):
                    return val
    except Exception:
        pass
    return []


def parse_date_expression(text: str) -> Optional[date]:
    s = text.strip().lower()
    today = date.today()
    if s in ("今天", "今日"):
        return today
    if s in ("明天",):
        return today + timedelta(days=1)
    if s in ("后天",):
        return today + timedelta(days=2)

    m = re.search(r"(周|星期)([一二三四五六日天1234567])", s)
    if m:
        w = m.group(2)
        map_cn = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"日":7,"天":7}
        if w.isdigit():
            target_w = int(w)
            if target_w == 7:
                target_w = 7
        else:
            target_w = map_cn.get(w, None)
        if target_w:
            today_w = today.isoweekday()
            days_ahead = (target_w - today_w) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)
    # full numeric date formats: YYYY-MM-DD or YYYY.MM.DD or YYYY/MM/DD
    m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", s)
    if m:
        y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, da)
        except Exception:
            return None

    # month-day formats like '3月5日' or '3.5' or '3/5' or '3.5号'
    m = re.search(r"(\d{1,2})月(\d{1,2})日", s)
    if not m:
        m = re.search(r"(\d{1,2})[.\-/](\d{1,2})(?:号)?", s)
    if m:
        mo, da = int(m.group(1)), int(m.group(2))
        y = today.year
        try:
            # Prefer the date in the current year for month-day queries
            d = date(y, mo, da)
            return d
        except Exception:
            return None

    return None


def format_events_for_date(events: list[dict[str,str]], target: date) -> list[str]:
    lines: list[str] = []
    from datetime import datetime
    for ev in events:
        start = ev.get("start")
        if not start:
            continue
        try:
            dt = datetime.fromisoformat(start)
        except Exception:
            try:
                dt = datetime.fromisoformat(start.split("+")[0])
            except Exception:
                continue
        if dt.date() == target:
            time_str = dt.strftime("%H:%M")
            lines.append(f"{time_str} {ev.get('summary')} {ev.get('location','')}")
    return sorted(lines)


__all__ = ["try_parse_ics", "parse_events_from_text", "parse_date_expression", "format_events_for_date"]
