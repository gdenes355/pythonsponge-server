import datetime
import urllib.parse
from random import choices
from typing import Optional, List

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.field_path import FieldPath

from shared.db.database import Database
from shared.models import ClassModel


class FirestoreDatabase(Database):

    def __init__(self):
        super().__init__()
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        self.__firestore = firebase_admin.firestore_async.client()

        self.__user_books_cache = {}  # local cache of user to book. Rarely changes anyway

    async def save_result(self, book: str, user: str, challenge_id: str, outcome: bool, code: str):
        user_standardised = self._standardise_username(user)
        document_id = self._get_result_doc_id(book, user_standardised)
        document_ref = self.__firestore.collection('results').document(document_id)
        update = self._compute_result_update(outcome, code)
        await document_ref.set({
            'book': book,
            'user': user_standardised,
            challenge_id: update
        }, merge=True)

    async def get_results_for_user(self, book: str, user: str):
        book_id = self._get_result_doc_id(book, self._standardise_username(user)) 
        doc = await self.__firestore.collection('results').document(book_id).get()
        return doc._data
    
    async def get_results_for_users(self, book: str, users: List[str]):
        user_names_standardised = [self._standardise_username(user) for user in users]
        book_ids = [self._get_result_doc_id(book, username) for username in user_names_standardised]
        docs = self.__firestore.collection('results')\
            .where(FieldPath.document_id(), 'in', book_ids).stream()
        data = [doc._data async for doc in docs]
        usernames_with_res = set([d['user'] for d in data])
        for username in user_names_standardised:
            if username not in usernames_with_res:
                data.append({'user': username, 'book': book})
        names = [self.get_user_name_from_local_cache(d['user']) for d in data]
        if not all(names):
            await self.refresh_user_name_cache()
        for d in data:
            name = self.get_user_name_from_local_cache(d['user'])
            d['name'] = name if name else d['user']
        return data
    
    async def add_result_comment(self, user: str, book: str, challenge: str, comment: str):
        user_standardised = self._standardise_username(user)
        book_id = self._get_result_doc_id(book, user_standardised)
        document_ref = self.__firestore.collection('results').document(book_id)
        update = {
            'comment': comment,
        }
        await document_ref.set({
            'book': book,
            'user': user,
            challenge: update,
        }, merge=True)

    
    async def get_student_books(self, user: str):
        user_standardised = self._standardise_username(user)
        now = datetime.now()

        cache_line = self.__user_books_cache.get(user_standardised, None)
        if cache_line and (now - cache_line[0]).total_seconds() < 60:
            return cache_line[1]  # use cache if no more than 1 minute old

        books = set()
        classes = self.__firestore.collection('classes') \
            .where('active', '==', True) \
            .where('students', 'array_contains', user_standardised).stream()
        async for klass in classes:
            books.update(klass._data['books'])
        cache_line = (now, list(books))
        self.user_books_cache[user_standardised] = cache_line
        return cache_line[1]
    
    async def delete_user_names(self):
        doc = self.__firestore.collection('users').document('all')
        await doc.delete()
        self._user_cache = {}

    async def refresh_user_name_cache(self):
        self._user_cache = {}
        doc = await self.__firestore.collection('users').document('all').get()
        self._user_cache = doc._data

    async def get_classes(self, is_active: Optional[bool] = None) -> List[ClassModel]:
        classes = []
        docs = self.__firestore.collection('classes')
        if is_active is not None:
            docs = docs.where('active', '==', is_active)
        async for doc in docs.stream():
            classes.append(doc._data)
            classes[-1]['name'] = doc.id
        return classes
    
    async def get_class(self, class_name: str) -> ClassModel:
        doc = await self.__firestore.collection('classes').document(class_name).get()
        return ClassModel(name=class_name, **doc._data)
    
    async def add_class(self, class_name: str):
        doc = self.__firestore.collection('classes').document(class_name)
        join_code = ''.join(choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))
        await doc.set({'active': True, 'join_code': join_code,
                'books': [], 'students': []})
        
    async def patch_class_active(self, class_name: str, is_active: bool):
        doc = self.__firestore.collection('classes').document(class_name)
        update = {}
        if is_active is not None:
            update['active'] = is_active
        if update:
            await doc.set(update, merge=True)
    
    async def delete_class(self, class_name: str):
        await self.__firestore.collection('classes').document(class_name).delete()

    async def add_students_to_class(self, class_name: str, students: List[str]):
        users_standardised = [self._standardise_username(student) for student in students]
        await self.__firestore.collection('classes').document(class_name) \
                .set({'students': firestore.ArrayUnion(users_standardised)}, merge=True)
        
    async def delete_student_from_class(self, class_name: str, student: str):
        user_standardised = self._standardise_username(student)
        doc = self.__firestore.collection('classes').document(class_name)
        await doc.set({'students': firestore.ArrayRemove([user_standardised])}, merge=True)

    async def add_book_to_class(self, class_name: str, book: str, is_enabled: bool):
        doc = self.__firestore.collection('classes').document(class_name)
        if is_enabled:
            await doc.set({'books': firestore.ArrayUnion([book]), 'disabled_books': firestore.ArrayRemove([book])}, merge=True)
        else:
            await doc.set({'disabled_books': firestore.ArrayUnion([book]), 'books': firestore.ArrayRemove([book])}, merge=True)

    def _compute_result_update(self, outcome: bool, code: str):
        if outcome:
            return {
                'correct-code': code,
                'correct': True,
                'correct-date': firestore.SERVER_TIMESTAMP,
                'correct-attempts': firestore.Increment(1),
            }
        else:
            return {
                'wrong-code': code,
                'correct': False,
                'wrong-date': firestore.SERVER_TIMESTAMP,
                'wrong-attempts': firestore.Increment(1),
            }
        
    def _get_result_doc_id(self, book, user):
        return urllib.parse.quote_plus(f'{book}&{user.lower()}')
