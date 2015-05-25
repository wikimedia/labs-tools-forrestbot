jsub -N forrestbot -l release=trusty -mem 500M /data/project/forrestbot/venv/bin/python /data/project/forrestbot/forrestbot/forrestbot.py
echo "Tailing log file, ^C to exit"
tail -f ~/forrestbot.err
