import copy, importlib.util, json, pathlib, shutil, tempfile, unittest
ROOT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('prototype', ROOT/'tools/prepare_axis_json.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_committed_axis_sources_build_exact_baseline(self):
  with tempfile.TemporaryDirectory() as td:
   out=pathlib.Path(td)/'site'
   records,_=m.build(ROOT,out)
   from merge_opportunities import LiteralParser
   baseline=LiteralParser((ROOT/'data.js').read_text()).records()[0]
   self.assertEqual(records,baseline)
   self.assertEqual(len(records),27)
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)/'repo'
  shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('opportunities','_site','__pycache__'))
  self.out=pathlib.Path(self.temp.name)/'site';m.initialize(self.root)
 def tearDown(self):self.temp.cleanup()
 def test_exact_preservation_and_public_artifacts(self):
  records,version=m.build(self.root,self.out)
  from merge_opportunities import LiteralParser
  baseline=LiteralParser((self.root/'data.js').read_text()).records()[0]
  self.assertEqual(records,baseline);self.assertEqual(len(records),27)
  self.assertEqual(set(p.name for p in self.out.iterdir()),{'index.html','data.js','.nojekyll'})
  self.assertIn('data.js?v='+version,(self.out/'index.html').read_text())
  self.assertIn('GENERAL_TAGS',(self.out/'index.html').read_text())
 def test_independent_additions_are_both_preserved(self):
  baseline,old=m.build(self.root,self.out)
  for axis in (1,2):
   p=self.root/f'opportunities/axis{axis}.json';items=m.load_json(p)
   record=copy.deepcopy(items[0]);record['name']=f'TEST ONLY {axis}';record['url']=f'https://example.org/test-{axis}'
   items.append(record);p.write_text(m.encoded(items))
  actual,new=m.build(self.root,self.out)
  self.assertEqual(actual[:27],baseline);self.assertEqual(len(actual),29);self.assertNotEqual(old,new)
 def test_duplicate_refused_without_overwriting_output(self):
  m.build(self.root,self.out);before=(self.out/'data.js').read_bytes()
  a=self.root/'opportunities/axis1.json';b=self.root/'opportunities/axis2.json'
  b.write_text(m.encoded(m.load_json(b)+[m.load_json(a)[0]]))
  with self.assertRaises(ValueError):m.build(self.root,self.out)
  self.assertEqual((self.out/'data.js').read_bytes(),before)
 def test_deletion_and_invalid_json_refused(self):
  a=self.root/'opportunities/axis1.json';items=m.load_json(a);a.write_text(m.encoded(items[1:]))
  with self.assertRaises(ValueError):m.build(self.root,self.out)
  a.write_text('{broken')
  with self.assertRaises(ValueError):m.build(self.root,self.out)
 def test_init_cannot_overwrite_sources(self):
  before=(self.root/'opportunities/axis1.json').read_bytes()
  with self.assertRaises(ValueError):m.initialize(self.root)
  self.assertEqual((self.root/'opportunities/axis1.json').read_bytes(),before)
 def test_stale_baseline_refused(self):
  shutil.rmtree(self.root/'opportunities');p=self.root/'data.js';p.write_text(p.read_text()+'\n')
  with self.assertRaises(ValueError):m.initialize(self.root)
if __name__=='__main__':unittest.main(verbosity=2)
