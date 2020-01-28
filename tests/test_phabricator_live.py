from pathlib import Path

import pytest

root = Path(__file__).parent.parent  # type: Path

if not (root / "config.py").exists():
    pytest.skip("No config.py present; skipping live tests", allow_module_level=True)

import forrestbot  # noqa -- import after verifying import can succeed


def test_get_slug():
    expected_slugs = {
        "pywikibot": "PHID-PROJ-orw42whe2lepxc7gghdq",
        "mw1.35.0-wmf.15": "PHID-PROJ-d5gpv3yru5mbqtsqnu52",
        "REL1_32": "PHID-PROJ-gmoiawb4gkjjuwz2qk2h",
    }

    retrieved_slugs = {
        slug: forrestbot.get_slug_PHID(slug)
        for slug in expected_slugs.keys()
    }

    assert expected_slugs == retrieved_slugs


def test_nonexistent_slug():
    try:
        forrestbot.get_slug_PHID("thisslugdoesnotexist")
        pytest.fail()
    except Exception as e:
        assert str(e) == "No PHID found for slug #thisslugdoesnotexist!"


def test_taskinfo():
    task_info = forrestbot.phab.request('maniphest.info', {'task_id': "243540"})

    assert 'PHID-PROJ-tzg2rzj42nn6vfeq3nou' in task_info['projectPHIDs']
