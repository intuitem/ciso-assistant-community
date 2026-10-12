"""Module for login rate limiting (bruteforce protection)."""

from dataclasses import dataclass
from collections import defaultdict
from typing import Final, Optional, ClassVar, cast
from pathlib import Path
from abc import ABC, abstractmethod
import threading
import ipaddress
import selectors
import socket
import fcntl
import time
import json
import enum

from global_settings.models import GlobalSettings
from global_settings.serializers import InfraConfigSerializer

from django.conf import settings

TIME_WINDOW_UNIT: Final[int] = 60
"""Granularity of the time window (in seconds) (for now time windows have a 1-minute time granularity)."""

@dataclass
class AuditLogLimit:
    RESET_TIME = 86400
    LOG_LIMIT = 200

    start_time: int
    log_count: int

    @staticmethod
    def create() -> AuditLogLimit:
        start_time = int(time.monotonic())
        log_count = 0
        return AuditLogLimit(start_time, log_count)

    def try_acquire(self) -> bool:
        """
        Increment the failed login audit log counter.

        Return `True` if the limit has been reached, return `False` otherwise.
        """
        current_time = int(time.monotonic())

        if (self.start_time + self.RESET_TIME) < current_time:
            self.start_time = current_time
            self.log_count = 0

        self.log_count += 1
        return self.log_count > self.LOG_LIMIT

@dataclass
class Settings:
    AUDIT_LOG_LIMIT = AuditLogLimit.create()

    max_failed_login_attempts: int = 15
    time_window_size: int = 1
    ban_time: int = 5 # 5*60(ban_time*time_window_size*TIME_WINDOWS_UNIT) = 300 (the ban time is of 300 seconds).

    def replace_with(self, new_settings: Settings) -> bool:
        """Return `true` if the settings actually changed (if any value changed)."""
        if self == new_settings:
            return False

        self.max_failed_login_attempts = new_settings.max_failed_login_attempts
        self.time_window_size = new_settings.time_window_size 
        self.ban_time = new_settings.ban_time 
        return True

    @staticmethod
    def from_infra_settings(infra_settings: Optional[GlobalSettings]) -> Settings:
        if infra_settings is not None:
            infra_config = dict(InfraConfigSerializer(infra_settings).data)
        else:
            infra_config = {}

        max_failed_login_attempts = infra_config.get("max_failed_login_attempts", InfraConfigSerializer.DEFAULT_MAX_FAILED_LOGIN_ATTEMPT)
        time_window_size = infra_config.get("time_window_size", InfraConfigSerializer.DEFAULT_TIME_WINDOW_SIZE)
        ban_time = infra_config.get("ban_time", InfraConfigSerializer.DEFAULT_BAN_TIME)

        return Settings(max_failed_login_attempts, time_window_size, ban_time)

    @staticmethod
    def create() -> Settings:
        try:
            infra_settings = GlobalSettings.objects.filter(name=GlobalSettings.Names.INFRA_CONFIG).first()
        except Exception:
            # The table may not exist yet.
            infra_settings = None
        return Settings.from_infra_settings(infra_settings)

# Defaults settings (modified by `_leader_thread` a leader thread is elected.).
SETTINGS = Settings.from_infra_settings(None)

@dataclass
class BanInfo:
    timestamp_window: int
    fail_count: int
    ban_until: Optional[int]

    @staticmethod
    def _get_timestamp_window() -> int:
        return int(time.monotonic() / (TIME_WINDOW_UNIT * SETTINGS.time_window_size))

    @staticmethod
    def create():
        timestamp_window = BanInfo._get_timestamp_window()
        ban_info = BanInfo(timestamp_window, 0, None)
        return ban_info

    def reset(self, new_timestamp_window: int):
        self.timestamp_window = new_timestamp_window
        self.fail_count = 0
        self.ban_until = None

    def is_banned(self, current_timestamp_window: int) -> bool:
        return self.ban_until is not None and self.ban_until >= current_timestamp_window

    def check_is_banned(self, *, increment_fail_count: bool) -> tuple[bool, bool]:
        """Return a tuple (`is_banned`, `is_newly_banned`)."""
        current_timestamp_window = BanInfo._get_timestamp_window()

        if self.is_banned(current_timestamp_window):
            return True, False

        elif self.timestamp_window < current_timestamp_window:
            self.reset(current_timestamp_window)

        if increment_fail_count:
            self.fail_count += 1
            if self.fail_count >= SETTINGS.max_failed_login_attempts:
                self.ban_until = current_timestamp_window + SETTINGS.ban_time

        is_banned = (self.ban_until is not None)
        is_newly_banned = is_banned
        return is_banned, is_newly_banned

