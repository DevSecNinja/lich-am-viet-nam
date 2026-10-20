# Vietnamese Lunar Calendar

[Vietnamese](README.md) | English

A minimalist Vietnamese lunar calendar for Google Calendar, Apple Calendar and
Outlook. Subscribe in your existing calendar app without installing another app.

- Daily lunar dates, first days of lunar months, full moons and major holidays.
- English event titles, descriptions, calendar name and calendar description.
- A rolling calendar from the current year through ten years ahead, inclusive.
- Automatic annual regeneration, with separate English and Vietnamese feeds.
- Free and open source under the [MIT License](LICENSE).

## Subscribe

Open the [English subscription file](output/viet_lunar_en_latest.ics), select
**Raw**, and copy the resulting URL into your calendar app. The raw URL identifies
the repository and branch you are viewing: when trying this change in a fork,
use that fork's branch, not upstream `main` until the English file is available
there. Keep using the `latest` file rather than a year-specific download for
automatic updates.

The existing Vietnamese subscription is unchanged:

```text
https://raw.githubusercontent.com/cmduyeen/lich-am-viet-nam/main/output/viet_lunar_latest.ics
```

Choose one language to avoid seeing two events for each day. English events have
their own stable identifiers, so they will not overwrite Vietnamese events.

### Set up your calendar app

- **Apple Calendar (iPhone / iPad):** Open Calendar, choose **Calendars**,
  **Add Calendar**, then **Add Subscription Calendar** and paste the URL.
  On older iOS versions, use **Settings > Calendar > Accounts > Add Account >
  Other > Add Subscribed Calendar**.
- **Apple Calendar (Mac):** Choose **File > New Calendar Subscription**, paste
  the URL and select an automatic refresh interval.
- **Google Calendar (Web / Android):** In [Google Calendar](https://calendar.google.com)
  on the web, choose **+** next to **Other calendars**, then **From URL**, and
  paste the URL. Enable the subscribed calendar on your Android device.
- **Outlook on the web:** Choose **Add calendar > Subscribe from web**, paste the
  URL, give the calendar a name and select **Import**.

Subscribe by URL rather than importing a downloaded file: a one-time file import
does not receive future updates. Refresh timing is controlled by your calendar app.

## What the events mean

Titles use **lunar day/month**, not the Gregorian date. Examples:

| Event | English title |
| --- | --- |
| Ordinary lunar day | `Lunar 14/11` |
| First day of a lunar month | `Lunar 1/6` &bull; `First Day of Lunar Month` |
| Full moon day | `Lunar 15/6` &bull; `Full Moon` |
| Lunar New Year | `Lunar 1/1` &bull; `Lunar New Year - Day 1` |
| A day in a leap lunar month | `Lunar 7/6 (leap month)` |

Descriptions translate the traditional stem-and-branch year into
English, for example **Yang Fire Horse year**. Vietnamese zodiac conventions,
including the **Cat** and **Buffalo**, are retained.

The English feed uses the same date calculations, holiday precedence, all-day
event boundaries and colours as the Vietnamese feed. It adds an explicit
**leap month** label to English titles and descriptions; the Vietnamese feed
keeps its existing formatting. This translation does not change the underlying
calendar algorithm or holiday rules.

## Included holidays

### Public holidays

| Holiday | Date |
| --- | --- |
| New Year's Day | January 1, Gregorian calendar |
| Lunar New Year's Eve | Last day of lunar month 12 |
| Lunar New Year - Days 1, 2 and 3 | Days 1-3 of lunar month 1 |
| Hung Kings Commemoration Day | Day 10 of lunar month 3 |
| Reunification Day | April 30, Gregorian calendar |
| International Labour Day | May 1, Gregorian calendar |
| National Day | September 2, Gregorian calendar |

### Traditional festivals

| Festival | Lunar date (day/month) |
| --- | --- |
| Kitchen Gods Day | 23/12 |
| God of Wealth Day | 10/1 |
| First Full Moon Festival | 15/1 |
| Buddha's Birthday | 15/4 |
| Double Fifth Festival | 5/5 |
| Filial Piety Festival | 15/7 |
| Mid-Autumn Festival | 15/8 |

These are the existing calendar's holiday dates, not a complete schedule of
government-announced days off or substitute holidays.

## Generate calendars locally

Use Python 3.11 or newer and install the existing dependencies:

```sh
python -m pip install -r requirements.txt
```

The default remains Vietnamese. Add `--language en` to generate English files
without overwriting Vietnamese files:

```sh
python main.py --split
python main.py --language en --split
python main.py --language en --start 2026 --end 2036
python main.py --language en --year 2027
```

Generation status messages remain in Vietnamese. On Windows terminals that do
not default to UTF-8, set `$env:PYTHONUTF8 = '1'` in PowerShell before running.

English files in `output` are:

- `viet_lunar_en_latest.ics`: rolling subscription feed.
- `viet_lunar_en_<start>_<end>.ics`: combined calendar for the requested years.
- `viet_lunar_en_<year>.ics`: single-year calendar (`--split` or `--year`).
- `viet_lunar_en_yearly_<start>_<end>.zip`: yearly calendars (`--split`, multiple years).

`--year` only writes a single-year file and does not replace the `latest` feed.
`--output-dir` selects a different output directory. Cleanup removes past-year
files only for the selected language and leaves the other language untouched.

The GitHub Actions workflow generates both languages on pushes to `main`, on
January 1 each year and on manual runs. It retains the existing rolling range.
Scheduled workflows may need to be enabled in a fork before automatic updates run.

Run the regression tests with:

```sh
python -m unittest discover -s tests -v
```

## License and attribution

[MIT License](LICENSE). Copyright (c) 2026
[cmduyeen](https://github.com/cmduyeen) - Pinkie Suite.

<p align="center">
  <img src="assets/signature.svg" alt="cmduyeen" width="400" />
</p>
