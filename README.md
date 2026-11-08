<h1 align="center">cronsay</h1>

<p align="center">
  <b>Say what a cron expression actually means — and when it next fires.</b>
</p>

<p align="center">
  <a href="https://github.com/Viltrumlik/cronsay/actions/workflows/ci.yml"><img src="https://github.com/Viltrumlik/cronsay/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero dependencies">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT"></a>
</p>

`*/15 9-17 * * 1-5` is not hard, exactly. It is just easy enough to get wrong at 2am — and wrong by a factor of sixty is a popular way to get it wrong.

```console
$ cronsay "*/15 9-17 * * 1-5"
Every 15 minutes, between 09:00 and 17:59, Monday through Friday
next: Mon 10 Nov 09:00, 09:15, 09:30
```

The next run times are the point. A description can look right and still be wrong; three real timestamps are hard to misread.

## The trap it will save you from

```console
$ cronsay "0 0 1 * 1"
At 00:00, on the 1st or Monday (whichever comes first)
next: Mon 30 Nov 00:00, Tue 01 Dec 00:00, Mon 07 Dec 00:00
```

Most people read that as *"the 1st of the month, if it's a Monday"*. Cron reads it as **or**: when day-of-month and day-of-week are both restricted, either one fires it. A monthly job quietly becomes a weekly one.

## What it understands

| | |
|---|---|
| `*` `5` `1-5` `*/15` `0-30/10` `1,15,42` | the usual |
| `JAN`–`DEC`, `SUN`–`SAT` | names, any case |
| `@daily` `@hourly` `@weekly` `@monthly` `@yearly` | shorthand |
| `0` and `7` for Sunday | both, as most crons do |

`@reboot` is refused with an explanation — it is not a schedule.

```bash
cronsay "0 9 * * 1-5"            # quoted
cronsay 0 9 '*' '*' 1-5          # or not
cronsay "@monthly" --next 6
cronsay "0 2 * * *" --next 0     # description only
```

Exit codes: `0` ok · `2` the expression does not parse.

## Install

```bash
pipx install git+https://github.com/Viltrumlik/cronsay
```

Or take the file — one script, no dependencies:

```bash
curl -O https://raw.githubusercontent.com/Viltrumlik/cronsay/main/cronsay.py
python3 cronsay.py "0 9 * * 1-5"
```

## Development

```bash
python3 -m unittest discover -s tests -v
```

34 tests, including the day-of-month/day-of-week **or** rule, leap years (`0 0 29 2 *` lands on 2028 and 2032) and dates that never happen (`0 0 30 2 *`). CI runs on Ubuntu, macOS and Windows with Python 3.9 through 3.13.

## License

[MIT](LICENSE) © Alisher Muhammadaliyev ([@Viltrumlik](https://github.com/Viltrumlik))
