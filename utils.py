import re


def wmf_number(branchname):
    """
    >>> wmf_number('1.27.0-wmf.21')
    12721
    >>> wmf_number('1.27.0-wmf21')
    12721
    >>> wmf_number('1.27.0-wmf.1')
    12701
    >>> wmf_number('1.27.0-wmf1')
    12701
    >>> wmf_number('1.26wmf10')
    12610
    >>> wmf_number('1.25wmf8')
    12508
    >>> wmf_number('1.26wmf3-back') # wtf Gather??
    False
    >>> wmf_number('phase0')
    False
    >>> wmf_number('1.27.2-wmf1') # only doing -wmf for .0
    False
    """
    try:
        major, minor = branchname.split('wmf', 1)
    except ValueError:
        return False

    major = major.replace('.', '')
    major = major.replace('-', '')
    if len(major) == 4:
        if major[-1] != '0':
            return False
        major = major[:-1]

    minor = minor.replace('.', '')
    try:
        int(minor)
    except ValueError:
        return False
    if len(minor) == 1:
        minor = '0' + minor

    return int(major + minor)


class TaskParseException(Exception):
    pass


_task_number_re = re.compile(r'T(\d+)')
_bugzilla_number_re = re.compile(r'(\d+)')


def parse_task_number(bugstring):
    """
    Find the first bug-like entry in the Bug: field
    This can be either a Phabricator T bug, or a Bugzilla-style bug number.
    Badly formed entries (e.g. Bug:    T1234) are also OK.

    >>> parse_task_number("T1234")
    1234
    >>> parse_task_number("T1234 ")
    1234
    >>> parse_task_number("   T1234")
    1234
    >>> parse_task_number("Bug: T1234")
    1234
    >>> parse_task_number("T1234, T1235, T1236")
    1234
    >>> # Bugzilla style, add 2000 to get Phab Task number
    >>> parse_task_number("1234")
    3234
    >>> try:
    ...     parse_task_number("Ttt")
    ... except TaskParseException as e:
    ...     assert str(e) == "Could not parse bug string 'Ttt'"
    """
    try:
        phab_match = _task_number_re.search(bugstring)
        if phab_match:
            return int(phab_match.groups()[0])
        bz_match = _bugzilla_number_re.search(bugstring)
        if bz_match:
            return int(bz_match.groups()[0]) + 2000
    except Exception as e:
        raise TaskParseException(
            "Could not parse bug string %r: %r" % (bugstring, e)
        )
    raise TaskParseException(
        "Could not parse bug string %r" % (bugstring, )
    )
