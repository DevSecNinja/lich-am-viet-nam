import contextlib
from dataclasses import replace
from datetime import date, timedelta
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from icalendar import Calendar

from main import cleanup_past_files, main
from src.config import (
    CALENDAR_DESCRIPTION_EN, CALENDAR_NAME_EN, EARTHLY_BRANCHES_EN,
    HEAVENLY_STEMS_EN, PRODID_EN,
)
from src.holidays import FIXED_LUNAR_HOLIDAYS, FIXED_SOLAR_HOLIDAYS, GIAO_THUA, HolidayInfo
from src.ics_generator import LunarCalendarGenerator, _build_event_for_day
from src.lunar_converter import DIA_CHI, THIEN_CAN, to_lunar


ROOT = Path(__file__).resolve().parents[1]


def without_timestamps(calendar):
    result = Calendar.from_ical(calendar.to_ical())
    for event in result.walk('VEVENT'):
        del event['DTSTAMP']
    return result.to_ical()


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.solar = date(2026, 1, 2)
        self.lunar = to_lunar(self.solar)

    def test_every_holiday_has_english_event_text(self):
        for (month, day), holiday in FIXED_LUNAR_HOLIDAYS.items():
            with self.subTest(holiday=holiday.name_en):
                lunar = replace(self.lunar, lunar_month=month, lunar_day=day)
                self.assert_holiday(self.solar, lunar, holiday)
        for (month, day), holiday in FIXED_SOLAR_HOLIDAYS.items():
            with self.subTest(holiday=holiday.name_en):
                self.assert_holiday(date(2026, month, day), self.lunar, holiday)

    def assert_holiday(self, solar, lunar, holiday):
        with patch('src.ics_generator.is_last_day_of_lunar_month', return_value=False):
            event = _build_event_for_day(solar, lunar, 'en')
        self.assertTrue(str(event['SUMMARY']).endswith(holiday.name_en))
        self.assertIn(f'{holiday.name_en}: {holiday.description_en}', str(event['DESCRIPTION']))
        self.assertTrue(holiday.name_en.isascii())
        self.assertTrue(holiday.description_en.isascii())
        self.assertEqual('X-MICROSOFT-CDO-IMPORTANCE' in event, holiday.is_public_holiday)

    def test_actual_lunar_new_year_and_eve(self):
        for solar, holiday in (
            (date(2026, 2, 16), GIAO_THUA),
            (date(2026, 2, 17), FIXED_LUNAR_HOLIDAYS[(1, 1)]),
        ):
            with self.subTest(date=solar):
                event = _build_event_for_day(solar, to_lunar(solar), 'en')
                self.assertTrue(str(event['SUMMARY']).endswith(holiday.name_en))
                self.assertIn(holiday.description_en, str(event['DESCRIPTION']))

    def test_ordinary_first_and_full_moon_days(self):
        for day, label in ((7, ''), (1, 'First Day of Lunar Month'), (15, 'Full Moon')):
            with self.subTest(day=day):
                lunar = replace(self.lunar, lunar_month=6, lunar_day=day)
                event = _build_event_for_day(self.solar, lunar, 'en')
                expected = f'Lunar {day}/6' + (f' \u2022 {label}' if label else '')
                self.assertEqual(str(event['SUMMARY']), expected)
                self.assertEqual(str(event['DESCRIPTION']), f'Lunar day {day}, month 6 (Yin Wood Snake year)')

    def test_actual_leap_month_markers(self):
        solar = date(2025, 7, 25)
        lunar = to_lunar(solar)
        self.assertTrue(lunar.is_leap_month)
        self.assertEqual(lunar.lunar_month, -6)
        event = _build_event_for_day(solar, lunar, 'en')
        self.assertEqual(str(event['SUMMARY']), 'Lunar 1/6 (leap month) \u2022 First Day of Lunar Month')
        self.assertIn('leap month 6', str(event['DESCRIPTION']))
        self.assertNotIn('(leap month)', str(_build_event_for_day(solar, lunar)['SUMMARY']))

    def test_year_translation_covers_all_stems_and_branches(self):
        self.assertEqual(set(HEAVENLY_STEMS_EN), set(THIEN_CAN.values()))
        self.assertEqual(set(EARTHLY_BRANCHES_EN), set(DIA_CHI.values()))
        for stem, stem_en in HEAVENLY_STEMS_EN.items():
            for branch, branch_en in EARTHLY_BRANCHES_EN.items():
                lunar = replace(self.lunar, can_chi_year=f'{stem} {branch}')
                event = _build_event_for_day(self.solar, lunar, 'en')
                self.assertIn(f'{stem_en} {branch_en} year', str(event['DESCRIPTION']))
        self.assertIn('Cat', EARTHLY_BRANCHES_EN.values())
        self.assertIn('Buffalo', EARTHLY_BRANCHES_EN.values())

    def test_missing_translation_fails_instead_of_publishing_partial_english(self):
        untranslated = {(self.lunar.lunar_month_abs, self.lunar.lunar_day): HolidayInfo('Untranslated')}
        with patch.dict(FIXED_LUNAR_HOLIDAYS, untranslated), \
                patch('src.ics_generator.to_lunar', return_value=self.lunar):
            with self.assertRaisesRegex(RuntimeError, 'Failed to generate English event'):
                LunarCalendarGenerator('en').generate_year(2026)

    def test_invalid_language_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported calendar language'):
            LunarCalendarGenerator('fr')


class FeedRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved_vi = Calendar.from_ical((ROOT / 'output' / 'viet_lunar_latest.ics').read_bytes())
        saved_events = cls.saved_vi.walk('VEVENT')
        cls.start = saved_events[0].decoded('DTSTART')
        cls.end = saved_events[-1].decoded('DTSTART')
        cls.vi = LunarCalendarGenerator().generate_range(cls.start.year, cls.end.year)
        cls.en = LunarCalendarGenerator('en').generate_range(cls.start.year, cls.end.year)

    def test_existing_vietnamese_feed_is_unchanged_except_timestamps(self):
        self.assertEqual(without_timestamps(self.vi), without_timestamps(self.saved_vi))

    def test_dates_styles_and_stable_separate_identifiers(self):
        vi_events = self.vi.walk('VEVENT')
        en_events = self.en.walk('VEVENT')
        self.assertEqual(len(en_events), (self.end - self.start).days + 1)
        self.assertEqual(len(vi_events), len(en_events))
        self.assertEqual(len({str(event['UID']) for event in en_events}), len(en_events))
        for offset, (vi, en) in enumerate(zip(vi_events, en_events)):
            solar = self.start + timedelta(days=offset)
            with self.subTest(date=solar):
                self.assertEqual(en.decoded('DTSTART'), solar)
                self.assertEqual(en.decoded('DTEND'), solar + timedelta(days=1))
                self.assertEqual(str(en['UID']), f'vnlunar-en-{solar:%Y%m%d}@cmduyeen')
                self.assertNotEqual(vi['UID'], en['UID'])
                for key in ('DTSTART', 'DTEND', 'COLOR', 'X-MICROSOFT-CDO-IMPORTANCE'):
                    self.assertEqual(vi.get(key), en.get(key))
                self.assertTrue(str(en['SUMMARY']).startswith('Lunar '))
                self.assertTrue(str(en['SUMMARY']).replace('\u2022', '').isascii())
                self.assertTrue(str(en['DESCRIPTION']).isascii())

    def test_english_metadata_and_published_artifacts(self):
        self.assertEqual(str(self.en['PRODID']), PRODID_EN)
        self.assertEqual(str(self.en['X-WR-CALDESC']), CALENDAR_DESCRIPTION_EN)
        self.assertEqual(str(self.en['X-WR-CALNAME']), f'{CALENDAR_NAME_EN} {self.start.year}\u2013{self.end.year}')
        output = ROOT / 'output'
        latest = (output / 'viet_lunar_en_latest.ics').read_bytes()
        combined = output / f'viet_lunar_en_{self.start.year}_{self.end.year}.ics'
        self.assertEqual(latest, combined.read_bytes())
        self.assertEqual(without_timestamps(Calendar.from_ical(latest)), without_timestamps(self.en))
        archive = output / f'viet_lunar_en_yearly_{self.start.year}_{self.end.year}.zip'
        with zipfile.ZipFile(archive) as zipped:
            expected_names = [f'viet_lunar_en_{year}.ics' for year in range(self.start.year, self.end.year + 1)]
            self.assertEqual(zipped.namelist(), expected_names)
            for year, name in zip(range(self.start.year, self.end.year + 1), expected_names):
                yearly = (output / name).read_bytes()
                self.assertEqual(zipped.read(name), yearly)
                calendar = Calendar.from_ical(yearly)
                self.assertEqual(str(calendar['X-WR-CALNAME']), f'{CALENDAR_NAME_EN} {year}')
                expected = [event for event in self.en.walk('VEVENT') if event.decoded('DTSTART').year == year]
                actual = calendar.walk('VEVENT')
                self.assertEqual(len(actual), len(expected))
                for saved, generated in zip(actual, expected):
                    for key in ('SUMMARY', 'DESCRIPTION', 'DTSTART', 'DTEND', 'UID', 'COLOR'):
                        self.assertEqual(saved[key], generated[key])

    def test_english_icalendar_wire_format(self):
        for path in (ROOT / 'output').glob('viet_lunar_en_*.ics'):
            with self.subTest(file=path.name):
                raw = path.read_bytes()
                self.assertTrue(raw.endswith(b'\r\n'))
                self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
                self.assertTrue(all(len(line) <= 75 for line in raw.split(b'\r\n')))


