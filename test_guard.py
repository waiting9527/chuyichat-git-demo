import unittest, tempfile, subprocess
from pathlib import Path
from guard import Session, Refused

def git(p,*a):
    return subprocess.check_output(['git','-C',str(p),*a])

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.p=self.root/'repo'; self.p.mkdir()
        git(self.p,'init','-q'); git(self.p,'config','user.name','Demo'); git(self.p,'config','user.email','demo@example.invalid')
        git(self.p,'config','core.autocrlf','false')
        self.write('app.txt','base\nsetting=old\n'); self.write('other.txt','base\n')
        git(self.p,'add','.'); git(self.p,'commit','-qm','base')
        self.write('app.txt','user-staged\nsetting=old\n'); git(self.p,'add','app.txt')
        self.write('app.txt','user-staged\nsetting=old\nuser-unstaged\n')
        self.write('notes.txt','user-untracked\n')
        self.before=self.files(); self.index=(self.p/'.git/index').read_bytes()
        self.s=Session(self.p,self.root/'session')
    def write(self,n,t): (self.p/n).write_text(t,encoding='utf8',newline='\n')
    def files(self): return {p.name:p.read_bytes() for p in self.p.iterdir() if p.is_file()}
    def edit(self): self.write('app.txt','user-staged\nsetting=agent\nuser-unstaged\n')
    def test_full_undo_preserves_dirty_work_and_index(self):
        self.s.start(); self.edit(); self.write('agent.txt','new\n'); self.s.capture(); self.s.undo(['app.txt','agent.txt'])
        self.assertEqual(self.before,self.files()); self.assertEqual(self.index,(self.p/'.git/index').read_bytes())
    def test_select_one_file_keeps_other_agent_change(self):
        self.s.start(); self.edit(); self.write('other.txt','agent-other\n'); self.s.capture(); self.s.undo(['app.txt'])
        self.assertEqual(self.before['app.txt'],(self.p/'app.txt').read_bytes()); self.assertEqual(b'agent-other\n',(self.p/'other.txt').read_bytes())
    def test_existing_untracked_file_restored_not_deleted(self):
        self.s.start(); self.write('notes.txt','agent edits old notes\n'); self.s.capture(); self.s.undo(['notes.txt'])
        self.assertEqual(self.before,self.files())
    def test_agent_deletion_restores_dirty_content(self):
        self.s.start(); (self.p/'app.txt').unlink(); self.s.capture(); self.s.undo(['app.txt']); self.assertEqual(self.before,self.files())
    def test_later_same_file_edit_refuses_without_writes(self):
        self.s.start(); self.edit(); self.s.capture(); self.write('app.txt','later-user\n'); before=self.files()
        with self.assertRaises(Refused): self.s.undo(['app.txt'])
        self.assertEqual(before,self.files())
    def test_later_unrelated_file_edit_survives(self):
        self.s.start(); self.edit(); self.s.capture(); self.write('other.txt','later-user\n'); self.s.undo(['app.txt'])
        self.assertEqual(b'later-user\n',(self.p/'other.txt').read_bytes())
    def test_agent_staging_refuses_capture(self):
        self.s.start(); self.edit(); git(self.p,'add','app.txt'); before=self.files(); idx=(self.p/'.git/index').read_bytes()
        with self.assertRaises(Refused): self.s.capture()
        self.assertEqual(before,self.files()); self.assertEqual(idx,(self.p/'.git/index').read_bytes())
    def test_later_staging_refuses_undo(self):
        self.s.start(); self.edit(); self.s.capture(); git(self.p,'add','app.txt'); before=self.files()
        with self.assertRaises(Refused): self.s.undo(['app.txt'])
        self.assertEqual(before,self.files())
    def test_unknown_path_refuses_entire_selection(self):
        self.s.start(); self.edit(); self.s.capture(); before=self.files()
        with self.assertRaises(Refused): self.s.undo(['app.txt','notes.txt'])
        self.assertEqual(before,self.files())
    def test_no_baseline_no_capture(self):
        with self.assertRaises(Refused): self.s.capture()
    def test_binary_file_round_trip(self):
        self.s.start(); (self.p/'blob.bin').write_bytes(bytes(range(256))); self.s.capture(); self.s.undo(['blob.bin']); self.assertEqual(self.before,self.files())
    def test_repeated_undo_refuses(self):
        self.s.start(); self.edit(); self.s.capture(); self.s.undo(['app.txt'])
        with self.assertRaises(Refused): self.s.undo(['app.txt'])

if __name__=='__main__': unittest.main(verbosity=2)
