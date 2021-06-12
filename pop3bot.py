import poplib
import email.parser
import config
import logging
import gerrit_rest

# monkey patch max line length for poplib
# as gmail sometimes sends > 2048 char lines
poplib._MAXLINE = 4096

logger = logging.getLogger('pop3bot')


def mkmailbox(debug=0):
    username = config.username
    password = config.password

    mailbox = poplib.POP3_SSL('pop.googlemail.com', '995')
    mailbox.set_debuglevel(debug)

    mailbox.user(username)
    mailbox.pass_(password)

    return mailbox


def mail_generator(mailbox):
    """ RETRieves the contents of mails, yields those
        and DELEtes them before the next mail is RETRieved """
    nmails, octets = mailbox.stat()
    for i in range(1, nmails+1):
        # use TOP rather than REPR to stop gmail from hiding/deleting emails
        # without explicit DELE
        yield "\n".join(
            [x.decode('utf-8', 'replace') for x in mailbox.top(i, 1000)[1]]
        )
        mailbox.dele(i)


def message_generator(mailbox):
    p = email.parser.Parser()
    for mail in mail_generator(mailbox):
        mail = p.parsestr(mail)
        payload = mail.get_payload(decode=True)
        if not payload:
            logger.debug("email from %s does not have payload" % mail['From'])
            continue
        yield mail, payload.decode('utf-8', 'replace')


def get_gerrit_data_from_contents(contents):
    for line in contents.split('\n'):
        if ': ' in line:
            key, value = line.split(': ', 1)
            if key.startswith('Gerrit-') or key in ['Bug', 'Task', 'Closes']:
                yield key, value.rstrip()


def gerritmail_generator(mailbox):
    for message, contents in message_generator(mailbox):
        if 'gerrit@wikimedia.org' not in message.get('From', ''):
            logger.debug(
                'Skipping message from %s' % message.get('From', '???')
            )
            continue

        gerrit_data = dict(
            (k, v) for (k, v) in message.items()
            if k.startswith('X-Gerrit')
        )

        gerrit_data.update(dict(get_gerrit_data_from_contents(contents)))

        if gerrit_data:
            yield gerrit_data


g = gerrit_rest.GerritREST('https://gerrit.wikimedia.org/r')


def get_changeset(changeid, o=['CURRENT_REVISION', 'CURRENT_FILES']):
    matchingchanges = g.changes(changeid, n=1, o=o)
    if matchingchanges:
        return matchingchanges[0]
    else:
        return None


if __name__ == "__main__":
    mailbox = mkmailbox(0)
    nmails, octets = mailbox.stat()
    print("%i e-mails to process (%i kB)" % (nmails, octets/1024))

    for m in gerritmail_generator(mailbox):
        print(repr(m))
        break

"""
if __name__ == "__main__":
    mailbox = mkmailbox(0)
    nmails, octets = mailbox.stat()

    from add_reviewer import ReviewerFactory, add_reviewers
    RF = ReviewerFactory()

    print("%i e-mails to process (%i kB)" % (nmails, octets/1024))

    try:
        for j,changeset in enumerate(new_changeset_generator(mailbox)):
            reviewers = get_reviewers_for_changeset(changeset)
            add_reviewers(changeset['current_revision'], reviewers)
    finally:
        # flush succesfully processed emails
        mailbox.quit()
"""
