"""Fakes sem rede para testes unitários do backend (Mongo em memória mínimo).

Suporta o subconjunto usado pelas rotas: find_one/find (+sort/limit),
insert_one, update_one(upsert), create_index, aggregate(mat/group/sort/limit)
e operador $regex (buscar_municipio).
"""


class FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction=1):
        if isinstance(key, list):
            for k, d in reversed(key):
                self._docs.sort(
                    key=lambda x: (x.get(k) is None, x.get(k)),
                    reverse=(d < 0),
                )
        else:
            self._docs.sort(
                key=lambda x: (x.get(key) is None, x.get(key)),
                reverse=(direction < 0),
            )
        return self

    def limit(self, n):
        try:
            n = int(n)
        except (TypeError, ValueError):
            n = 0
        self._docs = self._docs[: max(0, n)]
        return self

    def __iter__(self):
        return iter(self._docs)

    def __len__(self):
        return len(self._docs)


def _match(doc, query):
    for k, v in (query or {}).items():
        if isinstance(v, dict) and "$regex" in v:
            import re

            flags = re.IGNORECASE if "i" in str(v.get("$options", "")) else 0
            if not re.search(str(v["$regex"]), str(doc.get(k) or ""), flags):
                return False
        elif isinstance(v, dict):
            return False  # operador não suportado no fake
        elif doc.get(k) != v:
            return False
    return True


class _Result:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeCol:
    def __init__(self, docs=None):
        self.docs = [dict(d) for d in (docs or [])]
        self.indexes = []

    def create_index(self, key, **kw):
        self.indexes.append((key, kw))
        return f"{key}_1"

    def find_one(self, query=None, *a, **k):
        for d in self.docs:
            if _match(d, query):
                return dict(d)
        return None

    def find(self, query=None, *a, **k):
        return FakeCursor([dict(d) for d in self.docs if _match(d, query)])

    def insert_one(self, doc):
        d = dict(doc)
        d.setdefault("_id", len(self.docs))
        self.docs.append(d)
        return _Result(inserted_id=d["_id"])

    def update_one(self, filtr, update, upsert=False):
        for d in self.docs:
            if _match(d, filtr):
                d.update(dict((update or {}).get("$set", {})))
                return _Result(matched_count=1, modified_count=1, upserted_id=None)
        if upsert:
            d = dict(filtr or {})
            d.update(dict((update or {}).get("$set", {})))
            d.setdefault("_id", len(self.docs))
            self.docs.append(d)
            return _Result(matched_count=0, modified_count=0, upserted_id=d["_id"])
        return _Result(matched_count=0, modified_count=0, upserted_id=None)

    def aggregate(self, pipeline):
        docs = list(self.docs)
        for stage in pipeline or []:
            if "$match" in stage:
                docs = [d for d in docs if _match(d, stage["$match"])]
            elif "$group" in stage:
                gid = stage["$group"].get("_id")
                groups = {}
                for d in docs:
                    key = d.get(gid[1:]) if isinstance(gid, str) and gid.startswith("$") else gid
                    groups[key] = groups.get(key, 0) + 1
                docs = [{"_id": k, "n": v} for k, v in groups.items()]
            elif "$sort" in stage:
                for k, direction in reversed(list(stage["$sort"].items())):
                    docs.sort(
                        key=lambda x: (x.get(k) is None, x.get(k)),
                        reverse=(direction < 0),
                    )
            elif "$limit" in stage:
                docs = docs[: stage["$limit"]]
        return docs

    def count_documents(self, query=None):
        return sum(1 for d in self.docs if _match(d, query))


_COLS = (
    "produtores",
    "sessoes",
    "mensagens",
    "memorias",
    "municipios",
    "zarc",
    "psr_agregado",
    "sigef_agregado",
    "ana_atlas",
    "agrofit",
    "precos_conab",
    "precos_meta",
)


class FakeDB:
    def __init__(self, **cols):
        for name in _COLS:
            setattr(self, name, cols.get(name) or FakeCol())

    def __getitem__(self, name):
        return getattr(self, name)


def make_db(**cols):
    """make_db(zarc=FakeCol([...]), ...) — demais coleções vazias."""
    return FakeDB(**cols)


import pytest


@pytest.fixture(autouse=True)
def _sem_rede_ibge(monkeypatch):
    """Testes unitários não tocam a rede: a atualização viva do IBGE fica OFF por
    padrão. Os testes de 'série viva' religam explicitamente com monkeypatch.setenv.
    """
    monkeypatch.setenv("IBGE_AUTO_UPDATE", "0")
