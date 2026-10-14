"""Educational Git guard. See README before use. No AI attribution inference."""
import argparse, hashlib, json, os, subprocess, tempfile, uuid
from pathlib import Path

class Refused(RuntimeError): pass

class Session:
    def __init__(self, repo, state):
        self.repo=Path(repo).resolve(); self.state=Path(state).resolve()
        if self.state==self.repo or self.repo in self.state.parents:
            raise Refused('session directory must be OUTSIDE repository')
    def git(self,*args,env=None,data=None):
        e=os.environ.copy()
        # Refuse inherited index overrides instead of operating on the wrong index.
        if 'GIT_INDEX_FILE' in e: raise Refused('unset GIT_INDEX_FILE first')
        e.update(env or {})
        r=subprocess.run(['git','--no-optional-locks','-C',str(self.repo),*args],input=data,capture_output=True,env=e)
        if r.returncode: raise Refused(r.stderr.decode('utf8',errors='replace').strip())
        return r.stdout
    def index(self):
        p=Path(self.git('rev-parse','--path-format=absolute','--git-path','index').decode().strip())
        return p.read_bytes()
    def head(self): return self.git('rev-parse','HEAD').decode().strip()
    def manifest(self):
        paths=set(self.git('ls-files','-z','--cached','--others','--exclude-standard').split(b'\0'))-{b''}
        result={}
        for raw in sorted(paths):
            n=raw.decode('utf8'); p=self.repo/n
            if p.is_symlink(): raise Refused('symlinks not supported')
            if p.is_file(): result[n]=hashlib.sha256(p.read_bytes()).hexdigest()
        return result
    def snapshot(self, label, token):
        with tempfile.TemporaryDirectory() as d:
            idx=Path(d)/'index'; idx.write_bytes(self.index())
            env={'GIT_INDEX_FILE':str(idx)}
            self.git('add','-A','--','.',env=env)
            tree=self.git('write-tree',env=env).decode().strip()
        self.git('update-ref',f'refs/agent-demo/{token}/{label}',tree)
        return tree
    def load(self):
        try: return json.loads((self.state/'session.json').read_text(encoding='utf8'))
        except FileNotFoundError: raise Refused('no baseline; run start BEFORE agent work')
    def save(self,m): (self.state/'session.json').write_text(json.dumps(m,indent=2),encoding='utf8')
    def check(self,m):
        if m['repo']!=str(self.repo): raise Refused('wrong repository')
        if self.head()!=m['head']: raise Refused('HEAD changed')
        if self.index()!=(self.state/'original.index').read_bytes(): raise Refused('index changed; manual review required')
    def start(self):
        if self.state.exists(): raise Refused('use a NEW session directory')
        if Path(self.git('rev-parse','--show-toplevel').decode().strip()).resolve()!=self.repo:
            raise Refused('run from repository root')
        cfg=subprocess.run(['git','-C',str(self.repo),'config','--get','core.autocrlf'],capture_output=True).stdout.strip()
        if cfg not in (b'',b'false'): raise Refused('demo requires core.autocrlf=false; do not change a real repo blindly')
        tracked=self.git('ls-files','--stage').decode()
        if '160000 ' in tracked or '120000 ' in tracked: raise Refused('submodules/symlinks not supported')
        if self.git('ls-files','-u'): raise Refused('unmerged index')
        names=self.manifest()
        if any(Path(n).name=='.gitattributes' for n in names): raise Refused('attributes/filters not supported by demo')
        self.state.mkdir(parents=True)
        (self.state/'original.index').write_bytes(self.index())
        token=uuid.uuid4().hex
        m={'repo':str(self.repo),'head':self.head(),'token':token,'before_files':names}
        m['before']=self.snapshot('before',token); self.check(m); self.save(m)
        return m
    def capture(self):
        m=self.load(); self.check(m)
        if 'after' in m: raise Refused('already captured; use a new session for new work')
        m['after_files']=self.manifest(); m['after']=self.snapshot('after',m['token']); self.check(m)
        m['changed']=[n for n in sorted(set(m['before_files'])|set(m['after_files'])) if m['before_files'].get(n)!=m['after_files'].get(n)]
        m['undone']=[]
        patch=self.patch(m,m['changed']) if m['changed'] else b''
        (self.state/'candidate.patch').write_bytes(patch); self.save(m)
        return m
    def patch(self,m,paths):
        return self.git('--literal-pathspecs','diff','--no-ext-diff','--no-textconv','--binary','--full-index','--no-renames',m['before'],m['after'],'--',*paths)
    def undo(self,paths):
        m=self.load(); self.check(m)
        if 'after' not in m: raise Refused('capture first')
        if not paths or len(paths)!=len(set(paths)): raise Refused('select explicit unique paths')
        current=self.manifest()
        for n in paths:
            if n not in m['changed'] or n in m['undone']: raise Refused('not an available captured path: '+n)
            if current.get(n)!=m['after_files'].get(n): raise Refused('file changed AFTER capture: '+n)
        patch=self.patch(m,paths)
        if not patch: raise Refused('no Git patch; filters or raw-byte-only changes unsupported')
        (self.state/'selected.patch').write_bytes(patch)
        self.git('apply','--reverse','--check','--whitespace=nowarn','-',data=patch)
        # Pause all writers. Preflight + apply is not an atomic transaction against other processes.
        self.check(m)
        self.git('apply','--reverse','--whitespace=nowarn','-',data=patch)
        for n in paths:
            if self.manifest().get(n)!=m['before_files'].get(n): raise Refused('post-apply mismatch; inspect session backup, do not retry blindly')
        self.check(m); m['undone']+=paths; self.save(m)
        return m

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['start','capture','undo']); p.add_argument('--repo',required=True); p.add_argument('--session',required=True); p.add_argument('paths',nargs='*')
    a=p.parse_args()
    try:
        s=Session(a.repo,a.session)
        m=s.undo(a.paths) if a.action=='undo' else getattr(s,a.action)()
        print(json.dumps(m,ensure_ascii=False,indent=2))
    except Refused as e: p.exit(2,'REFUSED: '+str(e)+'\n')
if __name__=='__main__': main()