class CommandLineTests(unittest.TestCase):
    def run_main(self, *arguments):
        with patch('sys.argv', ['main.py', *arguments]), patch('main.HAS_TQDM', False), \
                contextlib.redirect_stdout(io.StringIO()):
            main()

    def test_split_and_single_year_outputs_do_not_overwrite_other_language(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            vi_latest = output / 'viet_lunar_latest.ics'
            vi_latest.write_bytes(b'Existing Vietnamese subscription')
            self.run_main('--language', 'en', '--start', '2026', '--end', '2027', '--split', '--output-dir', directory)
            en_latest = output / 'viet_lunar_en_latest.ics'
            saved_latest = en_latest.read_bytes()
            self.assertEqual(saved_latest, (output / 'viet_lunar_en_2026_2027.ics').read_bytes())
            self.assertEqual(vi_latest.read_bytes(), b'Existing Vietnamese subscription')
            with zipfile.ZipFile(output / 'viet_lunar_en_yearly_2026_2027.zip') as archive:
                self.assertEqual(archive.namelist(), ['viet_lunar_en_2026.ics', 'viet_lunar_en_2027.ics'])
            self.run_main('--language', 'en', '--year', '2028', '--output-dir', directory)
            self.assertEqual(en_latest.read_bytes(), saved_latest)
            self.assertEqual(len(Calendar.from_ical((output / 'viet_lunar_en_2028.ics').read_bytes()).walk('VEVENT')), 366)
            self.run_main('--year', '2028', '--output-dir', directory)
            self.assertTrue((output / 'viet_lunar_2028.ics').is_file())
            self.assertEqual(en_latest.read_bytes(), saved_latest)
            self.assertEqual(vi_latest.read_bytes(), b'Existing Vietnamese subscription')

    def test_cleanup_is_language_specific_and_keeps_latest(self):
        for language, prefix, other_prefix in (
            ('vi', 'viet_lunar', 'viet_lunar_en'),
            ('en', 'viet_lunar_en', 'viet_lunar'),
        ):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                expired = [f'{prefix}_2025.ics', f'{prefix}_2025_2035.ics', f'{prefix}_yearly_2025_2035.zip']
                keep = [f'{prefix}_latest.ics', f'{prefix}_2026.ics', f'{prefix}_2026_2036.ics',
                        f'{prefix}_yearly_2026_2036.zip', f'{other_prefix}_2025.ics',
                        f'{other_prefix}_2025_2035.ics', f'{other_prefix}_yearly_2025_2035.zip', 'notes.txt']
                for name in expired + keep:
                    (output / name).touch()
                self.assertEqual(set(cleanup_past_files(output, 2026, language)), set(expired))
                self.assertEqual({path.name for path in output.iterdir()}, set(keep))

    def test_invalid_language_exits_before_writing(self):
        with patch('sys.argv', ['main.py', '--language', 'fr']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
