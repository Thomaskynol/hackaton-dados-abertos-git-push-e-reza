"""Conexão lazy com o MongoDB (db `agropilot`).

get_db() retorna None se pymongo ausente ou sem conexão — o backend
segue no mock e nunca quebra sem Mongo.
"""
import os

_client = None

DB_NAME = "agropilot"


def _mongo_url():
    return os.getenv("MONGO_URL", "mongodb://localhost:27017")


def get_db():
    global _client
    try:
        from pymongo import MongoClient
    except ImportError:
        return None
    if _client is None:
        try:
            _client = MongoClient(_mongo_url(), serverSelectionTimeoutMS=2000)
            _client.admin.command("ping")
        except Exception:
            _client = None
            return None
    try:
        _client.admin.command("ping")
    except Exception:
        return None
    return _client[DB_NAME]
