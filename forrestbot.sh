#!/bin/bash
/data/project/forrestbot/venv-tf-python39/bin/python /data/project/forrestbot/forrestbot/forrestbot.py --logfile /data/project/forrestbot/forrestbot.log || (/data/project/forrestbot/venv-tf-python39/bin/python /data/project/forrestbot/forrestbot/error_email_k8s.py)

