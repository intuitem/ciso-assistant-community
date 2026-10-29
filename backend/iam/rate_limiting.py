"""Module for login rate limiting (bruteforce protection)."""

from dataclasses import dataclass
from collections import defaultdict
from typing import Final, Optional, ClassVar, TextIO, cast
from pathlib import Path
from abc import ABC, abstractmethod
import threading
import ipaddress
import os
import stat
import selectors
import socket
import heapq
import fcntl
import struct
import time
import json
import enum

import structlog
from django.db import close_old_connections

from global_settings.models import GlobalSettings
from global_settings.serializers import RateLimitingConfigSerializer

logger = structlog.get_logger(__name__)


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

    def replace_with(self, new_settings: Settings) -> bool:
        """Return `true` if the settings actually changed (if any value changed)."""
        if self == new_settings:
            return False

        self.max_failed_login_attempts = new_settings.max_failed_login_attempts
        self.time_window_size = new_settings.time_window_size
        return True

    @staticmethod
    def from_rate_limiting_settings(
        rate_limiting_settings: Optional[GlobalSettings],
    ) -> Settings:
        if rate_limiting_settings is not None:
            rate_limiting_config = dict(
                RateLimitingConfigSerializer(rate_limiting_settings).data
            )
        else:
            rate_limiting_config = {}

        max_failed_login_attempts = rate_limiting_config.get(
            "max_failed_login_attempts",
            RateLimitingConfigSerializer.DEFAULT_MAX_FAILED_LOGIN_ATTEMPT,
        )
        time_window_size = rate_limiting_config.get(
            "time_window_size", RateLimitingConfigSerializer.DEFAULT_TIME_WINDOW_SIZE
        )

        return Settings(max_failed_login_attempts, time_window_size)

    @staticmethod
    def create() -> Settings:
        # We have to call `close_old_connections` to clean the DB connection ourselves.
        # (this is usually handled by django during the HTTP request handling process, but this code isn't handled within the context of handling a request).
        # Without this we may keep a broken connection to the DB after a DB failure.
        close_old_connections()
        try:
            rate_limiting_settings = GlobalSettings.objects.filter(
                name=GlobalSettings.Names.RATE_LIMITING
            ).first()
        except Exception:
            # The table may not exist yet.
            rate_limiting_settings = None
        finally:
            close_old_connections()
        return Settings.from_rate_limiting_settings(rate_limiting_settings)


# Defaults settings (modified by `_leader_thread` a leader thread is elected.).
SETTINGS = Settings.from_rate_limiting_settings(None)


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
        _response_method = getattr(cls, "METHOD", None)  # TRACE: cls.METHOD
        if not isinstance(_response_method, RequestMethod):
            raise TypeError(
                f"The '{cls.__name__}.METHOD' static class attribute MUST be of RequestMethod type."
            )

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
        return {"is_banned": self.is_banned}

    @staticmethod
    def _from_json(data: dict) -> Optional[ResponseIsBanned]:
        is_banned = data.get("is_banned", False)
        return ResponseIsBanned(is_banned)


@dataclass(frozen=True)
class ResponseRegisterFailedLogin(Response):
    METHOD = RequestMethod.REGISTER_FAILED_LOGIN

    create_audit_log: bool

    def to_json(self):
        return {"create_audit_log": self.create_audit_log}

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
        request_method = getattr(cls, "METHOD", None)  # TRACE: cls.METHOD
        if not isinstance(request_method, RequestMethod):
            raise TypeError(
                f"The '{cls.__name__}.METHOD' static class attribute MUST be of RequestMethod type."
            )

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
        return {"ip_address": self.ip_address}

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
        return {"ip_address": self.ip_address, "email": self.email}

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

    max_failed_login_attempts: int
    time_window_size: int

    @staticmethod
    def from_settings(settings: Settings) -> RequestRefreshSettings:
        return RequestRefreshSettings(
            settings.max_failed_login_attempts,
            settings.time_window_size,
        )

    def to_settings(self) -> Settings:
        return Settings(self.max_failed_login_attempts, self.time_window_size)

    def _to_json_params(self) -> dict:
        return {
            "max_failed_login_attempts": self.max_failed_login_attempts,
            "time_window_size": self.time_window_size,
        }

    @staticmethod
    def _from_json_params(params: dict) -> Optional[RequestRefreshSettings]:
        values: list[Optional[int]] = [
            params.get(name)
            for name in ["max_failed_login_attempts", "time_window_size"]
        ]

        if not all(isinstance(value, int) for value in values):
            # If any parameter isn't an int, the settings dict is invalid.
            return

        return RequestRefreshSettings(*cast(list[int], values))


