"""Recreate shortcuts in a dedicated folder; never merge with an existing unrelated project."""
import json
from pathlib import Path
import shlex

root=Path(__file__).resolve().parents[1]
desktop=Path.home()/'Desktop/NEUAURA B2B'
marker=desktop/'.neuaura-b2b-shortcuts'
if desktop.exists() and (not marker.exists() or marker.read_text().strip()!=str(root)):
    raise SystemExit('Desktop/NEUAURA B2B already exists without this installer marker. Choose a separate folder before installing.')
desktop.mkdir(exist_ok=True)
marker.write_text(str(root)+'\n')
for filename,action in [('Start NEUAURA.command','start'),('Stop NEUAURA.command','stop'),('Copy setup token.command','copy-setup-token')]:
    content='#!/bin/bash\ncd '+shlex.quote(str(root))+'\n'+shlex.quote(str(root/'.venv/bin/python'))+' scripts/desktop.py '+action+'\nresult=$?\nprintf "\\nYou may close this window. Press Enter to finish.\\n"\nread -r unused\nexit "$result"\n'
    file=desktop/filename
    file.write_text(content)
    file.chmod(0o755)
link=desktop/'Project files'
if not link.exists() and not link.is_symlink():link.symlink_to(root,target_is_directory=True)
(desktop/'NEUAURA.code-workspace').write_text(json.dumps({'folders':[{'path':str(root)}],'settings':{'python.defaultInterpreterPath':str(root/'.venv/bin/python')}},indent=2)+'\n')
(desktop/'START HERE.txt').write_text('NEUAURA B2B\n\nDouble-click Start NEUAURA.command to start the app and AI.\nOpen http://localhost:8000.\nFirst time: run Copy setup token.command and paste into Setup token, then choose your own email/password.\nDouble-click Stop NEUAURA.command to stop.\n\nProject folder: '+str(root)+'\n\nOpen Project files, then docs/START_HERE.md for complete instructions and file locations.\n')
print('Desktop shortcuts ready: '+str(desktop))
