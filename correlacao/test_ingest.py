"""Testes da ingestao/correlacao (documento-mestre Sec. 5, 7.2, 9, 11).

Stdlib unittest only. Duas camadas:
- pura (fixtures sinteticas em memoria/tmp, sem I/O pesado);
- mongo (queries limitadas + contagens baratas; skip se mongo fora do ar).

NUNCA varre os JSONL/CSV gigantes. Roda com:
python3 -m unittest discover -s correlacao
"""
import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import zarc
from zarc import montar_doc

import psr
from psr import COLS_NECESSARIAS, agregar, num_br

import sigef
from sigef import (carregar_lookup, cultura_de_especie, norm_municipio)

import agrofit
from agrofit import flush, reassemble

import ana
from ana import code_str, col_idx
from ana import num as ana_num

import canon
from canon import cultura_canonica


def _zarc_row(**kw):
    row = {"Nome_cultura": "Milho 1ª Safra", "SafraIni": "2026",
           "SafraFin": "2027", "geocodigo": "3503208", "UF": "SP",
           "municipio": "Araraquara", "Portaria": "Portaria X",
           "Cod_Solo": "11", "Cod_Ciclo": "20", "Cod_Outros_Manejos": "1",
           "Cod_NM": ""}
    row.update(kw)
    for n in range(1, 37):
        row.setdefault(f"dec{n}", "0")
    return row


class TestZarcMontarDoc(unittest.TestCase):
    def test_dec_zero_excluido(self):
        row = _zarc_row(dec1="0", dec28="30", dec29="20")
        doc = montar_doc(row)
        self.assertEqual(doc["dec"], {"28": 30, "29": 20})
        self.assertEqual(doc["abertos"], [28, 29])
        self.assertEqual(doc["risco_min"], 20)
        self.assertEqual(doc["risco_max"], 30)

    def test_tudo_zero_sem_janela(self):
        doc = montar_doc(_zarc_row())
        self.assertEqual(doc["dec"], {})
        self.assertEqual(doc["abertos"], [])
        self.assertIsNone(doc["risco_min"])
        self.assertIsNone(doc["risco_max"])

    def test_nm_null_quando_cod_nm_vazio(self):
        self.assertIsNone(montar_doc(_zarc_row(Cod_NM=""))["nm"])

    def test_nm_numero_quando_presente(self):
        self.assertEqual(montar_doc(_zarc_row(Cod_NM="2"))["nm"], 2)

    def test_mapas_e_cultura(self):
        doc = montar_doc(_zarc_row(Cod_Solo="3", Cod_Ciclo="20",
                                   Cod_Outros_Manejos="1"))
        self.assertEqual(doc["solo_canonico"], "argiloso")
        self.assertEqual(doc["ciclo_grupo"], "grupo_i")
        self.assertEqual(doc["manejo_canonico"], "sequeiro")
        self.assertEqual(doc["cultura_canonica"], "milho")
        self.assertEqual(doc["cod_ibge"], "3503208")

    def test_mapa_desconhecido_vira_none(self):
        doc = montar_doc(_zarc_row(Cod_Solo="99", Cod_Ciclo="99"))
        self.assertIsNone(doc["solo_canonico"])
        self.assertIsNone(doc["ciclo_grupo"])


class TestPsrAgregacao(unittest.TestCase):
    HEADER = ("NM_MUNICIPIO_PROPRIEDADE;SG_UF_PROPRIEDADE;"
              "NM_CULTURA_GLOBAL;ANO_APOLICE;CD_GEOCMU;"
              "VALOR_INDENIZAÇÃO;EVENTO_PREPONDERANTE;"
              "NM_SEGURADO;NR_DOCUMENTO_SEGURADO\n")

    def _csv(self, linhas):
        fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                         encoding="latin1", newline="")
        fh.write(self.HEADER)
        fh.writelines(linhas)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_regra_sinistro_na_agregacao(self):
        path = self._csv([
            "Araraquara;SP;Soja;2025;3503208;0;-;x;y\n",      # sem sinistro
            "Araraquara;SP;Soja;2025;3503208;120587,38;SECA;x;y\n",  # sinistro
        ])
        grupos, linhas, sem_geo = agregar([path])
        g = grupos[("3503208", "SP", "Araraquara", "soja", 2025)]
        self.assertEqual(linhas, 2)
        self.assertEqual(g["apolices"], 2)
        self.assertEqual(g["sinistros"], 1)
        self.assertAlmostEqual(g["pago"], 120587.38)
        self.assertEqual(g["eventos"]["SECA"], 1)

    def test_pii_ignorada_na_leitura(self):
        # whitelist: PII passa pelo arquivo mas nunca entra no agregado
        path = self._csv([
            "Araraquara;SP;Milho;2025;3503208;0;-;FULANO;123456\n",
        ])
        grupos, _, _ = agregar([path])
        g = grupos[("3503208", "SP", "Araraquara", "milho", 2025)]
        for chave in ("FULANO", "123456", "NM_SEGURADO", "NR_DOCUMENTO_SEGURADO"):
            self.assertNotIn(chave, repr(g))
        self.assertNotIn("NM_SEGURADO", COLS_NECESSARIAS)
        self.assertNotIn("NR_DOCUMENTO_SEGURADO", COLS_NECESSARIAS)

    def test_num_br(self):
        self.assertEqual(num_br("120587,38"), 120587.38)
        self.assertEqual(num_br("9,5"), 9.5)
        self.assertEqual(num_br("-"), 0.0)
        self.assertEqual(num_br(""), 0.0)


