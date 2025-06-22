from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Dict, Optional

class DatabaseType(StrEnum):
    FIRESTORE = 'firestore'


class Database(ABC):
    def __init__(self) -> None:
        self.book_title_cache = {}
        self._user_cache = {}

    @abstractmethod
    async def refresh_user_name_cache(self):
        pass

    @abstractmethod
    async def delete_user_names(self):
        pass

    @abstractmethod
    async def save_result(self, book: str, user: str, outcome: bool, code: str):
        pass

    @abstractmethod
    async def get_student_books(self, user: str):
        pass

    def _standardise_username(self, user: str):
        return user.split('@')[0].lower()

    def add_user_to_local_cache(self, user: str, name: str):
        self.user_cache[self._standardise_username(user)] = name

    def get_user_name_from_local_cache(self, user: str):
        return self._user_cache.get(self._standardise_username(user), None)


__db_cache: Dict[DatabaseType, Database] = {}
def get_database(t: DatabaseType = DatabaseType.FIRESTORE) -> Database:
    if t in __db_cache:
        return __db_cache[t]
    
    
    if t == DatabaseType.FIRESTORE:
        from shared.db.firestore_database import FirestoreDatabase
        __db_cache[t] = FirestoreDatabase()
    else:
        raise ValueError("Unexpected db type")
    return __db_cache[t]
