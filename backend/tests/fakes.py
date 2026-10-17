from copy import deepcopy
from types import SimpleNamespace

from pymongo.errors import PyMongoError


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, key, direction):
        self.documents.sort(key=lambda item: item[key], reverse=direction < 0)
        return self

    def limit(self, count):
        self.documents = self.documents[:count]
        return self

    def __iter__(self):
        return iter(self.documents)


class FakeCollection:
    def __init__(self):
        self.documents = []
        self.failure = None
        self.read_only = False

    def _raise_if_failed(self):
        if self.failure is not None:
            raise self.failure

    def _raise_if_read_only(self):
        if self.read_only:
            raise PyMongoError("simulated read-only collection")

    def create_index(self, *args, **kwargs):
        self._raise_if_failed()
        self._raise_if_read_only()
        return kwargs.get("name", "fake_index")

    def insert_one(self, document):
        self._raise_if_failed()
        self._raise_if_read_only()
        self.documents.append(deepcopy(document))
        return SimpleNamespace(inserted_id=document["_id"])

    def find(self, query):
        self._raise_if_failed()
        found = [
            deepcopy(document)
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        ]
        return FakeCursor(found)

    def find_one(self, query):
        self._raise_if_failed()
        return next(
            (
                deepcopy(document)
                for document in self.documents
                if all(document.get(key) == value for key, value in query.items())
            ),
            None,
        )

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        self._raise_if_failed()
        self._raise_if_read_only()
        document = next(
            (
                item
                for item in self.documents
                if all(item.get(key) == value for key, value in query.items())
            ),
            None,
        )
        if document is None and upsert:
            document = deepcopy(update.get("$setOnInsert", {}))
            document.update(query)
            self.documents.append(document)
        if document is None:
            return None
        document.update(deepcopy(update.get("$set", {})))
        for key in update.get("$unset", {}):
            document.pop(key, None)
        return deepcopy(document)

    def delete_one(self, query):
        self._raise_if_failed()
        self._raise_if_read_only()
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                del self.documents[index]
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


class FakeMongoClient:
    def __init__(self):
        self.fail_ping = False
        self.admin = self

    def command(self, command):
        if self.fail_ping:
            raise PyMongoError("simulated database outage")
        return {"ok": 1}
