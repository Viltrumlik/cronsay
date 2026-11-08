#!/usr/bin/env python3
"""cronsay - say what a cron expression actually means.

`*/15 9-17 * * 1-5` is not hard, exactly. It is just easy enough to get
wrong at 2am, and wrong by a factor of sixty is a common way to get it
wrong.

    $ cronsay "*/15 9-17 * * 1-5"
    Every 15 minutes, between 09:00 and 17:59, Monday through Friday
    next: Mon 10 Nov 09:00, 09:15, 09:30

Exit codes: 0 ok, 2 the expression does not parse.

Zero dependencies. Python 3.9+.
"""

import argparse
import datetime as dt
import sys

VERSION = "0.1.0"
EXIT_OK, EXIT_USAGE = 0, 2

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday"]

SHORTHAND = {
    "@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *", "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *", "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

# (nom, eng kichik, eng katta, nomlar)
FIELDS = [
    ("minute", 0, 59, None),
    ("hour", 0, 23, None),
    ("day of month", 1, 31, None),
    ("month", 1, 12, MONTHS),
    ("day of week", 0, 7, DAYS),     # 7 ham yakshanba, ko'p cron'larda shunday
]


class CronError(ValueError):
    pass


class Field:
    def __init__(self, name, values, star, step=None):
        self.name = name
        self.values = values       # saralangan ro'yxat
        self.star = star           # "*" edimi (qadamsiz)
        self.step = step           # */n bo'lsa n


# ---------------------------------------------------------------- parsing


def parse_part(part, low, high, names, name):
    """Bitta bo'lak: *, a, a-b, */n, a-b/n, yoki ularning vergulli ro'yxati."""
    step = 1
    body = part
    if "/" in part:
        body, _, raw_step = part.partition("/")
        if not raw_step.isdigit() or int(raw_step) == 0:
            raise CronError("%s: qadam noto'g'ri: %r" % (name, part))
        step = int(raw_step)

    if body == "*":
        start, end = low, high
    elif "-" in body.lstrip("-"):
        a, _, b = body.partition("-")
        start, end = to_number(a, low, high, names, name), to_number(b, low, high, names, name)
        if start > end:
            raise CronError("%s: oraliq teskari: %r" % (name, part))
    else:
        start = end = to_number(body, low, high, names, name)
        if step > 1:
            end = high        # "5/10" ko'p cron'larda "5-max/10" degani

    return list(range(start, end + 1, step)), body == "*", (step if step > 1 else None)


def to_number(text, low, high, names, name):
    text = text.strip().upper()
    if names and text in names:
        return names.index(text) + (1 if names is MONTHS else 0)
    if not text.lstrip("-").isdigit():
        raise CronError("%s: son emas: %r" % (name, text))
    value = int(text)
    if not low <= value <= high:
        raise CronError("%s: %d oraliqdan tashqarida (%d-%d)" % (name, value, low, high))
    return value


def parse_field(text, low, high, names, name):
    values, star, step = set(), True, None
    for part in text.split(","):
        part = part.strip()
        if not part:
            raise CronError("%s: bo'sh bo'lak" % name)
        got, is_star, got_step = parse_part(part, low, high, names, name)
        values.update(got)
        star = star and is_star
        step = step or got_step
    if not values:
        raise CronError("%s: hech narsa tanlanmadi" % name)
    return Field(name, sorted(values), star and step is None, step)


def parse(expression):
    text = expression.strip()
    if text.lower() == "@reboot":
        raise CronError("@reboot vaqt jadvali emas: u har safar yuklanishda ishlaydi")
    text = SHORTHAND.get(text.lower(), text)
    parts = text.split()
    if len(parts) != 5:
        raise CronError("5 ta maydon kutilgan, %d ta berildi" % len(parts))
    fields = []
    for part, (name, low, high, names) in zip(parts, FIELDS):
        fields.append(parse_field(part, low, high, names, name))
    # Yakshanba 0 va 7 -- ikkalasini bitta qiymatga keltiramiz.
    dow = fields[4]
    if 7 in dow.values:
        dow.values = sorted(set(dow.values) - {7} | {0})
    return fields


# ---------------------------------------------------------------- describing


def join(items, last="and"):
    items = list(items)
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return "%s %s %s" % (items[0], last, items[1])
    return "%s %s %s" % (", ".join(items[:-1]), last, items[-1])


def is_run(values, low, high):
    """Qiymatlar uzluksiz oraliqmi va to'liq emasmi."""
    return (len(values) > 1 and values == list(range(values[0], values[-1] + 1))
            and not (values[0] == low and values[-1] == high))


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def describe_time(minute, hour):
    if minute.step and minute.star is False and hour.star:
        head = "Every %d minutes" % minute.step
    elif minute.step:
        head = "Every %d minutes" % minute.step
    elif len(minute.values) == 1 and len(hour.values) == 1:
        return "At %02d:%02d" % (hour.values[0], minute.values[0])
    elif len(minute.values) == 1 and hour.star:
        return "At %d minutes past every hour" % minute.values[0]
    elif len(minute.values) == 1:
        head = "At %d minutes past" % minute.values[0]
    else:
        head = "At %s minutes past" % join([str(m) for m in minute.values])

    if hour.star:
        return head if head.startswith("Every") else head + " every hour"
    if hour.step:
        if len(minute.values) == 1:
            at = ("on the hour" if minute.values[0] == 0
                  else "at minute %d" % minute.values[0])
            return "Every %d hours, %s" % (hour.step, at)
        return "%s, every %d hours" % (head, hour.step)
    if is_run(hour.values, 0, 23):
        return "%s, between %02d:00 and %02d:59" % (head, hour.values[0], hour.values[-1])
    return "%s, at %s" % (head, join(["%02d:00" % h for h in hour.values]))


def describe_days(dom, dow):
    day_phrase = week_phrase = None
    if not dom.star:
        day_phrase = ("every %d days" % dom.step if dom.step
                      else "the " + join([ordinal(d) for d in dom.values]))
    if not dow.star:
        names = [DAY_NAMES[d] for d in dow.values]
        week_phrase = ("%s through %s" % (names[0], names[-1])
                       if is_run(dow.values, 0, 6) else join(names))

    if day_phrase and week_phrase:
        # Cron'ning mashhur tuzog'i: ikkala maydon ham cheklangan bo'lsa,
        # ular VA emas, YOKI bilan birlashadi.
        return "on %s or %s (whichever comes first)" % (day_phrase, week_phrase)
    if day_phrase:
        return "on " + day_phrase
    return week_phrase or ""


def describe(fields):
    minute, hour, dom, month, dow = fields
    parts = [describe_time(minute, hour)]
    days = describe_days(dom, dow)
    if days:
        parts.append(days)
    if not month.star:
        names = [MONTH_NAMES[m - 1] for m in month.values]
        if is_run(month.values, 1, 12):
            parts.append("from %s through %s" % (names[0], names[-1]))
        else:
            parts.append("in " + join(names))
    return ", ".join(parts)


# ---------------------------------------------------------------- next runs


def matches_day(date, dom, month, dow):
    if date.month not in month.values:
        return False
    day_ok = date.day in dom.values
    # datetime: dushanba 0; cron: yakshanba 0
    week_ok = ((date.weekday() + 1) % 7) in dow.values
    if dom.star and dow.star:
        return True
    if dom.star:
        return week_ok
    if dow.star:
        return day_ok
    return day_ok or week_ok


# Sakkiz yil: 29-fevral jadvali uchun kamida ikkita kabisa yili kerak,
# aks holda uchta vaqt so'ralganda bittasi qaytadi.
HORIZON_DAYS = 366 * 8


def next_runs(fields, start, count=3, horizon_days=HORIZON_DAYS):
    minute, hour, dom, month, dow = fields
    runs = []
    date = start.date()
    for _ in range(horizon_days + 1):
        if matches_day(date, dom, month, dow):
            for h in hour.values:
                for m in minute.values:
                    when = dt.datetime(date.year, date.month, date.day, h, m)
                    if when > start:
                        runs.append(when)
                        if len(runs) == count:
                            return runs
        date += dt.timedelta(days=1)
    return runs


# ---------------------------------------------------------------- cli


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="cronsay",
        description="Cron ifodasini oddiy so'z bilan tushuntiradi.",
        epilog='misol: cronsay "*/15 9-17 * * 1-5" --next 5')
    p.add_argument("expression", nargs="+", metavar="IFODA")
    p.add_argument("--next", type=int, default=3, metavar="N",
                   help="keyingi N ishga tushishni ko'rsatish (0 -- ko'rsatilmasin)")
    p.add_argument("--version", action="version", version="cronsay " + VERSION)
    args = p.parse_args(argv)

    expression = " ".join(args.expression)
    try:
        fields = parse(expression)
    except CronError as e:
        print("xato: %s" % e, file=sys.stderr)
        return EXIT_USAGE

    print(describe(fields))
    if args.next > 0:
        runs = next_runs(fields, dt.datetime.now(), args.next)
        if not runs:
            print("next: hech qachon (bunday sana mavjud emas, masalan 30 fevral)")
        else:
            shown, last_date = [], None
            for run in runs:
                if run.date() != last_date:
                    shown.append(run.strftime("%a %d %b %H:%M"))
                    last_date = run.date()
                else:
                    shown.append(run.strftime("%H:%M"))
            print("next: " + ", ".join(shown))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
