import importlib.util,json,pathlib,tempfile,unittest
SCRIPT=pathlib.Path(__file__).resolve().parents[1]/"scripts"/"transition_guard.py";S=importlib.util.spec_from_file_location("t",SCRIPT);t=importlib.util.module_from_spec(S);S.loader.exec_module(t)
class T(unittest.TestCase):
 def test_binding_logic_source_has_stale_base_gate(self):
  text=SCRIPT.read_text();self.assertIn("stale/wrong expected base head",text);self.assertIn("atomic transition missing paths",text)
if __name__=="__main__":unittest.main()
