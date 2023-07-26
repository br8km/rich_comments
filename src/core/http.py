#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Smart HTTP Client."""

from time import time
from random import choice
from pathlib import Path
from typing import Any, Optional
from dataclasses import asdict, dataclass

import arrow
import orjson
import requests
from requests import Session, Response, RequestException
from dacite import from_dict

from ..base.io import IO
from ..base.debug import Debugger
from ..base.log import Logger

from ..utils.common import Utils


__all__ = (
    "HttpClient",
    "SmartHttpClient",
)



@dataclass
class AbsHttpData:
    """Http Data for Debugger."""

    time_stamp: float

    @property
    def time_str(self) -> str:
        """Get Timestamp String."""
        tz = "UTC+8"
        return arrow.get(self.time_stamp).to(tz).format()


@dataclass
class HttpRequest(AbsHttpData):
    """HTTP Client Request."""

    method: str  = ""

    url: str = ""
    params: dict = {}

    headers: dict = {}
    cookies: dict = {}


@dataclass
class HttpResponse(AbsHttpData):
    """HTTP Client Response."""

    success: bool = False
    code: int = 200

    url: str = ""

    headers: dict = {}
    cookies: dict = {}

    text: str = ""
    json: dict = {}


@dataclass
class ClientData:
    """HTTP Client Data for Debugger."""

    req: HttpRequest
    res: HttpResponse


class Http:
    """HTTP Client."""

    def __init__(self,
                 user_agent: str,
                 proxy_url: str,
                 timeout: int = 30,
                 logger: Optional[Logger] = None,
                 debugger: Optional[Debugger] = None,
                 ) -> None:
        """Init HTTP Client."""

        # user_agent Must be NOT empty
        assert user_agent

        self.user_agent = user_agent
        self.proxy_url = proxy_url

        self.logger = logger
        self.timeout = timeout
        self.debugger = debugger

        self.client = Session()
        self.client.headers.update({
            "User-Agent": user_agent,
        })
        if proxy_url:
            self.client.proxies = {
                "http":  proxy_url,
                "https": proxy_url,
            }

        self.data: ClientData 

    def header_set(self, key: str, value: Optional[str] = None) -> None:
        """set header for session"""
        if value is not None:
            self.client.headers[key] = value
        else:
            if key in self.client.headers.keys():
                del self.client.headers[key]

    def header_get(self, key: str) -> str:
        """Get header value for key string."""
        if key and key in self.client.headers.keys():
            value = self.client.headers[key]
            if value:
                return value
        return ""

    def h_accept(self, value: str = "*/*") -> None:
        """set heaer `Accept`"""
        self.header_set("Accept", value)

    def h_encoding(self, value: str = "gzip, defalte, br") -> None:
        """set header `Accept-Encoding`"""
        self.header_set("Accept-Encoding", value)

    def h_lang(self, value: str = "en-US,en;q=0.5") -> None:
        """set header `Accept-Language`"""
        self.header_set("Accept-Language", value)

    def h_origin(self, value: Optional[str] = None) -> None:
        """set header `Origin`"""
        self.header_set("Origin", value)

    def h_refer(self, value: Optional[str] = None) -> None:
        """set header `Referer`"""
        self.header_set("Referer", value)

    def h_type(self, value: Optional[str] = None) -> None:
        """set header `Content-Type`"""
        self.header_set("Content-Type", value)

    def h_xml(self, value: str = "XMLHttpRequest") -> None:
        """set header `X-Requested-With`"""
        self.header_set("X-Requested-With", value)

    def h_data(self, utf8: bool = True) -> None:
        """set header `Content-Type` for form data submit"""
        value = "application/x-www-form-urlencoded"
        if utf8 is True:
            value = f"{value}; charset=UTF-8"
        self.header_set("Content-Type", value)

    def h_json(self, utf8: bool = True) -> None:
        """set header `Content-Type` for json payload post"""
        value = "application/json"
        if utf8 is True:
            value = f"{value}; charset=UTF-8"
        self.header_set("Content-Type", value)

    def cookie_set(self, key: str, value: Optional[str]) -> None:
        """set cookie for session"""
        self.client.cookies.set(key, value)

    def cookie_load(self, file_cookie: Path) -> None:
        """load session cookie from local file"""
        if file_cookie.is_file():
            self.client.cookies.update(
                IO.load_dict(file_cookie)
            )

    def cookie_save(self, file_cookie: Path) -> None:
        """save session cookies into local file"""
        IO.save_dict(file_cookie, dict(self.client.cookies))

    def prepare_headers(self, **kwargs: Any) -> None:
        """set headers for following request"""
        if kwargs.get("json") is not None:
            self.h_json()
        elif kwargs.get("data") is not None:
            self.h_data()

        headers = kwargs.get("headers")
        if headers is not None:
            for key, value in headers.items():
                self.header_set(key, value)

    def save_req(
        self, method: str, url: str, debug: bool = False, **kwargs: Any
    ) -> None:
        """save request information into self.data"""
        if debug and self.debugger:
            params: dict[str, Any] = {}
            for key, value in kwargs.items():
                try:
                    orjson.dumps({"v": value})
                except TypeError:
                    value = str(value)
                params[key] = value

            cookies = dict(self.client.cookies.items())
            headers = dict(self.client.headers.items())
            time_stamp = int(time())

            self.data = ClientData(
                req=HttpRequest(
                    time_stamp=time_stamp,
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                ),
                res=HttpResponse(time_stamp=time_stamp)
            )
            self.debugger.id_add()
            self.debugger.save(data=asdict(self.data))

    def save_res(self, response: Response, debug: bool = False) -> None:
        """save http response into self.data"""
        if debug and self.debugger:
            cookies = dict(response.cookies.items())
            headers = dict(response.headers.items())
            try:
                res_json = orjson.loads(response.text)
            except orjson.JSONDecodeError:
                res_json = {}
            self.data.res.code = response.status_code
            self.data.res.success = response.ok
            self.data.res.url = response.url
            self.data.res.headers = headers
            self.data.res.cookies = cookies
            self.data.res.text = response.text
            self.data.res.json = res_json

            self.debugger.save(data=asdict(self.data))

    def req(
        self, method: str, url: str, debug: bool = False, **kwargs: Any
    ) -> Optional[Response]:
        """Preform HTTP Request"""
        response = None
        try:
            self.prepare_headers(**kwargs)
            self.save_req(method, url, debug, **kwargs)
            if not kwargs.get("timeout", None):
                kwargs["timeout"] = self.timeout
            with self.client.request(method, url, **kwargs) as response:
                code = response.status_code
                length = len(response.text)
                self.logger.info("[%d]<%d>%s", code, length, response.url)
                self.save_res(response, debug)
                return response
        except requests.RequestException as err:
            self.logger.exception(err)
        return response

    def get(self, url: str, debug: bool = False, **kwargs: Any) -> Optional[Response]:
        """HTTP GET"""
        return self.req("GET", url, debug=debug, **kwargs)

    def post(self, url: str, debug: bool = False, **kwargs: Any) -> Optional[Response]:
        """HTTP POST"""
        return self.req("POST", url, debug=debug, **kwargs)

    def head(self, url: str, debug: bool = False, **kwargs: Any) -> Optional[Response]:
        """HTTP HEAD"""
        return self.req("HEAD", url, debug=debug, **kwargs)

    def options(
        self, url: str, debug: bool = False, **kwargs: Any
    ) -> Optional[Response]:
        """HTTP OPTIONS"""
        return self.req("OPTIONS", url, debug=debug, **kwargs)

    def connect(
        self, url: str, debug: bool = False, **kwargs: Any
    ) -> Optional[Response]:
        """HTTP CONNECT"""
        return self.req("CONNECT", url, debug=debug, **kwargs)

    def put(self, url: str, debug: bool = False, **kwargs: Any) -> Optional[Response]:
        """HTTP PUT"""
        return self.req("PUT", url, debug=debug, **kwargs)

    def patch(self, url: str, debug: bool = False, **kwargs: Any) -> Optional[Response]:
        """HTTP PATCH"""
        return self.req("PATCH", url, debug=debug, **kwargs)

    def delete(
        self, url: str, debug: bool = False, **kwargs: Any
    ) -> Optional[Response]:
        """HTTP DELETE"""
        return self.req("DELETE", url, debug=debug, **kwargs)


