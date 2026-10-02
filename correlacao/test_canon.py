"""Testes unitarios dos contratos canonicos (documento-mestre Sec. 5 e 11).

Stdlib unittest only. Sem mongo, sem arquivos: rapido e deterministico.
Roda com: python3 -m unittest discover -s correlacao
"""
import unittest

from canon import (CICLO_MAP, CLIMA_MAP, MANEJO_MAP, SOLO_MAP, cultura_canonica,
                   e_sinistro, ibge7, sem_acento, tox_numerica)


class TestMapasCanonicos(unittest.TestCase):
    def test_solo(self):
        self.assertEqual(SOLO_MAP,
                         {1: "arenoso", 2: "media", 3: "argiloso",
                          11: "ad1", 12: "ad2", 13: "ad3",
                          14: "ad4", 15: "ad5", 16: "ad6"})

    def test_manejo(self):
        self.assertEqual(MANEJO_MAP,
                         {1: "sequeiro", 2: "irrigado", 3: "irrigado_geada"})

    def test_ciclo(self):
        self.assertEqual(CICLO_MAP,
                         {13: "perene", 19: "semiperene", 20: "grupo_i",
                          21: "grupo_ii", 22: "grupo_iii", 24: "grupo_iv",
                          25: "grupo_v", 26: "grupo_vi"})

    def test_clima(self):
        self.assertEqual(CLIMA_MAP,
                         {0: "nao_se_aplica", 1: "alta_frio", 2: "media_frio",
                          3: "baixa_frio", 4: "semiarido", 5: "ameno",
                          6: "quente", 7: "tropical",
                          8: "subtropical_ameno", 9: "subtropical_frio",
                          11: "subtropical"})


class TestCulturaCanonicas(unittest.TestCase):
    def test_foco(self):
        self.assertEqual(cultura_canonica("Milho 1ª Safra"), "milho")
        self.assertEqual(cultura_canonica("Soja"), "soja")
        self.assertEqual(cultura_canonica("Feijão Cores"), "feijao")
        self.assertEqual(cultura_canonica("Arroz Sequeiro"), "arroz")
        self.assertEqual(cultura_canonica("Trigo"), "trigo")

    def test_primeiro_token_minusculo_sem_acento(self):
        self.assertEqual(cultura_canonica("Café Arábica"), "cafe")
        self.assertEqual(cultura_canonica("  Algodão  "), "algodao")

    def test_vazio(self):
        self.assertEqual(cultura_canonica(""), "")
        self.assertEqual(cultura_canonica(None), "")

    def test_sem_acento(self):
        self.assertEqual(sem_acento("Araraquara"), "Araraquara")
        self.assertEqual(sem_acento("Conceição"), "Conceicao")


class TestToxNumerica(unittest.TestCase):
    def test_rotulo_exato(self):
        self.assertEqual(tox_numerica("Categoria 4"), 4)
        self.assertEqual(tox_numerica("Categoria 1"), 1)
        self.assertEqual(tox_numerica("Categoria 5"), 5)

    def test_composto_com_descricao(self):
        # "Categoria 4 – Produto Pouco Tóxico" -> 4 (regex, nao igualdade)
        self.assertEqual(tox_numerica("Categoria 4 – Produto Pouco Tóxico"), 4)
        self.assertEqual(tox_numerica("Categoria 2 - Produto Altamente Tóxico"), 2)

    def test_nao_classificado_e_indeterminado(self):
        self.assertIsNone(tox_numerica("Não Classificado"))
        self.assertIsNone(tox_numerica("Nao Classificado - Agente microbiologico"))
        self.assertIsNone(tox_numerica("NÃO DETERMINADO"))
        self.assertIsNone(tox_numerica(""))
        self.assertIsNone(tox_numerica(None))

    def test_rotulos_antigos(self):
        self.assertEqual(tox_numerica("Extremamente Tóxico"), 1)
        self.assertEqual(tox_numerica("Altamente Tóxico"), 2)
        self.assertEqual(tox_numerica("Medianamente Tóxico"), 3)
        self.assertEqual(tox_numerica("Pouco Tóxico"), 4)

    def test_desconhecido_e_none(self):
        self.assertIsNone(tox_numerica("Produto Improvável de Causar Dano Agudo"))


class TestIbge7(unittest.TestCase):
    def test_corta_digito_extra_ana(self):
        self.assertEqual(ibge7("35032080"), "3503208")

    def test_sete_digitos_intacto(self):
        self.assertEqual(ibge7("3503208"), "3503208")

    def test_int_e_vazio(self):
        self.assertEqual(ibge7(3503208), "3503208")
        self.assertEqual(ibge7(""), "")
        self.assertEqual(ibge7(None), "")


class TestESinistro(unittest.TestCase):
    """Regra medida Sec. 5.2: evento preenchido E indenizacao > 0."""

    def test_sinistro_valido(self):
        self.assertTrue(e_sinistro("SECA", "120587,38"))
        self.assertTrue(e_sinistro("GEADA", "10.5"))

    def test_evento_ausente(self):
        self.assertFalse(e_sinistro("", "120587,38"))
        self.assertFalse(e_sinistro("-", "120587,38"))
        self.assertFalse(e_sinistro(None, "120587,38"))

    def test_valor_zerado_ou_ausente(self):
        self.assertFalse(e_sinistro("SECA", "0"))
        self.assertFalse(e_sinistro("SECA", "0,00"))
        self.assertFalse(e_sinistro("SECA", "-"))
        self.assertFalse(e_sinistro("SECA", ""))
        self.assertFalse(e_sinistro("SECA", None))
        self.assertFalse(e_sinistro("SECA", "lixo"))


if __name__ == "__main__":
    unittest.main()
