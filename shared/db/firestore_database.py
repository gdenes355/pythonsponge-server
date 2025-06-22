from shared.db.database import Database
import urllib.parse

import firebase_admin
from firebase_admin import firestore, credentials, firestore_async
import datetime

class FirestoreDatabase(Database):

    def __init__(self):
        super().__init__()
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        self.__firestore = firebase_admin.firestore_async.client()

        self.__user_books_cache = {}  # local cache of user to book. Rarely changes anyway

    async def save_result(self, book: str, user: str, outcome: bool, code: str):
        user_standardised = self._standardise_username(user)
        document_id = self._get_result_doc_id(book, user_standardised)
        document_ref = self.__firestore.collection('results').document(document_id)
        update = self._compute_result_update(outcome, code)
        await document_ref.set({
            'book': book,
            'user': user_standardised,
            id: update
        }, merge=True)

    async def get_results(self, book: str, user: str):
        book_id = self._get_result_doc_id(book, self._standardise_username(user)) 
        doc = await self.__firestore.collection('results').document(book_id).get()
        return doc._data
    
    async def get_student_books(self, user: str):
        user_standardised = self._standardise_username(user)
        now = datetime.now()

        cache_line = self.__user_books_cache.get(user_standardised, None)
        if cache_line and (now - cache_line[0]).total_seconds() < 60:
            return cache_line[1]  # use cache if no mode than 1 minute old

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
        self.user_cache = {}
        doc = await self.__firestore.collection('users').document('all').get()
        self.user_cache = doc._data

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
