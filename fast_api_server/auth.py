import json
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import jwt
import requests
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from shared.db import database
from shared.models import AuthProvider
from shared.server_settings import server_settings

auth_router = APIRouter()

fernet = Fernet(server_settings.fernet_key)

db = database.get_database()

class TokenDto(BaseModel):
    msal_access_token: str
    bookUrl: Optional[str]



@auth_router.post('/token', tags=['Authentication'], summary='Authentication')
async def exchange_token(body: Optional[TokenDto]):
    """Exchange credentials or tokens to receive a JWT token."""
    book_url = body.bookUrl
    if not server_settings.is_debug and \
            book_url != f"{server_settings.site_url}/admin" and \
            book_url != f'{server_settings.site_url}/dashboard' and \
            (not book_url or not book_url.startswith(f'{server_settings.site_url}/books/')):
        raise HTTPException(status_code=403, detail='invalid book path')
    
    if server_settings.auth_provider == AuthProvider.MSAL:
        user = _ms_graph_me(body.msal_access_token)
    elif server_settings.auth_provider == AuthProvider.GOOGLE:
        user = _google_me(body.msal_access_token)
    else:
        raise HTTPException(status_code=403, detail='invalid auth provider')
    
    if not user:
        raise HTTPException(status_code=403, detail='cannot resolve token')

    name, email, = user
    # if not email.endswith('@myschool.com')
    #   return {'msg': 'invalid email domain'}, 403

    await db.meet_user(email, name)
    access_token = create_access_token(identity=email)
    return {'access_token': access_token}

@auth_router.post('logout', tags=['Authentication'], summary='Logout')
def logout():
    """End the current session."""
    # as we are authenticating with a Bearer token, we could ban-list the token
    pass



class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except Exception:
            return None  # Gracefully handle missing or invalid Authorization header

class AuthError(Exception):
    def __init__(self, reason: str):
        self.content = _get_auth_required_response(reason)

def register_auth_exception_handlers(app):
    @app.exception_handler(AuthError)
    async def auth_required_handler(request: Request, exc: AuthError):
        return JSONResponse(status_code=401, content=exc.content)
    


security = OptionalHTTPBearer()


def create_access_token(identity: str, expires_delta: timedelta = timedelta(hours=4)):
    identity_enc = fernet.encrypt(identity.encode('utf-8')).decode('utf-8')
    to_encode = {'sub': identity_enc}
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, server_settings.jwt_sercret_key, algorithm='HS256')
    return encoded_jwt


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not credentials:
        raise AuthError('jwt token required')
    token = credentials.credentials
    try:
        payload = jwt.decode(token, server_settings.jwt_sercret_key, algorithms=['HS256'])
        exp_timestamp = payload['exp']
        now = datetime.now(timezone.utc)
        if now.timestamp() > exp_timestamp:
            raise jwt.ExpiredSignatureError()
        sub = payload['sub']
        return fernet.decrypt(sub.encode('utf-8')).decode('utf-8')
    except jwt.ExpiredSignatureError:
        raise AuthError("jwt token expired")
    except jwt.InvalidTokenError:
        raise AuthError("jwt token invalid")

_google_keys = None
_google_keys_last_fetched = None
def _get_cached_google_keys():
    global _google_keys, _google_keys_last_fetched
    if _google_keys_last_fetched and _google_keys_last_fetched > datetime.now() - timedelta(hours=1):
        return _google_keys
    response = requests.get('https://www.googleapis.com/oauth2/v3/certs')
    if response.status_code != 200:
        return None
    keys = json.loads(response.text)['keys']
    res = {}
    for k in keys:
        kid = k['kid']
        res[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
    _google_keys = res
    _google_keys_last_fetched = datetime.now()
    return _google_keys

def _google_me(token: Optional[str]):
    if not token:
        raise HTTPException(status_code=401, detail='missing Google token')
                            
    # decode and verify the token
    header = jwt.get_unverified_header(token)
    algorithm = header['alg']
    kid = header['kid']
    keys = _get_cached_google_keys()
    if not keys:
        return None
    key = keys.get(kid, None)
    if not key:
        return None
    data = jwt.decode(token, key=key, algorithms=algorithm, verify=True, audience=server_settings.google_client_id)
    return (data['name'], data['email'])

def _ms_graph_me(token: Optional[str]):
    ''' fetch the user from MS Graph based on access token 
      return a tuple of (name, email) if the token is valid.
        othertiwse None
    '''
    if not token:
        raise HTTPException(status_code=401, detail='missing MSAL access token')

    response = requests.get('https://graph.microsoft.com/v1.0/me',
                            headers={'Authorization': f'Bearer {token}'})
    if response.status_code != 200:
        return None
    else:
        person = json.loads(response.text)
        surname = person.get('surname', '')
        given_name = person.get('givenName', '')
        displayName = person.get('displayName', '')
        name = f'{surname}, {given_name}' if surname and given_name else ''
        if displayName:
            try:
                displayName = re.sub(r"\(.*\)", "", displayName)
                displayName = displayName.split(" - ")[-1]
                displayName = displayName.strip()
                if displayName:
                    name = displayName
            finally:
                pass
        email = person.get('userPrincipalName', None)
        if not name or not email:
            return None
        return (name, email)

@lru_cache()
def _get_auth_required_response(reason: str):
    res = {
        'error': 'get-jwt',
        'reason': reason,
        'auth_provider': server_settings.auth_provider,
        'jwtEndpoint': f'{server_settings.site_url}/api/token/',
        'resultsEndpoint': f'{server_settings.site_url}/api/results/',
        'wsEndPoint': server_settings.ws_url,
    }
    if server_settings.auth_provider == AuthProvider.MSAL:
        res.update({
            'tenantId': server_settings.msal_tenant_id,
            'clientId': server_settings.msal_client_id,
        })
    elif server_settings.auth_provider == AuthProvider.GOOGLE:
        res.update({
            'clientId': server_settings.google_client_id,
        })
    return res
