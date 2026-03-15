from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED

security = HTTPBearer()


def check_token(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """
    Function that is used to validate the token in the case that it requires it
    """
    token = credentials.credentials
    if token is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    if len(token) != 31:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect auth token")

    return True
