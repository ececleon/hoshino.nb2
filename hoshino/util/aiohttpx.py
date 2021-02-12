'''
Author: AkiraXie
Date: 2021-01-30 01:37:42
LastEditors: AkiraXie
LastEditTime: 2021-02-13 01:09:52
Description: 
Github: http://github.com/AkiraXie/
'''
from aiohttp import ClientSession
from typing import Optional
from loguru import logger
from json import loads


class BaseResponse:
    def __init__(self, content=None, status_code=None, headers=None) -> None:
        self.content: Optional[bytes] = content
        self.status_code: Optional[int] = status_code
        self.headers: Optional[dict] = headers

    @property
    def json(self):
        try:
            return loads(self.content)
        except Exception as e:
            logger.exception(e)

    @property
    def text(self):
        try:
            return self.content.decode('utf8')
        except Exception as e:
            logger.exception(e)


async def get(url: str, *args, **kwargs) -> BaseResponse:
    kwargs.setdefault('verify_ssl', False)
    async with ClientSession() as session:
        async with session.get(url, *args, **kwargs) as resp:
            return BaseResponse(await resp.read(), resp.status, resp.headers)


async def post(url: str, *args, **kwargs) -> BaseResponse:
    kwargs.setdefault('verify_ssl', False)
    async with ClientSession() as session:
        async with session.post(url, *args, **kwargs) as resp:
            return BaseResponse(await resp.read(), resp.status, resp.headers)


async def head(url: str, *args, **kwargs) -> BaseResponse:
    kwargs.setdefault('verify_ssl', False)
    async with ClientSession() as session:
        async with session.head(url, *args, **kwargs) as resp:
            return BaseResponse(status_code=resp.status, headers=resp.headers)
