"""
See https://etherpad.wikimedia.org/p/T280 / https://phabricator.wikimedia.org/T280
"""
__author__ = 'Merlijn van Deen'

import gerrit_rest
reload(gerrit_rest)

# need to get this from somewhere
KNOWN_PROJECTS = """MW-1.19-release
MW-1.23-release
MW-1.24-release
MW-1.25-release
MW-1.26-release
WMF-deploy-2015-04-29_(1.26wmf4)
WMF-deploy-2015-05-06_(1.26wmf5)
WMF-deploy-2015-05-13_(1.26wmf6)
WMF-deploy-2015-05-20_(1.26wmf7)""".split("\n")

#import pop3bot

#mailbox = mkmailbox()
#for mail in pop3bot.gerritmail_generator():
    if mail.get('X-Gerrit-MessageType', '') != 'merged':
        continue
    branches = [mail['GERRIT_BRANCH']] # or something like that

    # GET BRANCHES FROM CHANGE
    branches = ['master']

    if branches == ['master']:
        gerrit = gerrit_rest.GerritREST("https://gerrit.wikimedia.org/r")
        branches = gerrit.branches("mediawiki%2Fcore")

        branches = [b['ref'] for b in branches]

        newest_wmf = sorted([b for b in branches if 'refs/heads/wmf/' in b])[-1]

        def REL_key(REL):
            major, minor = REL.split("REL")[1].split("_")
            return int(major), int(minor)

        newest_REL = sorted([b for b in branches if 'refs/heads/REL' in b], key=REL_key)[-1]
        branches =[newest_REL, newest_wmf]

    # now we need to get the right tag for all branches
    matched_projs = {}
    for project in KNOWN_PROJECTS:
        match1 = re.match(r"MW-([0-9\.]+)-release", project)
        if match1:
            branch = "refs/heads/REL" + match1.group(1).replace(".", "_")
            matched_projs[branch] = project
            continue

        match2 = re.match(r"WMF-deploy-.*\(([0-9\.]+wmf[0-9\.]+)\)", project)
        if match2:
            branch = "refs/heads/wmf/" + match2.group(1)
            matched_projs[branch] = project
            continue

        print "skipping ", project

    projects = [matched_projs[b] for b in branches]



