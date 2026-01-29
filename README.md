# ForrestBot - Release Tagger Bot

ForrestBot is an automated bot that processes Gerrit merge notifications and adds appropriate release tags to Phabricator tasks. It monitors Wikimedia Foundation's Gerrit repository for merged changesets and automatically tags the corresponding Phabricator tasks with the appropriate MediaWiki release version tags.

## Overview

ForrestBot operates as a cron-based service that:
1. Polls a POP3 mailbox for Gerrit merge notifications
2. Parses merge events to extract repository, branch, and task information
3. Determines which MediaWiki release tags should be applied
4. Updates Phabricator tasks by adding the appropriate project tags

## Architecture

### Entry Point

**[forrestbot.py](forrestbot.py)** - The main entry point that orchestrates the entire process:
- Connects to the POP3 mailbox via `pop3bot.py`
- Processes emails through `gerritmail_generator()` which acts as an event queue
- Parses merge notifications to extract task and branch information
- Batches updates by task ID to avoid duplicate edits
- Communicates with Phabricator API to add release tags

### Cron Scheduling

**[crontab](crontab)** - Defines the execution schedule:
```
0 * * * * jsub -quiet -N forrestbot -mem 500M /data/project/forrestbot/forrestbot/forrestbot.sh
```
- Runs hourly (at the top of each hour)
- Executes via the [forrestbot.sh](forrestbot.sh) wrapper script

**[forrestbot.sh](forrestbot.sh)** - Shell wrapper that:
- Executes `forrestbot.py` with a 1-hour timeout
- Logs output to a rotating log file
- Triggers error notification email on failure via [error_email_k8s.py](error_email_k8s.py)

### Event Queue

**[pop3bot.py](pop3bot.py)** - POP3 email client that provides the event queue:
- Connects to a mailbox via POP3
- Retrieves Gerrit merge notification emails from `gerrit@wikimedia.org`
- Parses email headers and body to extract Gerrit metadata
- Acts as a persistent queue: emails remain until successfully processed and deleted
- Provides `gerritmail_generator()` which yields parsed Gerrit events

### Core Utilities

**[gerrit_rest.py](gerrit_rest.py)** - REST API client for Gerrit:
- Queries Gerrit for repository information
- Retrieves branch lists for repositories
- Provides access to changeset details

**[utils.py](utils.py)** - Helper functions:
- `wmf_number()`: Parses and compares WMF branch version numbers
- `parse_task_number()`: Extracts task IDs from Bug/Task fields (supports both Phabricator T-numbers and legacy Bugzilla IDs)
- `get_slug()` and `slugify()`: Converts branch names to Phabricator project slugs (e.g., `REL1_23` → `mw1.23`)

**[wblogging.py](wblogging.py)** - Logging configuration:
- Sets up file-based logging with rotation
- Creates log files with secure permissions (0o600)
- Supports both file and stdout logging

**[error_email_k8s.py](error_email_k8s.py)** - Error notification:
- Sends email alerts when ForrestBot encounters errors
- Attaches compressed log file for debugging
- Only triggered on failure (non-zero exit code)

### Configuration

**[config.py.example](config.py.example)** - Template for configuration (copy to `config.py`):
- POP3 credentials for the notification mailbox
- Phabricator API credentials (host, username, token)

**[requirements.txt](requirements.txt)** - Python dependencies:
- `requests`: HTTP client for API calls
- `fab`: Phabricator API client (imported as `phabricator`)
- `wikimediaci-utils`: WMF-specific utilities for repository management

## Processing Logic

### Event Processing Flow

1. **Email Retrieval**: POP3bot retrieves emails from the mailbox
2. **Filtering**: Only processes emails with `X-Gerrit-MessageType: merged`
3. **Repository Filtering**: Only processes watched repositories (MediaWiki core + deployed extensions)
4. **Task Extraction**: Extracts task ID from `Bug:`, `Closes:`, or `Task:` fields
5. **Branch Analysis**: Determines which release tags to apply based on merge target branch
6. **Batching**: Groups all actions by task ID to minimize changes to Tasks
7. **Phabricator Update**: Adds release tags to tasks
8. **Email Deletion**: Removes successfully processed emails from the queue

### Branch-to-Tag Mapping

The bot applies different logic based on the merge target branch:

| Merge Target Branch | Tag(s) Applied | Notes |
|-------------------|----------------|-------|
| `master` | Next unreleased WMF branch | e.g., `mw1.43.0-wmf.5` (determined by querying latest wmf/ branch) |
| `wmf/X.Y.Z-wmf.N` | Matching release tag | e.g., `wmf/1.35.0-wmf.15` → `mw1.35.0-wmf.15` |
| `REL1_XX` (core) | Matching release tag | e.g., `REL1_32` → `mw1.32` |
| `REL1_XX` (extensions) | No tag | Extensions' REL branches aren't always in tarballs |
| `wmf_deploy` | No tag | Special deployment branch |

### Watched Repositories

- **MediaWiki Core**: `mediawiki/core`
- **Deployed Extensions**: Retrieved dynamically from `wikimediaci-utils.get_wikimedia_deployed_list()`

### Non-Deterministic / State-Dependent Components

**Master Branch Tag Resolution** (`get_master_branches()`):
- **Depends on**: Current state of Gerrit repository branches
- **Behavior**: Queries Gerrit to find the latest `wmf/` branch, then calculates the next branch
- **Example**: If processed before wmf.21 is created, might tag as `mw1.43.0-wmf.21`, but after wmf.22 is branched, would tag as `mw1.43.0-wmf.22`

**Repository Watch List** (`get_repos_to_watch()`):
- **Depends on**: External list of deployed extensions from `wikimediaci-utils`

**Phabricator Slug-to-PHID Resolution** (`get_slug_PHID()`):
- **Depends on**: Current Phabricator project configuration
- **Behavior**: If project slugs are renamed or deleted, lookups may fail

**Task Visibility** (`maniphest.info` API call):
- **Depends on**: Task security settings and user permissions
- **Behavior**: May fail if task becomes private/restricted

**Task Update Permissions** (`maniphest.update` API call):
- **Depends on**: Task edit permissions (e.g., read-only archived tasks)
- **Behavior**: May fail if task is locked or bot lacks permissions

### Error Handling

- Errors are logged to rotating log files (`forrestbot.log`)
- Critical errors trigger email notifications to maintainers
- Individual task failures don't stop batch processing
- All errors are summarized at the end of execution

### Deployment

Deployed on Toolforge as a Toolforge job:
- Configuration in [k8s-jobs.yaml](k8s-jobs.yaml)
- Runs in a Python 3.9 virtual environment
- Uses project-specific service account

## License and Attribution

- **Authors**: Merlijn van Deen (valhallasw) and Kunal Mehta (legoktm) with lots of input from James Forrester (jdforrester)
- **License**: GPLv3 or later