class TestSigef(unittest.TestCase):
    def test_especie_para_cultura(self):
        self.assertEqual(cultura_de_especie("Glycine max (L.) Merr."), "soja")
        self.assertEqual(cultura_de_especie("Zea mays L."), "milho")
        self.assertEqual(cultura_de_especie("Triticum aestivum L."), "trigo")
        self.assertEqual(cultura_de_especie("Phaseolus vulgaris L."), "feijao")

    def test_especie_fallback_genero(self):
        # sem mapa -> genero em latim, nunca vazio/erro
        got = cultura_de_especie("Cajanus cajan (L.) Millsp.")
        self.assertTrue(got)

    def test_norm_municipio(self):
        self.assertEqual(norm_municipio("São Manuel"), "sao manuel")
        self.assertEqual(norm_municipio("  Porto  Real  "), "porto real")

    def test_lookup_arquivo_ausente(self):
        self.assertEqual(carregar_lookup("/tmp/inexistente-xyz.jsonl"), {})

    def test_num_br(self):
        self.assertEqual(sigef.num_br("9,5"), 9.5)
        self.assertEqual(sigef.num_br("-"), 0.0)


class TestAgrofitParse(unittest.TestCase):
    def _chunk(self, cultura="Algodao", tox="Categoria 4", tail="TRUE"):
        campos = ["12345", "MARCA", "FORM", "INGR", "TIT", "CLASSE", "MODO",
                  cultura, "PRAGA", "PRAGA_COMUM", "EMPRESA XYZ", tox, "AMB",
                  "NAO", tail]
        return ";".join(campos) + "\n"

    def test_um_registro_um_doc_sem_explode(self):
        stats = {"chunks": 0, "bad_tail": 0, "bad_reassemble": 0, "bad_nr": 0,
                 "dropped_chunk": 0, "cultura_com_sep": 0, "ok": 0}
        out = list(flush([self._chunk()], stats))
        self.assertEqual(len(out), 1)  # 1 registro logico -> 1 doc
        self.assertEqual(stats["ok"], 1)
        self.assertEqual(cultura_canonica(out[0][7]), "algodao")

    def test_cauda_nao_true_rejeitada(self):
        stats = {"chunks": 0, "bad_tail": 0, "bad_reassemble": 0, "bad_nr": 0,
                 "dropped_chunk": 0, "cultura_com_sep": 0, "ok": 0}
        out = list(flush([self._chunk(tail="FALSE")], stats))
        self.assertEqual(out, [])
        self.assertEqual(stats["bad_tail"], 1)

    def test_reassemble_incompleto_rejeitado(self):
        self.assertIsNone(reassemble("12345;SO-MARCA\n"))

    def test_tox_composto_via_flush(self):
        stats = {"chunks": 0, "bad_tail": 0, "bad_reassemble": 0, "bad_nr": 0,
                 "dropped_chunk": 0, "cultura_com_sep": 0, "ok": 0}
        out = list(flush(
            [self._chunk(tox="Categoria 4 - Produto Pouco Toxico")], stats))
        self.assertEqual(len(out), 1)
        self.assertEqual(canon.tox_numerica(out[0][11]), 4)


