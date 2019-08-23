#!/bin/bash
/data/project/forrestbot/venv-py35-stretch/bin/python /data/project/forrestbot/forrestbot/forrestbot.py --logfile /data/project/forrestbot/forrestbot.log || (tail -n 30 /data/project/forrestbot/forrestbot.log | mail -s "Forrestbot broken" valhallasw@arctus.nl)

