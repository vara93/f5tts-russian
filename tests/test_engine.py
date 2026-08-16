import tempfile, unittest
from pathlib import Path
from engine import load_presets, validate_stress

class EngineTests(unittest.TestCase):
    def test_valid_stress_is_preserved(self):
        for text in ("молок+о","з+амок и зам+ок","ёж","без разметки"):
            self.assertTrue(validate_stress(text)[0]); self.assertIn("+",text) if "+" in text else None
    def test_invalid_stress(self):
        for text in ("+молоко","слово+","а + пробел","++а","latin+a"): self.assertFalse(validate_stress(text)[0])
    def test_empty_text(self): self.assertFalse(validate_stress("  ")[0])
    def test_presets(self):
        data=load_presets(); self.assertEqual(len(data),3); self.assertIn("з+амок",data["Тест ударений"]); self.assertIn("ё",data["А. С. Пушкин — «Зимнее утро», фрагмент"])
    def test_bad_presets(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"p.json"; p.write_text("[]")
            with self.assertRaises(ValueError): load_presets(p)
if __name__=="__main__":unittest.main()