class TestAna(unittest.TestCase):
    def test_code_str_corta_extra(self):
        self.assertEqual(code_str("35032080"), "3503208")
        self.assertEqual(code_str("3503208"), "3503208")
        self.assertIsNone(code_str("ABC"))

    def test_num(self):
        self.assertEqual(ana_num("10"), 10)
        self.assertEqual(ana_num("9,5"), 9.5)
        self.assertIsNone(ana_num(""))
        self.assertIsNone(ana_num(None))

    def test_col_idx(self):
        self.assertEqual(col_idx("A1"), 0)
        self.assertEqual(col_idx("C10"), 2)


# --- Camada mongo: queries limitadas + contagens baratas (skip sem mongo) ---

def _db():
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure
    except ImportError:
        return None
    try:
        cli = MongoClient("mongodb://localhost:27017",
                          serverSelectionTimeoutMS=2000)
        cli.admin.command("ping")
        return cli["agropilot"]
    except ConnectionFailure:
        return None


DB = _db()

PII_PROIBIDO = {"NM_SEGURADO", "NR_DOCUMENTO_SEGURADO", "CPF", "CNPJ",
                "LATITUDE", "LONGITUDE", "LAT", "LON", "COORDENADAS"}


@unittest.skipIf(DB is None, "mongo localhost:27017 indisponivel")
class TestInvariantesMongo(unittest.TestCase):
    def test_dec_zero_nunca_em_risco(self):
        # Sec. 5.1: 0 = nao indicado, excluido de dec/abertos/risco_min/max
        self.assertEqual(DB.zarc.count_documents({"risco_min": 0}), 0)
        self.assertEqual(DB.zarc.count_documents({"risco_max": 0}), 0)
        self.assertEqual(DB.zarc.count_documents({"dec.1": 0}), 0)

    def test_nm_null_quando_cod_nm_vazio(self):
        amostra = list(DB.zarc.find({"Cod_NM": ""}, {"_id": 0, "nm": 1})
                       .limit(500))
        self.assertTrue(amostra)
        for d in amostra:
            self.assertIsNone(d["nm"])

    def test_psr_2025_zero_sinistros(self):
        # Sec. 5.2: 2025 nao satisfaz a regra -> nenhum sinistro valido
        self.assertEqual(
            DB.psr_agregado.count_documents({"total_sinistros": {"$gt": 0}}), 0)
        self.assertEqual(sorted(DB.psr_agregado.distinct("ano")), [2025])

    def test_psr_sem_pii(self):
        # Sec. 9: PII nunca entra no agregado
        for d in DB.psr_agregado.find({}, {"_id": 0}).limit(200):
            for chave in d:
                self.assertNotIn(chave.upper(), PII_PROIBIDO)
            for ev in d.get("por_evento", []):
                for chave in ev:
                    self.assertNotIn(chave.upper(), PII_PROIBIDO)

    def test_join_zarc_ana_99pct(self):
        zarc_ibges = set(DB.zarc.distinct("cod_ibge"))
        ana_ibges = set(DB.ana_atlas.distinct("cod_ibge"))
        self.assertTrue(zarc_ibges and ana_ibges)
        cobertura = len(zarc_ibges & ana_ibges) / len(zarc_ibges) * 100
        self.assertGreaterEqual(cobertura, 99.0)

    def test_join_sigef_ibge_98pct(self):
        total = DB.sigef_agregado.count_documents({})
        com_ibge = DB.sigef_agregado.count_documents(
            {"cod_ibge": {"$nin": ["", None]}})
        self.assertTrue(total > 0)
        self.assertGreaterEqual(com_ibge / total * 100, 98.0)

    def test_spot_araraquara_milho_ad1_3_ciclos(self):
        # Sec. 7.2: janela por ciclo, nao unica
        ciclos = sorted(DB.zarc.distinct(
            "Cod_Ciclo",
            {"cod_ibge": "3503208", "cultura_canonica": "milho",
             "solo_canonico": "ad1", "Nome_cultura": "Milho 1ª Safra"}))
        self.assertEqual(ciclos, ["20", "21", "22"])

    def test_contagens_baratas(self):
        for col in ("zarc", "municipios", "psr_agregado", "sigef_agregado",
                    "agrofit", "ana_atlas"):
            with self.subTest(col=col):
                self.assertGreater(DB[col].count_documents({}), 0)
        # hub municipios nasce do ZARC (Sec. 11): 1 doc por cod_ibge
        self.assertEqual(DB.municipios.count_documents({}),
                         len(DB.zarc.distinct("cod_ibge")))


if __name__ == "__main__":
    unittest.main()
