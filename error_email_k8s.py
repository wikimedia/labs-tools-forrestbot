import bz2
import smtplib
from email.message import EmailMessage

errlog = open('forrestbot.log').readlines()

errorlines = []
for line in errlog:
    if "ERROR SUMMARY" in line:
        errorlines = [line]
    else:
        errorlines.append(line)

errortext = "".join(errorlines[-100:])

message = f"""Dear friends of ReleaseTaggerBot,

I'm sorry to inform you that ReleaseTaggerBot has run into a snag.
Please see the error below:

{errortext}

The full error log has been attached for your convenience.

With kind regards,
valhallasw in the past
"""

msg = EmailMessage()
msg.set_content(message)
msg['Subject'] = "ReleaseTaggerBot broken"
msg['From'] = "tools.forrestbot <tools.forrestbot@tools.wmflabs.org>"
msg['To'] = "ReleaseTaggerBot maintainers <tools.forrestbot@tools.wmflabs.org>"
msg.add_attachment(
    bz2.compress(open('forrestbot.log', 'rb').read()),
    filename='error.log.bz2',
    maintype='application',
    subtype='octet-stream')

s = smtplib.SMTP('mail.tools.wmflabs.org')
s.send_message(msg)
s.quit()

print("Sent error email")
