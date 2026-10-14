"""Creates only a new sandbox. Never edits an existing repository."""
import hashlib, json, subprocess, sys, uuid
from pathlib import Path
from guard import Session, Refused

ROOT=Path(__file__).resolve().parent

def main():
    run=ROOT/'runs'/uuid.uuid4().hex[:12]; repo=run/'repo'; repo.mkdir(parents=True)
    log=[]
    def say(t): print(t,flush=True); log.append(str(t))
    def command(*a):
        say('$ '+' '.join(a))
        r=subprocess.run(a,cwd=repo,capture_output=True,text=True,encoding='utf8')
        if r.stdout: say(r.stdout.rstrip())
        if r.stderr: say(r.stderr.rstrip())
        say('exit='+str(r.returncode))
        if r.returncode: raise RuntimeError('command failed')
        return r.stdout
    def write(n,t): (repo/n).write_text(t,encoding='utf8',newline='\n')
    def files(): return {p.name:p.read_bytes() for p in repo.iterdir() if p.is_file()}
    say('REAL GIT DEMO / scripted agent simulation / NOT a live Codex or Claude Code session')
    say('sandbox='+str(repo))
    command('git','--version'); command(sys.executable,'--version')
    command('git','init','-q'); command('git','config','user.name','ChuyiChat Demo'); command('git','config','user.email','demo@example.invalid'); command('git','config','core.autocrlf','false')
    base='TAX = 0\ndef total():\n    return 100 + TAX\n\nif __name__ == "__main__":\n    print(total())\n'
    write('app.py',base); write('feature.txt','feature=off\n'); command('git','add','.'); command('git','commit','-qm','initial runnable demo')
    staged=base.replace('TAX = 0','TAX = 2'); write('app.py',staged); command('git','add','app.py')
    dirty=staged+'\n# user unfinished work\n'; write('app.py',dirty); write('notes.txt','user private draft\n')
    before=files(); index=(repo/'.git/index').read_bytes(); cached=command('git','diff','--cached','--binary')
    say('BEFORE: staged + unstaged + untracked')
    command('git','--no-optional-locks','status','--short'); command(sys.executable,'app.py')
    session=Session(repo,run/'session'); m=session.start(); say('baseline_tree='+m['before'])
    write('app.py',dirty.replace('return 100 + TAX','return 999 + TAX')); write('feature.txt','feature=on\n'); write('agent-new.txt','agent generated\n')
    say('AFTER scripted agent writes (no staging)'); command(sys.executable,'app.py')
    say('MIXED DIFF FROM HEAD (not Agent-only):'); command('git','diff','HEAD','--','app.py')
    m=session.capture(); say('after_tree='+m['after']); say('candidate_paths='+json.dumps(m['changed']))
    say('CAPTURED INCREMENT ONLY:'); say((run/'session/candidate.patch').read_text())
    session.undo(['app.py','agent-new.txt'])
    say('SELECTIVE UNDO app.py + agent-new.txt'); command(sys.executable,'app.py'); command('git','--no-optional-locks','status','--short')
    assert (repo/'app.py').read_bytes()==before['app.py']; say('PASS user staged + unstaged bytes preserved')
    assert (repo/'notes.txt').read_bytes()==before['notes.txt']; say('PASS original untracked notes preserved')
    assert not (repo/'agent-new.txt').exists(); say('PASS selected agent new file removed')
    assert (repo/'feature.txt').read_text()=='feature=on\n'; say('PASS unselected agent feature kept')
    assert (repo/'.git/index').read_bytes()==index; say('PASS original index byte-for-byte unchanged')
    assert command('git','diff','--cached','--binary')==cached; say('PASS staged diff unchanged')
    # A later user edit to an un-reverted agent path must stop rollback.
    write('feature.txt','feature=later-user\n'); check=files()
    try: session.undo(['feature.txt'])
    except Refused as e: say('EXPECTED REFUSAL: '+str(e))
    else: raise AssertionError('expected refusal')
    assert files()==check; say('PASS refusal wrote no working files')
    say('RESULT: 7/7 demo assertions passed')
    say('index_sha256='+hashlib.sha256(index).hexdigest())
    (run/'transcript.txt').write_text('\n'.join(log)+'\n',encoding='utf8')
    (ROOT/'evidence/latest-demo.txt').write_text('\n'.join(log)+'\n',encoding='utf8')
    (ROOT/'evidence/latest-run.json').write_text(json.dumps({'run':str(run),'repo':str(repo),'before':m['before'],'after':m['after']},indent=2),encoding='utf8')
    say('Evidence saved. Sandbox is retained; reruns create NEW directories.')

if __name__=='__main__': main()