class RPCSocket:
    """(Mandatory)Socket wrapper used to send/receive packet from the RPC-server."""

    def __init__(self, socket: socket.socket):
        self._socket = socket

    def send(self, packet: bytes):
        length = struct.pack("<I", len(packet))
        self._socket.sendall(length + packet)

    def send_error(self):
        self.send(json.dumps({"error": True}).encode())

    def _recv_until(self, length: int) -> tuple[bytes, bool]:
        """Return `(data, close_socket)`"""
        data = bytearray()
        remaining_length = length

        while remaining_length > 0:
            chunck = self._socket.recv(remaining_length)
            if chunck == b"":
                return b"", True

            data.extend(chunck)
            remaining_length = length - len(data)

        return bytes(data), False

    def recv(self) -> tuple[bytes, bool]:
        """Return `(packet, close_socket)`."""
        encoded_length, close_socket = self._recv_until(4)

        if close_socket:
            return b"", True

        length = struct.unpack("<I", encoded_length)[0]
        packet, close_socket = self._recv_until(length)

        if close_socket:
            return b"", True

        return packet, False

    def close(self):
        self._socket.close()


class RPCServer:
    POLL_TIMEOUT: Final[float] = 1.0
    """Max time (in seconds) a `poll()` blocks, so the leader can periodically run its health checks."""
    ACCEPT_BACKOFF: Final[float] = 0.1
    """Time (in seconds) the server socket stops being polled after a failed `accept()`."""

    def __init__(self, ban_cache: _BanCache):
        self._socket_file_path = ban_cache._socket_file_path
        self._selector = selectors.DefaultSelector()
        self._accept_resume_at: Optional[float] = None
        """When set, the listening socket is unregistered until this `time.monotonic()` deadline."""
        self._server_socket: Optional[socket.socket] = None
        self._socket_file_identity: Optional[tuple[int, int, int]] = None
        """`(st_dev, st_ino, st_ctime_ns)` of the socket file this server owns."""
        self._bind_socket()

        self._ban_cache = ban_cache

    def _bind_socket(self):
        _BanCache._ensure_runtime_dir()
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._socket_file_path.unlink(missing_ok=True)
            server_socket.bind(str(self._socket_file_path))
            server_socket.listen()
            st = os.stat(self._socket_file_path)
        except Exception:
            server_socket.close()
            raise

        self._server_socket = server_socket
        self._socket_file_identity = (st.st_dev, st.st_ino, st.st_ctime_ns)
        self._selector.register(
            server_socket, selectors.EVENT_READ, self._handle_accept
        )

    def _is_socket_file_owner(self) -> bool:
        """Return `True` if the server owns this socket file (and if the socket wasn't deleted/replaced in the meantime)."""
        try:
            st = os.stat(self._socket_file_path)
        except FileNotFoundError:
            return False
        return (st.st_dev, st.st_ino, st.st_ctime_ns) == self._socket_file_identity

    def _ensure_socket_exists(self):
        """
        Re-create the socket file if it was deleted/replaced by an external process.

        Already connected RPC clients are kept (they don't depend on the socket file).
        """
        if not self._is_socket_file_owner():
            if self._server_socket is not None:
                # A paused listening socket is already unregistered.
                if self._accept_resume_at is None:
                    self._selector.unregister(self._server_socket)
                self._server_socket.close()
                self._server_socket = None
                self._socket_file_identity = None

            self._accept_resume_at = None
            self._bind_socket()

    def _method_is_banned(self, request: RequestIsBanned) -> ResponseIsBanned:
        is_banned, create_audit_log = self._ban_cache._check_is_banned(request)
        return ResponseIsBanned(is_banned)

    def _method_register_failed_login(
        self, request: RequestRegisterFailedLogin
    ) -> ResponseRegisterFailedLogin:
        _, create_audit_log = self._ban_cache._check_is_banned(request)
        return ResponseRegisterFailedLogin(create_audit_log)

    def _method_refresh_settings(
        self, request: RequestRefreshSettings
    ) -> ResponseRefreshSettings:
        has_changed = SETTINGS.replace_with(request.to_settings())
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

    def _handle_read(self, _conn: socket.socket):
        conn = RPCSocket(_conn)
        try:
            encoded_request, close_socket = conn.recv()

            if close_socket:
                self._close_client(_conn)
                return

            request = Request.decode(encoded_request)
            if request is None:
                conn.send_error()
                return

            response = self._handle_request(request)
            encoded_response = response.encode()
            conn.send(encoded_response)

        except Exception:
            self._close_client(_conn)
            return

    def _close_client(self, _conn: socket.socket):
        self._selector.unregister(_conn)
        _conn.close()

    def _handle_accept(self, server: socket.socket):
        try:
            client_conn, _ = server.accept()
        except OSError as e:
            logger.error("Rate limiting RPC server accept failed", exc_info=e)
            self._selector.unregister(server)
            self._accept_resume_at = time.monotonic() + RPCServer.ACCEPT_BACKOFF
            return

        client_conn.settimeout(0.05)
        self._selector.register(client_conn, selectors.EVENT_READ, self._handle_read)

    def poll(self):
        """
        Poll the server socket to `accept` new connection AND the (connected)client sockets `read` to handle their requests.

        **WARNING**: If this function raises an `Exception`, the caller(the leader thread) MUST give up its leadership (to let another worker take it back).
        """
        timeout = RPCServer.POLL_TIMEOUT
        if self._accept_resume_at is not None:
            remaining = self._accept_resume_at - time.monotonic()
            if remaining <= 0:
                self._accept_resume_at = None
                if self._server_socket is not None:
                    self._selector.register(
                        self._server_socket, selectors.EVENT_READ, self._handle_accept
                    )
            else:
                timeout = min(timeout, remaining)

        for key, _ in self._selector.select(timeout=timeout):
            try:
                key.data(key.fileobj)
            except Exception as e:
                logger.error("Rate limiting RPC server callback failed", exc_info=e)

    def close(self):
        is_socket_file_owner = self._is_socket_file_owner()

        # A paused (`self._accepted_resume_at is None`) listening socket isn't registered in the selector.
        if self._accept_resume_at is not None and self._server_socket is not None:
            self._server_socket.close()

        # Closing the client connections makes the followers notice the leader is gone (and re-run the election).
        for key in list(self._selector.get_map().values()):
            try:
                key.fileobj.close()
            except OSError:
                pass
        self._selector.close()
        self._server_socket = None

        # Never unlink the socket file of another leader.
        if is_socket_file_owner:
            self._socket_file_path.unlink(missing_ok=True)