@dataclass(frozen=True)
class IPLookupEntry:
    ip_address: str
    time_window: int

class RequestMethod(enum.StrEnum):
    IS_BANNED = "is_banned"
    REGISTER_FAILED_LOGIN = "register_failed_login"
    REFRESH_SETTINGS = "refresh_settings"

class Response(ABC):
    METHOD: RequestMethod

    _METHOD_MAP: ClassVar[dict[RequestMethod, type[Response]]] = {}

    def __init_subclass__(cls: type[Response]):
        _response_method = getattr(cls, "METHOD", None) #TRACE: cls.METHOD
        if not isinstance(_response_method, RequestMethod):
            raise TypeError(f"The '{cls.__name__}.METHOD' static class attribute MUST be of RequestMethod type.")

        Response._METHOD_MAP[_response_method] = cls
        return cls

    @abstractmethod
    def to_json(self) -> dict:
        pass

    def encode(self) -> bytes:
        data = self.to_json()
        response_data = {
            "method": str(self.METHOD),
            "result": data,
        }
        return json.dumps(response_data).encode()

    @staticmethod
    @abstractmethod
    def _from_json(data: dict) -> Optional[Response]:
        pass

    @classmethod
    def decode(cls, data: bytes) -> Optional[Response]:
        try:
            response_data = json.loads(data)
            method = response_data.get("method", "")
            request_method = RequestMethod(method)
            result = response_data.get("result", {})

            response_cls = Response._METHOD_MAP.get(request_method)
            if response_cls is None:
                return

            return response_cls._from_json(result)
        except Exception:
            return

@dataclass(frozen=True)
class ResponseIsBanned(Response):
    METHOD = RequestMethod.IS_BANNED

    is_banned: bool

    def to_json(self):
        return { "is_banned": self.is_banned }

    @staticmethod
    def _from_json(data: dict) -> Optional[ResponseIsBanned]:
        is_banned = data.get("is_banned", False)
        return ResponseIsBanned(is_banned)

@dataclass(frozen=True)
class ResponseRegisterFailedLogin(Response):
    METHOD = RequestMethod.REGISTER_FAILED_LOGIN

    create_audit_log: bool

    def to_json(self):
        return { "create_audit_log": self.create_audit_log }

    @staticmethod
    def _from_json(data: dict) -> Optional[ResponseRegisterFailedLogin]:
        create_audit_log = data.get("create_audit_log", False)
        return ResponseRegisterFailedLogin(create_audit_log)

@dataclass(frozen=True)
class ResponseRefreshSettings(Response):
    METHOD = RequestMethod.REFRESH_SETTINGS

    def to_json(self):
        return {}

    @staticmethod
    def _from_json(data: dict) -> Optional[ResponseRefreshSettings]:
        return ResponseRefreshSettings()

class Request(ABC):
    METHOD: RequestMethod

    _METHOD_MAP: ClassVar[dict[RequestMethod, type[Request]]] = {}

    def __init_subclass__(cls: type[Request]):
        request_method = getattr(cls, "METHOD", None) #TRACE: cls.METHOD
        if not isinstance(request_method, RequestMethod):
            raise TypeError(f"The '{cls.__name__}.METHOD' static class attribute MUST be of RequestMethod type.")

        Request._METHOD_MAP[request_method] = cls
        return cls

    @abstractmethod
    def _to_json_params(self) -> dict:
        pass

    def encode(self) -> bytes:
        json_params = self._to_json_params()
        json_data = {
            "method": self.METHOD,
            "params": json_params,
        }
        return json.dumps(json_data).encode()

    @staticmethod
    @abstractmethod
    def _from_json_params(params: dict) -> Optional[Request]:
        pass

    @classmethod
    def decode(cls, data: bytes) -> Optional[Request]:
        # { "method": ..., "params": {} }
        try:
            json_data = json.loads(data)
            method = json_data.get("method", "")
            request_method = RequestMethod(method)
            params = json_data.get("params")
            if not isinstance(params, dict):
                raise TypeError("The 'params' key MUST be a dict.")
        except Exception:
            return
        else:
            request_cls = Request._METHOD_MAP.get(request_method)
            if request_cls is not None:
                return request_cls._from_json_params(params)


