import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

from fixture_pii import scan_file, scan_text  # noqa: E402


class FixturePiiTest(unittest.TestCase):
    def kinds(self, text):
        return sorted({f["kind"] for f in scan_text(text)})

    def test_public_mail_provider_is_flagged(self):
        self.assertEqual(self.kinds('{"email": "maria.souza+pos@gmail.com"}'), ["email"])

    def test_synthetic_mail_passes(self):
        self.assertEqual(self.kinds('{"email": "aluno-p-1@exemplo.com", "e": "x@exemplo.test"}'), [])

    def test_real_city_and_uf_are_flagged(self):
        self.assertEqual(self.kinds('{"cidade": "Belém", "uf": "PA"}'), ["cidade", "uf"])

    def test_synthetic_city_passes(self):
        self.assertEqual(self.kinds('{"cidade": "Cidade Exemplo 5", "uf": "ZZ"}'), [])

    def test_full_name_is_flagged(self):
        self.assertEqual(self.kinds('{"nome": "Rafael Duarte Lima"}'), ["nome"])

    def test_pseudonym_passes(self):
        self.assertEqual(self.kinds('{"nome": "Aluno Exemplo 01", "name": "Aluno Exemplo"}'), [])

    def test_real_looking_phone_is_flagged(self):
        self.assertEqual(self.kinds('{"telefone": "98991419352"}'), ["telefone"])

    def test_fake_phone_range_passes(self):
        self.assertEqual(self.kinds('{"telefone": "11900000101", "fone": "11911111111"}'), [])

    def test_scan_file_reports_path_and_line(self):
        path = os.path.join(tempfile.mkdtemp(), "f.json")
        with open(path, "w") as f:
            f.write('{\n  "email": "joao@hotmail.com"\n}\n')
        found = scan_file(path)
        self.assertEqual([(x["kind"], x["line"]) for x in found], [("email", 2)])


if __name__ == "__main__":
    unittest.main()
