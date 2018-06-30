"""
https://etherpad.wikimedia.org/p/T280 & https://phabricator.wikimedia.org/T280
"""
__author__ = 'Merlijn van Deen'  # noqa

import functools
import itertools
import requests

import logging
from wblogging import LoggingSetupParser

import gerrit_rest
import phabricator as legophab
import config
from utils import wmf_number, parse_task_number, slugify

parser = LoggingSetupParser(
    description="Process changesets and add release tags as required",
)
args = parser.parse_args()

logging.getLogger('requests').setLevel(logging.INFO)
logger = logging.getLogger('forrestbot')


phab = legophab.Phabricator(
    config.PHAB_HOST,
    config.PHAB_USER,
    config.PHAB_CERT
)
gerrit = gerrit_rest.GerritREST("https://gerrit.wikimedia.org/r")


@functools.lru_cache()
def get_master_branches(repository):
    logging.debug("Requesting 'master' branches for %s" % repository)
    silly_encoded_name = repository.replace('/', '%2F')  # wtf gerrit
    projbranches = gerrit.branches(silly_encoded_name)

    projbranches = [b['ref'] for b in projbranches]

    marker = 'refs/heads/wmf/'
    newest_wmf = sorted([b.split(marker)[1] for b in projbranches
                         if (marker in b and wmf_number(b.split(marker)[1]))],
                        key=wmf_number)[-1]

    wmf_parts = newest_wmf.split("wmf")
    wmf_parts[1] = wmf_parts[1].replace('.', '')
    next_wmf = wmf_parts[0] + "wmf" + str(int(wmf_parts[1]) + 1)

    return [next_wmf]


@functools.lru_cache()
def get_repos_to_watch():
    # This url will redirect like 3 times, but requests handles it nicely
    r = requests.get(
        'https://phabricator.wikimedia.org/diffusion/MREL/browse/master/' +
        'make-wmf-branch/config.json?view=raw'
    )
    conf = r.json()
    repos = ['mediawiki/core']
    for ext in conf['extensions']:
        repos.append('mediawiki/' + ext)
    # Intentionally ignore special_extensions because they're special
    return repos


@functools.lru_cache()
def get_slug_PHID(slug):
    try:
        rq = list(
            phab.request('project.query', {'slugs': [slug]})['slugMap']
                .values()
        )
    except AttributeError:
        # If slugMap is empty, an empty list rather than an empty dict is
        # returned by Phabricator.
        raise Exception("No PHID found for slug #%s!" % slug)
    if rq:
        logging.debug(
            "Slug {slug} = PHID {phid}".format(slug=slug, phid=rq[0])
        )
        return rq[0]
    raise Exception("No PHID found for slug #%s!" % slug)


class SkipMailException(Exception):
    pass


def process_mail(mail):
    proj = mail.get('Gerrit-Project', '')
    if proj not in get_repos_to_watch():
        raise SkipMailException("Project %s is not being watched" % proj)
    if mail.get('X-Gerrit-MessageType', '') != 'merged':
        raise SkipMailException('Not a merge email')

    try:
        taskbranches = [mail['Gerrit-Branch']]
        task = (
            mail.get('Bug', '') or
            mail.get('Closes', '') or
            mail.get('Task', '')
        )
        task = task.strip()
        if not task:
            raise KeyError('No Task ID (Bug, Closes or Task)')
        task = parse_task_number(task)
    except KeyError as e:
        raise SkipMailException(e)

    if taskbranches == ['master']:
        taskbranches = get_master_branches(proj)

    if proj != 'mediawiki/core':
        # Remove any REL1_XX branches for now since we don't know if this
        # extension is included in the tarball.
        for taskbranch in taskbranches[:]:
            if taskbranch.startswith('REL'):
                taskbranches.remove(taskbranch)

    slugs = slugify(taskbranches)

    return {
        'url': mail['X-Gerrit-ChangeURL'][1:-1],
        'branch': mail['Gerrit-Branch'],
        'task': task,
        'slugs': slugs,
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s: %(levelname)-8s - %(message)s'
    )

    # logger.info("Current master branches are: %r" % (get_master_branches(),))

    import pop3bot
    mailbox = pop3bot.mkmailbox()

    nmails, octets = mailbox.stat()

    logger.info("%i e-mails to process (%i kB)" % (nmails, octets/1024))

    actions = []

    for i, mail in enumerate(pop3bot.gerritmail_generator(mailbox)):
        try:
            action = process_mail(mail)
            actions.append(action)
            logger.info(
                ("{url}: merged in branch {branch}, Task {task}," +
                 " needs slugs {slugs}").format(**action)
            )
        except SkipMailException as e:
            logger.debug("%s: skipping (%r)" % (mail['X-Gerrit-ChangeURL'], e))
            pass

    # after parsing all entries, make sure we only do a single edit per Task.
    def key(x):
        return x['task']

    for task, acts in itertools.groupby(sorted(actions, key=key), key=key):
        acts = sorted(acts, key=lambda x: x['slugs'])

        add_PHIDs = set()

        # build changes
        for act in acts:
            for slug in act['slugs']:
                add_PHIDs.add(get_slug_PHID(slug))

        logger.info("Adding PHID {PHIDs} to T{task}.".format(
            PHIDs=add_PHIDs, task=task
        ))

        # now we get the task to know what the existing tags are
        task_info = phab.request('maniphest.info', {'task_id': str(task)})
        if not task_info:
            # Security bug? T101133
            logger.warning(
                ('Unable to get information about T{task}, maybe it is' +
                 ' private?').format(task=task)
            )
            continue
        old_projs = set(task_info['projectPHIDs'])
        logger.debug("Existing PHIDs: {old_projs}".format(old_projs=old_projs))
        new_projs = set(task_info['projectPHIDs']) | add_PHIDs
        if old_projs != new_projs:
            phab.request('maniphest.update', {'id': str(task),
                                              'projectPHIDs': list(new_projs),
                                              }
                         )
        else:
            logging.info(
                "Skipping T{task}; no new projects to add".format(task=task)
            )

    mailbox.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Releasetaggerbot crashed while processing messages")
        raise
