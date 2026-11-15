import tempfile,sys,unittest
from pathlib import Path
from unittest.mock import patch
import vmaf_hdr as h
class DecoderErrorTests(unittest.TestCase):
 def test_decoder_crash_not_reported_as_only_frame_mismatch(self):
  python=getattr(sys,'_base_executable',sys.executable)
  bad=[python,'-c','raise SystemExit(7)']
  good=[python,'-c','import sys;sys.stdout.buffer.write(bytes(16*16*3)*2)']
  worker=[python,'-c','import sys;sys.stdin.buffer.read()']
  children=[];popen=h.subprocess.Popen
  def track(*a,**kw):
   p=popen(*a,**kw);children.append(p);return p
  with tempfile.TemporaryDirectory() as d,patch.object(h,'worker_command',return_value=worker),patch.object(h.subprocess,'Popen',side_effect=track):
   with self.assertRaisesRegex(RuntimeError,r'Referenz-Decoder: Exitcode 7 \(0x00000007\)'):
    h.evaluate([bad,good],16,16,2,1,Path(d),Path(d)/'measurement.log',False)
  self.assertEqual(len(children),3);self.assertTrue(all(p.poll() is not None for p in children))
if __name__=='__main__':unittest.main()
