import json
import os
from typing import List

from shared.models import BookNode
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
    
    def _book_path_to_local_path(self, book_path):
        book_path = book_path.replace(server_settings.site_url, '')
        return os.path.normpath(f'{server_settings.server_dir}/{book_path}')

    
    def load_book(self, path: str) -> BookNode:
        try:
            with open(self._book_path_to_local_path(path), 'r') as f:
                return BookNode(**json.load(f))
                # TODO: handle nested books (bookLink)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(e)
            return None
        
    # find list of nodes with tests associated with them
    def book_to_testable_node_list(self, node: BookNode, node_list: List[BookNode]=None):
        if node_list is None:
            node_list = []
        if node.isExample or node.typ == 'parsons' or node.tests or node.isAssessment and node.py:
            node_list.append(node)
        if node.children:
            for child in node.children:
                self.book_to_testable_node_list(child, node_list)
        return node_list
