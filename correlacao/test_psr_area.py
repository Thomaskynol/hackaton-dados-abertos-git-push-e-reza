"""Lacuna-seguro: parse_area/canonizar + agregacao PSR com NR_AREA_TOTAL.

Stdlib unittest only. Sem rede, sem Mongo, sem "base de dados/".
Roda com: python3 -m unittest discover -s correlacao -v
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canon import canonizar, ibge7z, parse_area
from psr import COLS_NECESSARIAS, agregar, main


class TestParseArea(unittest.TestCase):
    def test_vazio_e_hifen_none(self):
        self.assertIsNone(parse_area(""))
        self.assertIsNone(parse_area("-"))
        self.assertIsNone(parse_area(None))

    def test_virgula_decimal(self):
        self.assertEqual(parse_area("12,5"), 12.5)

    def test_milhar_br(self):
        self.assertEqual(parse_area("1.234,56"), 1234.56)

    def test_lixo_none(self):
        self.assertIsNone(parse_area("lixo"))


class TestCanonizar(unittest.TestCase):
    def test_hifen_e_acento(self):
        self.assertEqual(canonizar("Cana-de-açúcar"), "cana-de-acucar")

    def test_mojibake(self):
        self.assertEqual(canonizar("Cana-de-aÃ§Ãºcar"), "cana-de-acucar")

    def test_safra_distinta(self):
        self.assertNotEqual(canonizar("Milho 1ª"), canonizar("Milho 2ª"))
        self.assertEqual(canonizar("Milho 1ª"), "milho-1a")


class TestIbge7z(unittest.TestCase):
    def test_zfill(self):
        self.assertEqual(ibge7z("35306"), "0035306")
        self.assertEqual(ibge7z("3503208"), "3503208")
        self.assertEqual(ibge7z("35032080"), "3503208")
        self.assertEqual(ibge7z(""), "")


class TestPsrArea(unittest.TestCase):
    HEADER_COM_AREA = (";".join(COLS_NECESSARIAS)
                       + ";NM_SEGURADO;NR_DOCUMENTO_SEGURADO\n")
    HEADER_SEM_AREA = (";".join(c for c in COLS_NECESSARIAS
                                if c != "NR_AREA_TOTAL")
                       + ";NM_SEGURADO;NR_DOCUMENTO_SEGURADO\n")

    def _csv(self, header, linhas):
        fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                          encoding="latin1", newline="")
        fh.write(header)
        fh.writelines(linhas)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_whitelist_tem_area(self):
        self.assertIn("NR_AREA_TOTAL", COLS_NECESSARIAS)
        self.assertNotIn("NM_SEGURADO", COLS_NECESSARIAS)
        self.assertNotIn("NR_DOCUMENTO_SEGURADO", COLS_NECESSARIAS)

    def test_agregacao_pequena_vs_grande(self):
        path = self._csv(self.HEADER_COM_AREA, [
            "Araraquara;SP;Soja;2024;3503208;0;-;12,5;x;y\n",
            "Araraquara;SP;Soja;2024;3503208;0;-;200,0;x;y\n",
        ])
        grupos, linhas, _ = agregar([path])
        g = grupos[("3503208", "SP", "Araraquara", "soja", 2024)]
        self.assertEqual(linhas, 2)
        self.assertEqual(g["apolices"], 2)
        self.assertEqual(g["apolices_pequenas"], 1)
        self.assertAlmostEqual(g["area_pequena_ha"], 12.5)
        self.assertAlmostEqual(g["area_total_ha"], 212.5)

    def test_limiar_50_inclusivo(self):
        path = self._csv(self.HEADER_COM_AREA, [
            "X;SP;Milho;2024;3503208;0;-;50,0;x;y\n",
            "X;SP;Milho;2024;3503208;0;-;50,01;x;y\n",
        ])
        grupos, _, _ = agregar([path])
        g = grupos[("3503208", "SP", "X", "milho", 2024)]
        self.assertEqual(g["apolices_pequenas"], 1)
        self.assertAlmostEqual(g["area_pequena_ha"], 50.0)
        self.assertAlmostEqual(g["area_total_ha"], 100.01)

    def test_fallback_sem_coluna_area_nao_quebra(self):
        path = self._csv(self.HEADER_SEM_AREA, [
            "Araraquara;SP;Soja;2025;3503208;0;-;x;y\n",
        ])
        grupos, linhas, _ = agregar([path])
        self.assertEqual(linhas, 1)
        g = grupos[("3503208", "SP", "Araraquara", "soja", 2025)]
        self.assertEqual(g["apolices"], 1)
        self.assertEqual(g["apolices_pequenas"], 0)
        self.assertEqual(g["area_total_ha"], 0.0)

    def test_jsonl_tem_campos_area_e_sem_pii_e_zfill(self):
        path = self._csv(self.HEADER_COM_AREA, [
            "Araraquara;SP;Soja;2024;35306;0;-;12,5;FULANO;123456\n",
        ])
        # main() so aceita posicional (flags --out/--prov viram entrada);
        # usa cwd temporario + saidas default, sem mudar comportamento.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, prev)
        main([path])
        out = os.path.join(tmp.name, "correlacao", "output",
                           "psr_agregado.jsonl")
        with open(out, encoding="utf-8") as fh:
            docs = [json.loads(li) for li in fh if li.strip()]
        self.assertEqual(len(docs), 1)
        d = docs[0]
        self.assertEqual(d["cod_ibge"], "0035306")  # zfill(7)
        self.assertEqual(d["total_apolices_pequenas"], 1)
        self.assertAlmostEqual(d["area_pequena_ha"], 12.5)
        self.assertAlmostEqual(d["area_total_ha"], 12.5)
        blob = json.dumps(docs)
        for chave in ("FULANO", "123456", "NM_SEGURADO",
                      "NR_DOCUMENTO_SEGURADO"):
            self.assertNotIn(chave, blob)


if __name__ == "__main__":
    unittest.main()
