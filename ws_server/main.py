
import asyncio
import json
import os

import jwt
import websockets
from cryptography.fernet import Fernet
from datetime import datetime, timezone

from shared.db import database
from shared.logging import logger
from shared.server_settings import server_settings



fernet = Fernet(server_settings.fernet_key)

db = database.get_database()

file_cache = dict()

BOOKS_DIR = os.path.normpath(f'{os.getcwd()}/books')

# map teacher username to students + socket to ping updates to teachers
teacher_listeners = dict()

def decode_jwt(token):
    token = jwt.decode(token, server_settings.jwt_sercret_key, algorithms='HS256')
    exp_timestamp = token['exp']
    sub = token['sub']
    now = datetime.now(timezone.utc)
    if now.timestamp() > exp_timestamp:
        logger.error('expired token')
        raise ValueError()
    user = fernet.decrypt(sub.encode('utf-8')).decode('utf-8')
    return user

async def send_error(websocket, i):
    await websocket.send(json.dumps({'res': 'err', 'i': i}))


async def handle_incoming_packet(websocket, packet, user=None, book=None, is_admin=False):
    data = json.loads(packet)
    if data.get('cmd') == 'welcome':
        user = decode_jwt(data.get('Authorization', ''))
        book = data.get('book')
        if user.lower() in server_settings.admin_accounts:
            logger.warning(f'admin {user} connected to WS via book {book}')
        else:
            books = await db.get_student_books(user)
            if book not in books:
                logger.error(f'{user} tried to connect to book {book} through WS. Not allowed.')
                raise ValueError()
            logger.info(f'{user} connected to book {book}')
        return ['welcome', user, book]
    elif data.get('cmd') == 'set-result':
        id = data.get('id', None)
        outcome = data.get('outcome', False)
        code = data.get('code', '')
        is_long = data.get('is_long')
        if not is_long:
            code = code[:4000]
        if user and book and id:
            await db.save_result(book, id, user, outcome, code)
            user_norm = user.split('@')[0].lower()
            for teacher in teacher_listeners:
                if user_norm in teacher_listeners[teacher][0]:
                    await teacher_listeners[teacher][1].send(json.dumps({'cmd': 'teacher-update', 'code': code, 'outcome': outcome, 'ch-id': id, 'student': user_norm}))
    elif data.get('cmd') == 'get-results':
        if user and book:
            results = await db.get_results_for_user(book, user)
            await websocket.send(json.dumps({'res': 'succ', 'data': results, 'i': data.get('i')}, default=str))
    elif data.get('cmd') == 'fetch':
        path: str = data.get('path')
        i = data.get('i')
        if not path.startswith(server_settings.site_url + '/books'):
            await send_error(websocket, i)
            return
        path = path[len(server_settings.site_url + '/books'):]

        local_path = os.path.normpath(f'{BOOKS_DIR}{path}')
        if local_path in file_cache:
            data = file_cache[local_path]
        else:
            # fetch from file...
            if not os.path.exists(local_path) or not os.path.isfile(local_path):
                await send_error(websocket, i)
                return
            ext = os.path.splitext(local_path)[1]
            if ext not in ['.md', '.py', '.json', '.txt']:
                # only serving text files here
                await send_error(websocket, i)
                return
            with open(local_path, 'r') as f:
                data = f.read()
                file_cache[local_path] = data
        await websocket.send(json.dumps({'res': 'succ', 'data': data, 'i': i}))
    elif data.get('cmd') == 'reg-teacher-group':
        students: str = data.get('students')
        if not is_admin:
            await send_error(websocket, i)
            return
        if students:
            teacher_listeners[user] = (students, websocket)
        elif user in teacher_listeners:
            del teacher_listeners[user]


async def results(websocket):
    user = None
    try:
        logger.info(f'Incoming connection')
        cmd, user, book = await handle_incoming_packet(websocket, await websocket.recv())
        is_admin = user.lower() in server_settings.admin_accounts
        assert (cmd == 'welcome')
        async for message in websocket:
            await handle_incoming_packet(websocket, message, user, book, is_admin)

    except Exception as e:
        logger.error(f'terminated results connection with exception {e}')
    finally:
        if user:
            if user in teacher_listeners:
                del teacher_listeners[user]
        print('terminating connection')

async def main():
     async with websockets.serve(results, 'localhost', 5002):
        print("✅ WebSocket server started on ws://localhost:5002")
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    logger.info('Starting websocket server')
    if server_settings.is_debug:
        logger.warning('WARNING: THIS SERVER IS RUNNING IN DEBUG MODE. THIS SHOULD ONLY HAPPEN WHEN TESTING ON LOCALHOST')
    asyncio.run(main())
