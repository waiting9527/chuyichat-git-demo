import subprocess,sys,tempfile,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_guard import SafetyTests
x=SafetyTests(); x.setUp()
try:
    script=str(Path(__file__).with_name('guard.py').resolve())
    state=x.root/'cli'
    for action in ['start','capture','undo']:
        if action=='capture': x.edit()
        args=[sys.executable,script,action,'--repo',str(x.p),'--session',str(state)]+(['app.txt'] if action=='undo' else [])
        r=subprocess.run(args,capture_output=True,text=True)
        print(action,r.returncode,r.stderr)
        assert r.returncode==0
finally:x.doCleanups()
