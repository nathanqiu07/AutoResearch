#!/usr/bin/env python3
"""Independent synthetic controls; never reads production payload/archive paths."""
import argparse, contextlib, hashlib, importlib.util, io, json, os
from pathlib import Path
import stat, sys, tarfile, tempfile, unittest
from unittest import mock

PIN='68e9550f742416e68fba295a16f12d65d27651f6e048f982292ed126f4da82bf'
p=argparse.ArgumentParser();p.add_argument('--code',required=True);p.add_argument('--out',required=True);a=p.parse_args()
code=Path(a.code);before=code.read_bytes();assert hashlib.sha256(before).hexdigest()==PIN
spec=importlib.util.spec_from_file_location('retention_subject',code);s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def sha(b):return hashlib.sha256(b).hexdigest()
class IndependentControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.private=self.root/'private';self.private.mkdir(mode=0o700)
 def tearDown(self):self.tmp.cleanup()
 def row(self,name,data,roles=None):
  path=self.root/name;path.write_bytes(data);return {'path':str(path),'sha256':sha(data),'logical_size_bytes_observed':len(data),'roles':roles or ['synthetic.input']}
 def retain(self,rows,excluded=None,reuse=None,old=None):
  return s.retain(rows,excluded or [],reuse or {'members':[]},old,self.private/'new.tar.gz')
 def test_reused_original_is_rehashed_and_not_assumed_from_archive(self):
  r=self.row('reused',b'old');blob=s.pack_objects({r['sha256']:b'old'});old=self.private/'old.tar.gz';old.write_bytes(blob);old.chmod(0o600)
  reuse={'archive_sha256':sha(blob),'members':[{'source_path':r['path'],'archive_member':'objects/'+r['sha256'],'sha256':r['sha256'],'size_bytes':3}]}
  Path(r['path']).write_bytes(b'bad')
  with self.assertRaisesRegex(s.BoundaryError,'approved_source_pin_mismatch'):self.retain([r],reuse=reuse,old=old)
  self.assertFalse((self.private/'new.tar.gz').exists())
 def test_every_duplicate_is_read_twice_exclusions_never_opened_no_body_json(self):
  x=self.row('x',b'\x00NOT-JSON\xff',['a','b']);y=self.row('y',b'\x00NOT-JSON\xff',['c']);trap=dict(x,path=str(self.root/'excluded-do-not-open'))
  real=s.read_regular;seen=[]
  def read(path):
   seen.append(str(path));self.assertNotEqual(str(path),trap['path']);return real(path)
  with mock.patch.object(s,'read_regular',side_effect=read),mock.patch.object(s.json,'loads',side_effect=AssertionError('body parsed')):
   r=self.retain([x,y],excluded=[trap])
  self.assertEqual(seen.count(x['path']),2);self.assertEqual(seen.count(y['path']),2);self.assertEqual(r['new_member_count'],1)
  self.assertEqual([v['roles'] for v in r['logical_inputs']],[['a','b'],['c']]);self.assertNotIn(trap['path'],seen)
 def test_same_bytes_replaced_inode_is_stopped_after_private_write(self):
  r=self.row('source',b'same');real=s.read_regular;n=0
  def read(path):
   nonlocal n
   if str(path)==r['path']:
    n+=1
    if n==2:
     tmp=self.root/'replacement';tmp.write_bytes(b'same');os.replace(tmp,path)
   return real(path)
  with mock.patch.object(s,'read_regular',side_effect=read):
   with self.assertRaisesRegex(s.BoundaryError,'original_changed_after_copy'):self.retain([r])
  self.assertEqual(stat.S_IMODE((self.private/'new.tar.gz').stat().st_mode),0o600)
 def test_control_changed_without_pin_refresh_is_rejected(self):
  p=self.root/'control';p.write_bytes(b'{}');raw,state=s.read_regular(p);p.write_bytes(b'[]')
  with self.assertRaisesRegex(s.BoundaryError,'control_changed_during_operation'):s.unchanged_controls({'synthetic':(p,raw,state)})
 def test_duplicate_tar_member_is_rejected(self):
  b=io.BytesIO();name='objects/'+sha(b'x')
  with tarfile.open(fileobj=b,mode='w:gz',format=tarfile.USTAR_FORMAT) as t:
   for _ in range(2):
    m=tarfile.TarInfo(name);m.mode=0o600;m.size=1;t.addfile(m,io.BytesIO(b'x'))
  with self.assertRaisesRegex(s.BoundaryError,'archive_inventory_mismatch'):s.verify_tar(b.getvalue(),{name:{'sha256':sha(b'x'),'size_bytes':1}})
 def test_failure_receipt_never_contains_unexpected_exception_body(self):
  out=self.root/'failure';argv=['synthetic','verify','--allowlist','/never-read/allow','--custody','/never-read/custody','--reuse-receipt','/never-read/receipt','--reuse-archive','/never-read/old','--out',str(out),'--receipt','/never-read/saved','--archive','/never-read/new']
  err=io.StringIO()
  with mock.patch.object(sys,'argv',argv),mock.patch.object(s,'controls',return_value=({'allowed':[]},{},{})),mock.patch.object(s,'verify_saved',side_effect=ValueError('SYNTHETIC_PRIVATE_PROSE_DO_NOT_EXPORT')),contextlib.redirect_stderr(err):
   self.assertEqual(s.main(),1)
  b=(out/'failure.json').read_bytes();self.assertNotIn(b'SYNTHETIC_PRIVATE_PROSE',b);self.assertNotIn('SYNTHETIC_PRIVATE_PROSE',err.getvalue());j=json.loads(b)
  self.assertEqual(j['reason_code'],'ValueError');self.assertTrue(j['no_success_claim']);self.assertEqual(stat.S_IMODE((out/'failure.json').stat().st_mode),0o600);self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o700)

# Synthetic core needs no process or socket access.
import socket
with mock.patch.object(s.subprocess,'run',side_effect=AssertionError('process denied')),mock.patch.object(socket,'socket',side_effect=AssertionError('socket denied')):
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls))
assert code.read_bytes()==before
out=Path(a.out);out.mkdir(mode=0o700,exist_ok=False)
report={'schema_version':'audit044-independent-synthetic-boundaries-v1','code_sha256':PIN,'code_unchanged':True,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'payloads':'generated synthetic bytes only','production_payloads_or_archives_opened':False,'process_and_socket_access_denied':True}
(out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');(out/'unittest.txt').write_text(stream.getvalue());print(json.dumps(report,sort_keys=True));sys.exit(not result.wasSuccessful())
