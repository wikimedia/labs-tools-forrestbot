import re
from pathlib import Path

import pytest

root = Path(__file__).parent.parent  # type: Path

if not (root / "config.py").exists():
    pytest.skip("No config.py present; skipping live tests", allow_module_level=True)

import forrestbot  # noqa -- import after verifying import can succeed
import pop3bot     # noqa -- import after verifying import can succeed


class FakeMailbox:
    def __init__(self, filename):
        self._content = [(root / 'tests' / 'data' / filename).open(encoding='utf-8').read()]

    def stat(self):
        return len(self._content), sum(len(x) for x in self._content)

    def top(self, item, n_lines):
        return (
            "+OK",
            [x.encode('utf-8') for x in self._content[item-1].split("\n")[:n_lines]],
            len(self._content[item-1])
        )

    def dele(self, id):
        pass


def test_lst_merged_notask():
    """If no Task ID is present we cannot add a tag to the task"""
    mail = list(pop3bot.gerritmail_generator(FakeMailbox('lst_merged_notask.mbox')))[0]
    try:
        forrestbot.process_mail(mail)
        pytest.fail()
    except forrestbot.SkipMailException as e:
        assert str(e) == "'No Task ID (Bug, Closes or Task)'"


def test_lst_merged_REL():
    """Release branches for extensions do not get tagged as it is unclear whether they are included in the tarball"""
    mail = list(pop3bot.gerritmail_generator(FakeMailbox('lst_merged_REL.mbox')))[0]
    result = forrestbot.process_mail(mail)

    assert result == {
        'branch': 'REL1_32',
        'slugs': [],
        'task': 207255,
        'url': 'https://gerrit.wikimedia.org/r/473672'}


def test_lst_merged_master():
    """When a change is merged in master, apply the most recent release branch slug"""
    mail = list(pop3bot.gerritmail_generator(FakeMailbox('lst_merged_master.mbox')))[0]
    result = forrestbot.process_mail(mail)

    assert result['branch'] == 'master'
    assert result['task'] == 207255
    assert result['url'] == 'https://gerrit.wikimedia.org/r/472763'

    assert len(result['slugs']) == 1
    assert re.match(r"mw\d+\.\d+\.\d+-wmf\.\d+", result['slugs'][0])


def test_wmf_deploy():
    """wmf_deploy branch should be skipped and should not crash"""
    mail = list(pop3bot.gerritmail_generator(FakeMailbox('wmf_deploy.mbox')))[0]
    result = forrestbot.process_mail(mail)

    assert result == {
        'branch': 'wmf_deploy',
        'slugs': [],
        'task': 196090,
        'url': 'https://gerrit.wikimedia.org/r/566748'
    }


def test_extension_wmf_branch():
    mail = list(pop3bot.gerritmail_generator(FakeMailbox('extension_wmf_branch.mbox')))[0]
    result = forrestbot.process_mail(mail)

    assert result == {
        'branch': 'wmf/1.35.0-wmf.15',
        'slugs': ['mw1.35.0-wmf.15'],
        'task': 231720,
        'url': 'https://gerrit.wikimedia.org/r/566382'
    }


def test_mw_core_master():
    mail = list(pop3bot.gerritmail_generator(FakeMailbox('mw_core_master.mbox')))[0]
    result = forrestbot.process_mail(mail)

    assert result['branch'] == 'master'
    assert result['task'] == 241354
    assert result['url'] == 'https://gerrit.wikimedia.org/r/562917'

    assert len(result['slugs']) == 1
    assert re.match(r"mw\d+\.\d+\.\d+-wmf\.\d+", result['slugs'][0])


@pytest.mark.xfail
def test_mw_core_REL_branch():
    pytest.fail("No example email found yet")

    mail = list(pop3bot.gerritmail_generator(FakeMailbox('mw_core_REL_branch.mbox')))[0]
    result = forrestbot.process_mail(mail)

    assert result is not None


def test_mw_core_wmf_branch():
    mail = list(pop3bot.gerritmail_generator(FakeMailbox('mw_core_wmf_branch.mbox')))[0]
    result = forrestbot.process_mail(mail)

    assert result == {
        'branch': 'wmf/1.35.0-wmf.16',
        'slugs': ['mw1.35.0-wmf.16'],
        'task': 243125,
        'url': 'https://gerrit.wikimedia.org/r/566586'
    }


def test_nontracked_repo():
    try:
        mail = list(pop3bot.gerritmail_generator(FakeMailbox('nontracked_repo.mbox')))[0]
        forrestbot.process_mail(mail)
        pytest.fail()
    except forrestbot.SkipMailException as exc:
        assert str(exc) == "Project operations/mediawiki-config is not being watched"


def test_not_jenkins():
    assert list(pop3bot.gerritmail_generator(FakeMailbox('not_jenkins.mbox'))) == []


def test_not_merge():
    try:
        mail = list(pop3bot.gerritmail_generator(FakeMailbox('not_merge.mbox')))[0]
        forrestbot.process_mail(mail)
        pytest.fail()
    except forrestbot.SkipMailException as exc:
        assert str(exc) == "Not a merge email"
