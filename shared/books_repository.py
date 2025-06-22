import json
import os

from shared.server_settings import server_settings


class BooksRepository:
    def __init__(self):
        self.book_title_cache = {}

    def get_local_book_titles(self, book_urls):
        res = {}
        for url in book_urls:
            book_path = url.replace(server_settings.site_url, '')
            if book_path not in self.book_title_cache:
                if not book_path.startswith('books/') and not book_path.startswith('/books/'):
                    self.book_title_cache[book_path] = None
                    continue
                local_path = os.path.normpath(f'{server_settings.server_dir}/{book_path}')
                if not os.path.exists(local_path):
                    self.book_title_cache[book_path] = None
                    continue
                try:
                    with open(local_path, 'r') as f:
                        book = json.loads(f.read())
                        self.book_title_cache[book_path] = book.get('name')
                except:
                    self.book_title_cache[book_path] = None
                    continue
            res[url] = self.book_title_cache[book_path]
        return res
