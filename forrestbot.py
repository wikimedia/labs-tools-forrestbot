"""
See https://etherpad.wikimedia.org/p/T280 / https://phabricator.wikimedia.org/T280
"""
__author__ = 'Merlijn van Deen'

import functools

import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('forrestbot')

import gerrit_rest
import legophab
import config

phab = legophab.Phabricator(
            config.PHAB_HOST,
            config.PHAB_USER,
            config.PHAB_CERT
        )

@functools.lru_cache()
def get_master_branches():
    gerrit = gerrit_rest.GerritREST("https://gerrit.wikimedia.org/r")
    projbranches = gerrit.branches("mediawiki%2Fcore")

    projbranches = [b['ref'] for b in projbranches]

    marker = 'refs/heads/wmf/'
    newest_wmf = sorted([b for b in projbranches if marker in b])[-1]
    newest_wmf = newest_wmf.split(marker)[1]

    def REL_key(REL):
        major, minor = REL.split("REL")[1].split("_")
        return int(major), int(minor)

    marker = 'refs/heads/REL'
    newest_REL = sorted([b for b in projbranches if marker in b], key=REL_key)[-1]
    newest_REL = newest_REL.split('refs/heads/')[1]

    return [newest_REL, newest_wmf]

print(get_master_branches())
print(get_master_branches())


def get_slug(branch):
    """ Slugify the branch name.

    REL1_23 --> mw1.23
    1.23wmf6 -> mw1.23wmf6

    :param branch: Branch name
    :return: Slugified branch name
    """
    if branch[:3] == "REL":
        major, minor = branch.split("REL")[1].split("_")
        return "mw%s.%s" % (major, minor)
    elif "wmf" in branch:
        return 'mw'+branch

def slugify(taskbranches):
    """ Slugify all branches

    :param taskbranches: list of branches
    :return: list of slugs
    """

    slugs = [get_slug(b) for b in taskbranches]

testmail = {'X-Gerrit-Change-Id': 'I650cd2615ebac862e1b5fcff3707f4caf7f56944',
                         'X-Gerrit-MessageType': 'merged',
                         'X-Gerrit-Branch': '1.23wmf6',
                         'Bug': 'T1152'}


class SkipMailException(Exception):
    pass

def process_mail(mail):
    if mail.get('X-Gerrit-MessageType', '') != 'merged':
        raise SkipMailException('Not a merge email')

    try:
        taskbranches = mail['X-Gerrit-Branch']
        task = mail.get('Bug', '') or mail.get('Closes', '')
        if not task:
            raise KeyError
    except KeyError as e:
        raise SkipMailException(e)

    if taskbranches == ['master']:
        taskbranches =  get_master_branches()

    slugs = slugify(taskbranches)
    project_PHIDs = phab.request('project.query', {'slugs': slugs})['slugMap'].values()

    try:
        existing_projects = phab.request('maniphest.info', {'task_id': task})['projectPHIDs']
    except PhabricatorException as e:
        if e.code == 'ERR_BAD_TASK':
            logging.verbose('Task %s does not exist!' % task)
            raise SkipMailException(e)

    phab.request('maniphest.update', {'id': '1152', 'projectPHIDs': project_PHIDs})



# query projects


#import pop3bot

#mailbox = pop3bot.mkmailbox()
#for mail in pop3bot.gerritmail_generator():