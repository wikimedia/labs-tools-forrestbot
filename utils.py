def wmf_number(branchname):
    """
    >>> wmf_number('1.26wmf10')
    12610
    >>> wmf_number('1.25wmf8')
    12508
    >>> wmf_number('1.26wmf3-back') # wtf Gather??
    False
    >>> wmf_number('phase0')
    False
    """

    try:
        major, minor = branchname.split('wmf', 1)
    except ValueError:
        return False
    major = major.replace('.', '')
    try:
        int(minor)
    except ValueError:
        return False
    if len(minor) == 1:
        minor = '0' + minor

    return int(major + minor)