class SmartHTTP:
    """Smart Http Client."""

    utils = Utils()

    def __init__(self,
                 file_user_agent: Path,
                 file_proxy_url: Path,
                 logger: Logger,
                 timeout: int = 30,
                 debugger: Optional[Debugger] = None,
                 ) -> None:
        """Init """
        self.file_user_agent = file_user_agent
        self.file_proxy_url = file_proxy_url

        self.logger = logger
        self.timeout = timeout
        self.debugger = debugger

        self.list_ua = self.load_user_agent()
        self.list_px = self.load_proxy()

        self.http = self.default_http()

    def load_user_agent(self) -> list[str]:
        """Load list of User-Ageng string."""
        return IO.load_line(
            file_name=self.file_user_agent,
            keyword="Mozilla",
        )

    def load_proxy(self) -> list[str]:
        """Load list of proxy string."""
        return IO.load_line(
            file_name=self.file_proxy_url,
            keyword="http",
        )

    def new_http(self, user_agent: str, proxy_url: str) -> Http:
        """Generate New HTTP."""
        return Http(
            user_agent=user_agent,
            proxy_url=proxy_url,
            timeou=self.timeout,
            logger=self.logger,
            debugger=self.debugger,
        )

    def rnd_http(self) -> Http:
        """Generate Random Http."""
        return self.new_http(
            user_agent=choice(self.list_ua),
            proxy_url=choice(self.list_px),
        )

    def default_http(self) -> Http:
        """Get Default Http."""
        return self.new_http(
            user_agent=self.list_ua[0],
            proxy_url=self.list_px[0],
        )

    def http_get_html(self, url: str, debug: bool = False, retry: int = 3) -> str:
        """HTTP GET Method to get html string from url."""
        for _ in range(retry):
            try:
                with self.http.get(url=url, debug=debug) as response:
                    if response:
                        return response.text
            except RequestException as err:
                if debug:
                    raise err
            self.utils.smart_delay(2)
        return ""

    def http_get_json(self, url: str, debug: bool = False, retry: int = 3) -> dict:
        """HTTP GET Method to get json dict from url."""
        for _ in range(retry):
            try:
                with self.http.get(url=url, debug=debug) as response:
                    if response:
                        return response.json()
            except RequestException as err:
                if debug:
                    raise err
            self.utils.smart_delay(2)
        return {}