@dataclass(frozen=True)
class RequestIsBanned(Request):
    METHOD = RequestMethod.IS_BANNED

    ip_address: str

    def _to_json_params(self) -> dict:
        return { "ip_address": self.ip_address }

    @staticmethod
    def _from_json_params(params: dict) -> Optional[RequestIsBanned]:
        ip_address = params.get("ip_address")
        if not isinstance(ip_address, str):
            return

        try:
            # Check if it's a valid IP address.
            _ = ipaddress.ip_address(ip_address)
        except Exception:
            return

        return RequestIsBanned(ip_address)

@dataclass(frozen=True)
class RequestRegisterFailedLogin(Request):
    METHOD = RequestMethod.REGISTER_FAILED_LOGIN

    ip_address: str
    email: Optional[str]

    def _to_json_params(self) -> dict:
        return { "ip_address": self.ip_address, "email": self.email }

    @staticmethod
    def _from_json_params(params: dict) -> Optional[RequestRegisterFailedLogin]:
        ip_address = params.get("ip_address")
        if not isinstance(ip_address, str):
            return

        email = params.get("email")
        if not isinstance(email, str):
            return

        try:
            # Check if it's a valid IP address.
            _ = ipaddress.ip_address(ip_address)
        except Exception:
            return

        return RequestRegisterFailedLogin(ip_address, email)

@dataclass(frozen=True)
class RequestRefreshSettings(Request):
    METHOD = RequestMethod.REFRESH_SETTINGS

    def _to_json_params(self) -> dict:
        return {}

    @staticmethod
    def _from_json_params(params: dict) -> Optional[RequestRefreshSettings]:
        return RequestRefreshSettings()

class RPCServer:
    def __init__(self, ban_cache: _BanCache):
        self._selector = selectors.DefaultSelector()
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        if _BanCache.UNIX_SOCKET_FILE_PATH.exists():
            _BanCache.UNIX_SOCKET_FILE_PATH.unlink()

        self._socket.bind(str(_BanCache.UNIX_SOCKET_FILE_PATH))
        self._socket.listen()
        self._socket.setblocking(False)
        self._selector.register(self._socket, selectors.EVENT_READ, self._handle_accept)
        self._ban_cache = ban_cache

    def _method_is_banned(self, request: RequestIsBanned) -> ResponseIsBanned:
        is_banned, create_audit_log = self._ban_cache._check_is_banned(request)
        return ResponseIsBanned(is_banned)

    def _method_register_failed_login(self, request: RequestRegisterFailedLogin) -> ResponseRegisterFailedLogin:
        _, create_audit_log = self._ban_cache._check_is_banned(request)
        return ResponseRegisterFailedLogin(create_audit_log)

    def _method_refresh_settings(self, request: RequestRefreshSettings) -> ResponseRefreshSettings:
        #TODO: The caller MUST provide the InfraSettings(or a subset of it) instead (via `RequestRefreshSettings`).
        infra_settings = GlobalSettings.objects.get(name=GlobalSettings.Names.INFRA_CONFIG)
        new_settings = Settings.from_infra_settings(infra_settings)

        has_changed = SETTINGS.replace_with(new_settings)
        if has_changed:
            # Ban cache entries with different settings are incompatible, so it's better to just flush them (when updating the settings).
            self._ban_cache._flush_all_entries()

        return ResponseRefreshSettings()

    def _handle_request(self, request: Request) -> Response:
        if isinstance(request, RequestIsBanned):
            return self._method_is_banned(request)
        elif isinstance(request, RequestRegisterFailedLogin):
            return self._method_register_failed_login(request)
        elif isinstance(request, RequestRefreshSettings):
            return self._method_refresh_settings(request)
        else:
            raise NotImplementedError(f"Unsupported method {request.METHOD}.")

    def _handle_read(self, conn: socket.socket):
        try:
            if not (encoded_request := conn.recv(4096)):
                self._selector.unregister(conn)
                conn.close()
                return

            request = Request.decode(encoded_request)
            if request is None:
                conn.sendall(json.dumps({ "error": True }).encode())
                return

            response = self._handle_request(request)
            encoded_response = response.encode()
            conn.sendall(encoded_response)
        except Exception:
            conn.sendall(json.dumps({ "error": True }).encode())

    def _handle_accept(self, server: socket.socket):
        client_conn, _ = server.accept()
        client_conn.setblocking(False)
        self._selector.register(client_conn, selectors.EVENT_READ, self._handle_read)

    def poll(self):
        try:
            for key, _ in self._selector.select():
                callback = key.data
                callback(key.fileobj)
        except Exception:
            pass

    def close(self):
        self._selector.close()
        self._socket.close()
        try:
            _BanCache.UNIX_SOCKET_FILE_PATH.unlink()
        except FileNotFoundError:
            pass