RUNTIME_DIR: Final[Path] = Path(
    os.environ.get("CISO_ASSISTANT_RUNTIME_DIR", "/tmp/ciso-assistant")
)


class _BanCache:
    # TODO: Remove `ENTRY_LIMIT` references from the whole file.
    # ENTRY_LIMIT: Final[int] = 65536
    HEALTH_CHECK_INTERVAL: Final[float] = 1.0

    def __init__(self):
        runtime_dir = _BanCache._ensure_runtime_dir()
        self._lock_file_path = runtime_dir / "leader_election.lock"
        self._socket_file_path = runtime_dir / "cache.socket"

        self.banned_ips: set[str] = set()
        """`hashmap(ip_address-str => ban_until(float))` (evicted by popping the `self.eviction_queue` min-heap)"""
        self.ip_to_fail_count: dict[
            str, int
        ] = {}  # hahsmap(ip => fail_count(int)) (reset for each new window)
        """`hahsmap(ip_address(str) => failed_login_count(int))` (all entries are flushed each time we enter a new time window)."""
        self.eviction_queue: list[tuple[float, str]] = []
        """min_heap(tuple[ban_until, ip])."""
        self.current_time_window = 0
        """Current time window (for `self.ip_to_fail_count`) (corresponds to: `time.monotonic() // (time_window_size*60)`)."""

        # TODO: (Also remove the `BanInfo` class now that it's useless)
        # TODO: REMOVE THE 2 FOLLOWING ATTRIBUTES FROM THIS CLASS:
        # self.ip_to_ban_info: dict[str, BanInfo] = {}
        # self.eviction_cache: dict[int, set[str]] = defaultdict(set)
        """`hashmap(time_window => set[ip_address])`"""

        self._lock_file_mutex = threading.Lock()
        """Mutex used to access `self._lock_file` (as we don't want the main/leader threads to have concurrent access to it)."""
        self._lock_file: TextIO = self._open_lock_file()

        self.conn = None
        self.is_leader = False
        self._leader_thread_handle: Optional[threading.Thread] = None
        self._try_become_leader()

    def _open_lock_file(self) -> TextIO:
        _BanCache._ensure_runtime_dir()
        return open(self._lock_file_path, "w")

    def _is_lock_file_owner(self) -> bool:
        """Return `True` if the lock file path still points to the lock file opened by this process, return `False` otherwise."""
        try:
            path_st = os.stat(self._lock_file_path)
        except FileNotFoundError:
            return False

        fd_st = os.fstat(self._lock_file.fileno())

        file_identity = (path_st.st_dev, path_st.st_ino, path_st.st_ctime_ns)
        opened_file_identity = (fd_st.st_dev, fd_st.st_ino, fd_st.st_ctime_ns)

        is_lock_file_unchanged = file_identity == opened_file_identity
        return is_lock_file_unchanged

    def _acquire_lock_file(self) -> bool:
        """
        Lock the lock file (re-creating it if needed), return `True` on success or `False` otherwise.

        **WARNING**: The caller MUST hold `_lock_file_mutex`.
        """
        for _ in range(3):
            if not self._is_lock_file_owner():
                new_lock_file = self._open_lock_file()
                # Closing the stale file releases any lock held on it (it's an orphan file anyway).
                self._lock_file.close()
                self._lock_file = new_lock_file

            try:
                fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False

            # The lock file may have been deleted between `open` and `flock`.
            if self._is_lock_file_owner():
                return True

        return False

    @staticmethod
    def _ensure_runtime_dir() -> Path:
        """Create the private runtime directory if missing (containing the lock file and unix socket)."""
        RUNTIME_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = RUNTIME_DIR.lstat()
        if (
            not stat.S_ISDIR(st.st_mode)
            or st.st_uid != os.getuid()
            or st.st_mode & 0o022
        ):
            raise PermissionError(
                f"Unsafe rate limiting runtime directory: {RUNTIME_DIR}"
            )
        return RUNTIME_DIR

    def _try_become_leader(self) -> bool:
        with self._lock_file_mutex:
            thread = self._leader_thread_handle
            if thread is not None and thread.is_alive():
                return self.is_leader

            if not self._acquire_lock_file():
                self.is_leader = False
            else:
                self.is_leader = True
                self._leader_thread_handle = threading.Thread(
                    target=self._leader_thread, daemon=True
                )
                self._leader_thread_handle.start()

        return self.is_leader

    def _leader_thread(self):
        try:
            SETTINGS.replace_with(Settings.create())
            rpc_server = RPCServer(self)
        except Exception:
            self._release_leader_lock()
            raise

        try:
            next_health_check = 0.0
            while True:
                now = time.monotonic()
                if now >= next_health_check:
                    if not self._leader_health_check(rpc_server):
                        break
                    next_health_check = now + _BanCache.HEALTH_CHECK_INTERVAL
                rpc_server.poll()
        finally:
            rpc_server.close()
            self._release_leader_lock()

    def _leader_health_check(self, rpc_server: RPCServer) -> bool:
        """
        Return `False` if this thead lost the leadership.

        **WARNING**: This function should only be used by the leader thread itself.
        """
        try:
            with self._lock_file_mutex:
                if not self._acquire_lock_file():
                    # Another process locked the re-created lock file first.
                    return False
            rpc_server._ensure_socket_exists()
        except Exception:
            # e.g. the runtime directory is temporarily unsafe/unwritable.
            pass
        return True

    def _release_leader_lock(self):
        """Stop being the leader and release the leader election lock."""
        with self._lock_file_mutex:
            self.is_leader = False
            try:
                fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            except OSError, ValueError:
                pass

    def _flush_all_entries(self):
        """Flush out all the cache data (reset the cache)."""
        self.banned_ips.clear()
        self.ip_to_fail_count.clear()
        self.eviction_queue.clear()

    def _clean_stale_cache_entries(self):
        current_time = time.monotonic()

        while len(self.eviction_queue) > 0:
            ban_until, ip_address = self.eviction_queue[0]
            if ban_until < current_time:
                heapq.heappop(self.eviction_queue)
                self.banned_ips.discard(ip_address)
            else:
                break

    @staticmethod
    def _normalize_ip_address(ip_address: str) -> str:
        addr = ipaddress.ip_address(ip_address)
        if isinstance(addr, ipaddress.IPv6Address):
            if addr.ipv4_mapped:
                return str(addr.ipv4_mapped)
            # This is to avoid an attacker "bypassing" the rate-limiting by buying a single /64 ipv6 range.
            return str(ipaddress.ip_network(f"{addr}/64", strict=False).network_address)
        return str(addr)

    def _check_is_banned(
        self, request: RequestIsBanned | RequestRegisterFailedLogin
    ) -> tuple[bool, bool]:
        """
        Return a (`is_banned, create_audit_log`) tuple.

        - `is_banned` is `True` if the `ip_address` of the `Request` is banned or `False` otherwise.
        - `create_audit_log` is `True` is failed login `LogEntry`(audit log) IP-ban should be created by the caller (RPC caller).
        """

        self._clean_stale_cache_entries()

        current_time = time.monotonic()
        # The time window has a 1-minute granularity.
        time_window = SETTINGS.time_window_size * 60
        new_time_window = current_time // time_window

        if new_time_window > self.current_time_window:
            self.ip_to_fail_count.clear()
            self.current_time_window = new_time_window

        ip_address = self._normalize_ip_address(request.ip_address)

        is_banned = ip_address in self.banned_ips
        is_newly_banned = False

        if not is_banned:
            fail_count = self.ip_to_fail_count.get(ip_address, 0)
            increment_fail_count = request.METHOD == RequestMethod.REGISTER_FAILED_LOGIN

            if increment_fail_count:
                fail_count += 1
                self.ip_to_fail_count[ip_address] = fail_count

            if fail_count >= SETTINGS.max_failed_login_attempts:
                self.banned_ips.add(ip_address)
                unban_time = (
                    current_time + time_window
                )  # The ban duration is of `time_window` (for now).
                heapq.heappush(self.eviction_queue, (unban_time, ip_address))
                is_banned = True
                is_newly_banned = True

        create_audit_log = (
            is_newly_banned
            and isinstance(request, RequestRegisterFailedLogin)
            and not Settings.AUDIT_LOG_LIMIT.try_acquire()
        )
        return is_banned, create_audit_log

    def _close_connection(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _send_request(self, request: Request) -> Optional[Response]:
        """Return `True` if the `ip_address` of the request is banned, or `False` otherwise"""
        try:
            if self.conn is None:
                conn_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                conn_socket.settimeout(0.2)
                conn_socket.connect(str(self._socket_file_path))
                self.conn = RPCSocket(conn_socket)

            encoded_request = request.encode()
            self.conn.send(encoded_request)

            encoded_response, close_socket = self.conn.recv()
            if close_socket:
                # Peer closed the connection: the leader (or its thread) is gone.
                raise ConnectionResetError("rate limiting server closed the connection")

            response = Response.decode(encoded_response)
            return response

        except TimeoutError:
            # A slow leader doesn't mean the leader is down (so there's no election).
            self._close_connection()
            return
        except OSError, ValueError:
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

    def refresh_settings(self, new_settings: Settings):
        request = RequestRefreshSettings.from_settings(new_settings)
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
