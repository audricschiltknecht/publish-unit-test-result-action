import contextlib
import locale
import logging
import unittest
from typing import Any

from publish_unit_test_results import as_delta, as_stat_number, as_stat_duration, \
    get_formatted_digits, get_short_summary_md, get_long_summary_md, get_stats, \
    get_stats_with_delta, parse_junit_xml_files, get_test_results


@contextlib.contextmanager
def temp_locale(encoding) -> Any:
    old_locale = locale.getlocale()
    locale.setlocale(locale.LC_ALL, encoding)
    try:
        res = yield
    finally:
        locale.setlocale(locale.LC_ALL, old_locale)
    return res


def n(number, delta=None):
    if delta is None:
        return dict(number=number)
    return dict(number=number, delta=delta)


def d(duration, delta=None):
    if delta is None:
        return dict(duration=duration)
    return dict(duration=duration, delta=delta)


class Test(unittest.TestCase):
    old_locale = None

    @classmethod
    def setUpClass(cls) -> None:
        super(Test, cls).setUpClass()
        cls.old_locale = locale.getlocale()
        logging.info('initial test locale: {}'.format(cls.old_locale))
        locale.setlocale(locale.LC_ALL, (None, None))

    @classmethod
    def tearDownClass(cls) -> None:
        locale.setlocale(locale.LC_ALL, cls.old_locale)
        super(Test, cls).tearDownClass()

    def test_get_formatted_digits(self):
        self.assertEqual(get_formatted_digits(None), (3, 0))
        self.assertEqual(get_formatted_digits(None, 1), (3, 0))
        self.assertEqual(get_formatted_digits(None, 123), (3, 0))
        self.assertEqual(get_formatted_digits(None, 1234), (4, 0))
        self.assertEqual(get_formatted_digits(0), (1, 0))
        self.assertEqual(get_formatted_digits(1, 2, 3), (1, 0))
        self.assertEqual(get_formatted_digits(10), (2, 0))
        self.assertEqual(get_formatted_digits(100), (3, 0))
        self.assertEqual(get_formatted_digits(1234, 123, 0), (4, 0))
        with temp_locale('en_US.utf8'):
            self.assertEqual(get_formatted_digits(1234, 123, 0), (5, 0))
        with temp_locale('de_DE.utf8'):
            self.assertEqual(get_formatted_digits(1234, 123, 0), (5, 0))

        self.assertEqual(get_formatted_digits(dict()), (3, 3))
        self.assertEqual(get_formatted_digits(dict(number=1)), (1, 3))
        self.assertEqual(get_formatted_digits(dict(number=12)), (2, 3))
        self.assertEqual(get_formatted_digits(dict(number=123)), (3, 3))
        self.assertEqual(get_formatted_digits(dict(number=1234)), (4, 3))
        with temp_locale('en_US.utf8'):
            self.assertEqual(get_formatted_digits(dict(number=1234)), (5, 3))
        with temp_locale('de_DE.utf8'):
            self.assertEqual(get_formatted_digits(dict(number=1234)), (5, 3))

        self.assertEqual(get_formatted_digits(dict(delta=1)), (3, 1))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=1)), (1, 1))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=12)), (1, 2))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=123)), (1, 3))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=1234)), (1, 4))
        with temp_locale('en_US.utf8'):
            self.assertEqual(get_formatted_digits(dict(number=1, delta=1234)), (1, 5))
        with temp_locale('de_DE.utf8'):
            self.assertEqual(get_formatted_digits(dict(number=1, delta=1234)), (1, 5))

    def test_get_test_results(self):
        self.assertEqual(get_test_results(dict(cases=[])), dict(
            cases=0, cases_skipped=0, cases_failures=0, cases_errors=0, cases_time=0,
            tests=0, tests_skipped=0, tests_failures=0, tests_errors=0,
        ))
        self.assertEqual(get_test_results(dict(cases=[
            ('class1', 'test1', 'success', 1),
            ('class1', 'test2', 'skipped', 2),
            ('class1', 'test3', 'failure', 3),
            ('class2', 'test1', 'error', 4),
            ('class2', 'test2', 'skipped', 5),
            ('class2', 'test3', 'failure', 6),
            ('class2', 'test4', 'failure', 7),
        ])), dict(
            cases=7, cases_skipped=2, cases_failures=3, cases_errors=1, cases_time=28,
            tests=7, tests_skipped=2, tests_failures=3, tests_errors=1,
        ))
        self.assertEqual(get_test_results(dict(cases=[
            ('class1', 'test1', 'success', 2),
            ('class1', 'test1', 'success', 2),

            # success state has precedence over skipped
            ('class1', 'test2', 'success', 2),
            ('class1', 'test2', 'skipped', 2),

            # only when all runs are skipped, test has state skipped
            ('class1', 'test3', 'skipped', 2),
            ('class1', 'test3', 'skipped', 2),

            ('class1', 'test4', 'success', 2),
            ('class1', 'test4', 'failure', 2),

            ('class1', 'test5', 'success', 2),
            ('class1', 'test5', 'error', 2),
        ])), dict(
            cases=10, cases_skipped=3, cases_failures=1, cases_errors=1, cases_time=20,
            tests=5, tests_skipped=1, tests_failures=1, tests_errors=1,
        ))

    def test_get_stats(self):
        self.assertEqual(get_stats(dict()), dict(
            files=None,
            suites=None,
            duration=None,

            tests=None,
            tests_succ=None,
            tests_skip=None,
            tests_fail=None,
            tests_error=None,

            runs=None,
            runs_succ=None,
            runs_skip=None,
            runs_fail=None,
            runs_error=None
        ))

        self.assertEqual(get_stats(dict(
            suite_tests=20,
            suite_skipped=5,
            suite_failures=None,

            tests=40,
            tests_skipped=10,
            tests_failures=None
        )), dict(
            files=None,
            suites=None,
            duration=None,

            tests=40,
            tests_succ=30,
            tests_skip=10,
            tests_fail=None,
            tests_error=None,

            runs=20,
            runs_succ=15,
            runs_skip=5,
            runs_fail=None,
            runs_error=None
        ))

        self.assertEqual(get_stats(dict(
            files=1,
            suites=2,
            suite_time=3,

            suite_tests=20,
            suite_skipped=5,
            suite_failures=6,
            suite_errors=7,

            tests=30,
            tests_skipped=8,
            tests_failures=9,
            tests_errors=10
        )), dict(
            files=1,
            suites=2,
            duration=3,

            tests=30,
            tests_succ=3,
            tests_skip=8,
            tests_fail=9,
            tests_error=10,

            runs=20,
            runs_succ=2,
            runs_skip=5,
            runs_fail=6,
            runs_error=7
        ))

    def test_get_stats_with_delta(self):
        self.assertEqual(get_stats_with_delta(dict(), dict(), 'type'), dict(
            reference_commit=None,
            reference_type='type'
        ))
        self.assertEqual(get_stats_with_delta(dict(
            files=1,
            suites=2,
            duration=3,

            tests=20,
            tests_succ=2,
            tests_skip=5,
            tests_fail=6,
            tests_error=7,

            runs=40,
            runs_succ=12,
            runs_skip=8,
            runs_fail=9,
            runs_error=10,

            commit='commit'
        ), dict(), 'missing'), dict(
            files=dict(number=1),
            suites=dict(number=2),
            duration=dict(duration=3),

            tests=dict(number=20),
            tests_succ=dict(number=2),
            tests_skip=dict(number=5),
            tests_fail=dict(number=6),
            tests_error=dict(number=7),

            runs=dict(number=40),
            runs_succ=dict(number=12),
            runs_skip=dict(number=8),
            runs_fail=dict(number=9),
            runs_error=dict(number=10),

            reference_commit=None,
            reference_type='missing'
        ))

        self.assertEqual(get_stats_with_delta(dict(
            files=1,
            suites=2,
            duration=3,

            tests=20,
            tests_succ=2,
            tests_skip=5,
            tests_fail=6,
            tests_error=7,

            runs=40,
            runs_succ=12,
            runs_skip=8,
            runs_fail=9,
            runs_error=10,

            commit='commit'
        ), dict(
            files=3,
            suites=5,
            duration=7,

            tests=41,
            tests_succ=5,
            tests_skip=11,
            tests_fail=13,
            tests_error=15,

            runs=81,
            runs_succ=25,
            runs_skip=17,
            runs_fail=19,
            runs_error=21,

            commit='ref'
        ), 'type'), dict(
            files=n(1, 2),
            suites=n(2, 3),
            duration=d(3, 4),

            tests=n(20, 21),
            tests_succ=n(2, 3),
            tests_skip=n(5, 6),
            tests_fail=n(6, 7),
            tests_error=n(7, 8),

            runs=n(40, 41),
            runs_succ=n(12, 13),
            runs_skip=n(8, 9),
            runs_fail=n(9, 10),
            runs_error=n(10, 11),

            reference_commit='ref',
            reference_type='type'
        ))

    def test_as_delta(self):
        self.assertEqual(as_delta(0, 1), '±0')
        self.assertEqual(as_delta(+1, 1), '+1')
        self.assertEqual(as_delta(-2, 1), '-2')

        self.assertEqual(as_delta(0, 2), '± 0')
        self.assertEqual(as_delta(+1, 2), '+ 1')
        self.assertEqual(as_delta(-2, 2), '- 2')

        self.assertEqual(as_delta(1, 5), '+    1')
        self.assertEqual(as_delta(12, 5), '+   12')
        self.assertEqual(as_delta(123, 5), '+  123')
        self.assertEqual(as_delta(1234, 5), '+ 1234')

        with temp_locale('en_US.utf8'):
            self.assertEqual(as_delta(1234, 5), '+1,234')
        with temp_locale('de_DE.utf8'):
            self.assertEqual(as_delta(1234, 5), '+1.234')

    def test_as_stat_number(self):
        label = 'unit'
        self.assertEqual(as_stat_number(None, 1, 0, label), 'N/A unit')

        self.assertEqual(as_stat_number(1, 1, 0, label), '1 unit')
        self.assertEqual(as_stat_number(1234, 5, 0, label), ' 1234 unit')
        self.assertEqual(as_stat_number(12345, 5, 0, label), '12345 unit')

        with temp_locale('en_US.utf8'):
            self.assertEqual(as_stat_number(123, 6, 0, label), '   123 unit')
            self.assertEqual(as_stat_number(1234, 6, 0, label), ' 1,234 unit')
            self.assertEqual(as_stat_number(12345, 6, 0, label), '12,345 unit')
        with temp_locale('de_DE.utf8'):
            self.assertEqual(as_stat_number(123, 6, 0, label), '   123 unit')
            self.assertEqual(as_stat_number(1234, 6, 0, label), ' 1.234 unit')
            self.assertEqual(as_stat_number(12345, 6, 0, label), '12.345 unit')

        self.assertEqual(as_stat_number(dict(number=1), 1, 0, label), '1 unit')

        self.assertEqual(as_stat_number(dict(number=1, delta=-1), 1, 1, label), '1 unit [-1]')
        self.assertEqual(as_stat_number(dict(number=2, delta=+0), 1, 1, label), '2 unit [±0]')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1), 1, 1, label), '3 unit [+1]')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1), 1, 2, label), '3 unit [+ 1]')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1), 2, 2, label), ' 3 unit [+ 1]')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1234), 1, 6, label), '3 unit [+  1234]')
        with temp_locale('en_US.utf8'):
            self.assertEqual(as_stat_number(dict(number=3, delta=+1234), 1, 6, label), '3 unit [+ 1,234]')
            self.assertEqual(as_stat_number(dict(number=3, delta=+12345), 1, 6, label), '3 unit [+12,345]')
        with temp_locale('de_DE.utf8'):
            self.assertEqual(as_stat_number(dict(number=3, delta=+1234), 1, 6, label), '3 unit [+ 1.234]')
            self.assertEqual(as_stat_number(dict(number=3, delta=+12345), 1, 6, label), '3 unit [+12.345]')

        self.assertEqual(as_stat_number(dict(delta=-1), 3, 1, label), 'N/A [-1]')

        self.assertEqual(as_stat_number(dict(number=1, delta=-2, new=3), 1, 1, label), '1 unit [-2, 3 new]')
        self.assertEqual(as_stat_number(dict(number=2, delta=+0, new=3, gone=4), 1, 1, label), '2 unit [±0, 3 new, 4 gone]')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1, gone=4), 1, 1, label), '3 unit [+1, 4 gone]')

    def test_as_stat_duration(self):
        label = 'time'
        self.assertEqual(as_stat_duration(None, label), 'N/A time')
        self.assertEqual(as_stat_duration(0, None), '0s')
        self.assertEqual(as_stat_duration(0, label), '0s time')
        self.assertEqual(as_stat_duration(12, label), '12s time')
        self.assertEqual(as_stat_duration(72, label), '1m 12s time')
        self.assertEqual(as_stat_duration(3754, label), '1h 2m 34s time')
        self.assertEqual(as_stat_duration(-3754, label), '1h 2m 34s time')

        self.assertEqual(as_stat_duration(d(3754), label), '1h 2m 34s time')
        self.assertEqual(as_stat_duration(d(3754, 0), label), '1h 2m 34s time [± 0s]')
        self.assertEqual(as_stat_duration(d(3754, 1234), label), '1h 2m 34s time [+ 20m 34s]')
        self.assertEqual(as_stat_duration(d(3754, -123), label), '1h 2m 34s time [- 2m 3s]')
        self.assertEqual(as_stat_duration(dict(delta=123), label), 'N/A time [+ 2m 3s]')

    def do_test_get_short_summary_md(self, stats, expected_md):
        self.assertEqual(get_short_summary_md(stats), expected_md)

    def test_get_short_summary_md(self):
        self.do_test_get_short_summary_md(dict(
        ), ('N/A tests N/A :heavy_check_mark: N/A :zzz: N/A :heavy_multiplication_x: N/A :fire:'))

        self.do_test_get_short_summary_md(dict(
            files=1, suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
            runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13
        ), ('4 tests 5 :heavy_check_mark: 6 :zzz: 7 :heavy_multiplication_x: 8 :fire:'))

        self.do_test_get_short_summary_md(dict(
            files=n(1, 2), suites=n(2, -3), duration=d(3, 4),
            tests=n(4, -5), tests_succ=n(5, 6), tests_skip=n(6, -7), tests_fail=n(7, 8), tests_error=n(8, -9),
            runs=n(9, 10), runs_succ=n(10, -11), runs_skip=n(11, 12), runs_fail=n(12, -13), runs_error=n(13, 14),
            reference_type='type', reference_commit='0123456789abcdef'
        ), ('4 tests [-5] 5 :heavy_check_mark: [+6] 6 :zzz: [-7] 7 :heavy_multiplication_x: [+8] 8 :fire: [-9]'))

    def do_test_get_long_summary_md(self, stats, expected_md):
        self.assertEqual(get_long_summary_md(stats), expected_md)

    def test_get_long_summary_md(self):
        self.do_test_get_long_summary_md(dict(
        ), ('## Unit Test Results\n'
            'N/A files  N/A suites N/A :stopwatch:\n'
            'N/A tests N/A :heavy_check_mark: N/A :zzz: N/A :heavy_multiplication_x: N/A :fire:\n'
            'N/A runs  N/A :heavy_check_mark: N/A :zzz: N/A :heavy_multiplication_x: N/A :fire:\n'))

        self.do_test_get_long_summary_md(dict(
            files=1, suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
            runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13
        ), ('## Unit Test Results\n'
            '1 files  2 suites 3s :stopwatch:\n'
            '4 tests  5 :heavy_check_mark:  6 :zzz:  7 :heavy_multiplication_x:  8 :fire:\n'
            '9 runs  10 :heavy_check_mark: 11 :zzz: 12 :heavy_multiplication_x: 13 :fire:\n'))

        self.do_test_get_long_summary_md(dict(
            files=n(1, 2), suites=n(2, -3), duration=d(3, 4),
            tests=n(4, -5), tests_succ=n(5, 6), tests_skip=n(6, -7), tests_fail=n(7, 8), tests_error=n(8, -9),
            runs=n(9, 10), runs_succ=n(10, -11), runs_skip=n(11, 12), runs_fail=n(12, -13), runs_error=n(13, 14),
            reference_type='type', reference_commit='0123456789abcdef'
        ), ('## Unit Test Results\n'
            '1 files  [+ 2] 2 suites [-3] 3s :stopwatch: [+ 4s]\n'
            '4 tests [- 5]  5 :heavy_check_mark: [+ 6]  6 :zzz: [- 7]  7 :heavy_multiplication_x: [+ 8]  8 :fire: [- 9]\n'
            '9 runs  [+10] 10 :heavy_check_mark: [-11] 11 :zzz: [+12] 12 :heavy_multiplication_x: [-13] 13 :fire: [+14]\n'
            '\n'
            '[±] comparison against type commit 01234567'))

    def test_files(self):
        parsed = parse_junit_xml_files(['files/junit.gloo.elastic.spark.tf.xml',
                                        'files/junit.gloo.elastic.spark.torch.xml',
                                        'files/junit.gloo.elastic.xml',
                                        'files/junit.gloo.standalone.xml',
                                        'files/junit.gloo.static.xml',
                                        'files/junit.mpi.integration.xml',
                                        'files/junit.mpi.standalone.xml',
                                        'files/junit.mpi.static.xml',
                                        'files/junit.spark.integration.1.xml',
                                        'files/junit.spark.integration.2.xml'])
        results = get_test_results(parsed)
        stats = get_stats(results)
        md = get_long_summary_md(stats)
        self.assertEqual(md, ('## Unit Test Results\n'
                              ' 10 files  10 suites 39m 1s :stopwatch:\n'
                              '217 tests 208 :heavy_check_mark:  9 :zzz: 0 :heavy_multiplication_x: 0 :fire:\n'
                              '373 runs  333 :heavy_check_mark: 40 :zzz: 0 :heavy_multiplication_x: 0 :fire:\n'))


if __name__ == '__main__':
    unittest.main()