class _BanCache:
    """**WARNING**: This cache is NOT thread-safe, so only the main thread of each gunicorn worker process SHALL use it."""

    ENTRY_LIMIT: Final[int] = 65536
    LEADER_ELECTION_FILE_PATH: Final[Path] = settings.BASE_DIR / "leader_election.lock"
    UNIX_SOCKET_FILE_PATH: Final[Path] = settings.BASE_DIR / "cache.socket"
    #TODO: Think about user changing (time_window_size, max_failed_login_attempts, ban_time)
    # The user SHALL NOT be able to change `time_window_size` (adjusting max_failed_login_attempts and ban_time is enough)
    # What impact would it have at runtime (the InfraSetting changes MUST be communicated via the unix socket to be sure the cache settings are updated accordingly).

    def __init__(self):
        self.ip_to_ban_info: dict[str, BanInfo] = {}
        # self.ip_eviction_deque: deque[IPLookupEntry] = deque()
        self.eviction_cache: dict[int, set[str]] = defaultdict(set)
        """`hashmap(time_window => set[ip_address])`"""

        self._lock_file = open(_BanCache.LEADER_ELECTION_FILE_PATH, "w")

        self.conn = None
        self.is_leader = False
        self._leader_thread_handle: Optional[threading.Thread] = None
        self._try_become_leader()

    def _try_become_leader(self) -> bool:
        try:
            fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.is_leader = False
            return False

        self.is_leader = True
        thread = self._leader_thread_handle
        if thread is None or not thread.is_alive():
            self._leader_thread_handle = threading.Thread(
                target=self._leader_thread, daemon=True
            )
            self._leader_thread_handle.start()

        return True

    def _leader_thread(self):
        try:
            SETTINGS.replace_with(Settings.create())
            rpc_server = RPCServer(self)
        except Exception:
            self._release_leader_lock()
            raise

        try:
            while True:
                rpc_server.poll()
        finally:
            rpc_server.close()
            self._release_leader_lock()

    def _release_leader_lock(self):
        """Stop being the leader and releas the leader election lock."""
        self.is_leader = False
        try:
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
        except OSError:
            pass

    def _flush_all_entries(self):
        """Flush out all the cache data (reset the cache)."""
        self.ip_to_ban_info = {}
        self.eviction_cache = defaultdict(set)

    def _clean_stale_cache_entries(self, current_timestamp_window: int):
        timestamp_windows = list(self.eviction_cache.keys())

        for timestamp_window in timestamp_windows:
            if timestamp_window + SETTINGS.ban_time < current_timestamp_window:
                ip_address_set = self.eviction_cache.pop(timestamp_window)

                for ip_address in ip_address_set:
                    ban_info = self.ip_to_ban_info.get(ip_address)
                    if ban_info is not None:
                        if ban_info.timestamp_window < current_timestamp_window:
                            if not ban_info.is_banned(current_timestamp_window):
                                self.ip_to_ban_info.pop(ip_address, None)

    @staticmethod
    def _normalize_ip_address(ip_address: str) -> str:
        addr = ipaddress.ip_address(ip_address)
        if isinstance(addr, ipaddress.IPv6Address):
            if addr.ipv4_mapped:
                return str(addr.ipv4_mapped)
            # This is to avoid an attacker "bypassing" the rate-limiting by buying a single /64 ipv6 range.
            return str(ipaddress.ip_network(f"{addr}/64", strict=False).network_address)
        return str(addr)

    def _evict_one_ip_address(self):
        ip_address_to_evict = next(iter(self.ip_to_ban_info.keys()), "")
        self.ip_to_ban_info.pop(ip_address_to_evict, None)

        eviction_cache_evictions: list[int] = []

        for time_window, ip_address_set in self.eviction_cache.items():
            if ip_address_to_evict in ip_address_set:
                eviction_cache_evictions.append(time_window)

        eviction_cache_evictions.sort()

        for time_window in eviction_cache_evictions[:-1]:
            ip_address_set = self.eviction_cache.get(time_window, set())
            ip_address_set.discard(ip_address_to_evict)

    def _check_is_banned(self, request: RequestIsBanned | RequestRegisterFailedLogin) -> tuple[bool, bool]:
        """
        Return a (`is_banned, create_audit_log`) tuple.
        
        - `is_banned` is `True` if the `ip_address` of the `Request` is banned or `False` otherwise.
        - `create_audit_log` is `True` is failed login `LogEntry`(audit log) IP-ban should be created by the caller (RPC caller).
        """
        current_timestamp_window = BanInfo._get_timestamp_window()

        self._clean_stale_cache_entries(current_timestamp_window)

        ip_address = self._normalize_ip_address(request.ip_address)
        ban_info = self.ip_to_ban_info.get(ip_address)

        if ban_info is None:
            ban_info = BanInfo.create()
            self.ip_to_ban_info[ip_address] = ban_info
            self.eviction_cache[current_timestamp_window].add(ip_address)

            if len(self.ip_to_ban_info) > _BanCache.ENTRY_LIMIT:
                self._evict_one_ip_address()

        increment_fail_count = (request.METHOD == RequestMethod.REGISTER_FAILED_LOGIN)
        is_banned, is_newly_banned = ban_info.check_is_banned(increment_fail_count=increment_fail_count)

        create_audit_log = (is_newly_banned and isinstance(request, RequestRegisterFailedLogin) and Settings.AUDIT_LOG_LIMIT.try_acquire())
        return is_banned, create_audit_log

    def _close_connection(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _send_request(self, request: Request) -> Optional[Response]:
        """Return `True` if the `ip_address` of the request is banned, or `False` otherwise"""
        try:
            if self.conn is None:
                self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                self.conn.settimeout(0.2)
                self.conn.connect(str(_BanCache.UNIX_SOCKET_FILE_PATH))

            encoded_request = request.encode()
            self.conn.sendall(encoded_request)

            encoded_response = self.conn.recv(4096)
            if not encoded_response:
                # Peer closed the connection: the leader (or its thread) is gone.
                raise ConnectionResetError("rate limiting server closed the connection")
            response = Response.decode(encoded_response)
            return response

        except TimeoutError:
            # A slow leader doesn't mean the leader is down (so there's no election).
            self._close_connection()
            return
        except (OSError, ValueError):
            # ConnectionRefusedError / FileNotFoundError (socket file gone) / reset / EOF.
            self._close_connection()
            self._try_become_leader()
            return

    def is_banned(self, ip_address: str) -> bool:
        request = RequestIsBanned(ip_address)
        response = self._send_request(request)

        if response is None:
            return False

        return cast(ResponseIsBanned, response).is_banned

    def register_failed_login(self, ip_address: str, email: Optional[str]) -> bool:
        """Return `True` if a new failed login IP-ban `LogEntry`(audit log) should be created by the caller."""
        request = RequestRegisterFailedLogin(ip_address, email)
        response = self._send_request(request)
        if response is None:
            return False
        return cast(ResponseRegisterFailedLogin, response).create_audit_log

    def refresh_settings(self):
        request = RequestRefreshSettings()
        self._send_request(request)

_BAN_CACHE: Optional[_BanCache] = None
_BAN_CACHE_LOCK = threading.Lock()

def get_ban_cache() -> _BanCache:
    """Return the process-wide ban cache, creating it (and joining the leader election) on first use."""
    global _BAN_CACHE
    if _BAN_CACHE is None:
        with _BAN_CACHE_LOCK:
            if _BAN_CACHE is None:
                _BAN_CACHE = _BanCache()
    return _BAN_CACHE

