"""Detached, single-instance local GUI service using only the standard library."""
import contextlib
import errno
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler

if __package__:
    from .vmaf_settings import config_path
    from .vmaf_library import atomic_json
else:
    from vmaf_settings import config_path
    from vmaf_library import atomic_json


def service_paths():
    directory = config_path().expanduser().resolve().parent
    return tuple(directory / name for name in ('gui-session.json', 'gui.lock', 'gui.log'))


class ServiceLock:
    """OS-owned lock, automatically released even after a crash. Never unlink it."""
    def __init__(self, path):
        self.path = path
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.file = os.fdopen(os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600), 'r+b')
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.release()
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                return False
            raise
        return True

    def release(self):
        if self.file is not None:
            self.file.close()
            self.file = None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def live_session():
    """Only connect to our loopback endpoint; never follow a state-file URL."""
    try:
        state = json.loads(service_paths()[0].read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            return None
        port, token, pid = state['port'], state['token'], state['pid']
        if type(port) is not int or not 1 <= port <= 65535 or type(pid) is not int or pid <= 0:
            return None
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{40,64}', token):
            return None
        url = f'http://127.0.0.1:{port}/{token}/'
        # Local readiness requests must not use the user's HTTP proxy.
        with build_opener(ProxyHandler({}), NoRedirect()).open(url + 'health', timeout=.5) as response:
            health = json.loads(response.read(8192))
        if not isinstance(health, dict) or health.get('application') != 'xelavie-vmaf-check' or health.get('pid') != pid:
            return None
        if health.get('closing'):
            raise ValueError('Die GUI wird gerade beendet. Bitte danach --gui erneut starten.')
        return {**state, 'url': url, 'version': health.get('version', '')}
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None


def detached_options(platform=None):
    if (platform or os.name) == 'nt':
        # A separate hidden console survives the caller's console and still lets
        # Job.cancel send CTRL_BREAK_EVENT to its encoder process group.
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        return {'creationflags': subprocess.CREATE_NEW_CONSOLE, 'startupinfo': startup}
    return {'start_new_session': True}


def ensure_service(launcher, timeout=30):
    current = live_session()
    if current:
        return current
    session, lock, log = service_paths()
    session.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    process = subprocess.Popen(
        [sys.executable, '-u', str(launcher), '--_gui-service'],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, cwd=os.getcwd(),
        env={**os.environ, 'VMAF_SETTINGS_FILE': str(config_path().expanduser().resolve()),
             'PYTHONIOENCODING': 'utf-8'}, **detached_options())
    # Reap the worker if this launcher is itself long-lived (e.g. embedded/test).
    # A daemon thread does not keep a normal CLI launcher alive.
    threading.Thread(target=process.wait, daemon=True).start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = live_session()
        if current:
            return current
        code = process.poll()
        # 75 means another concurrently started worker owns the lock. Wait for it.
        if code is not None and code != 75:
            raise ValueError(f'GUI-Hintergrunddienst konnte nicht starten (Code {code}). Protokoll: {log}')
        time.sleep(.1)
    # Never kill an existing or still-starting service on a readiness timeout.
    raise ValueError(f'GUI-Dienst noch nicht erreichbar. --gui erneut versuchen. Protokoll: {log}')


def run_service(server_factory):
    session, lock_path, log_path = service_paths()
    lock = ServiceLock(lock_path)
    if not lock.acquire():
        return 75
    server = None
    try:
        fd = os.open(log_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8', buffering=1) as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                try:
                    server = server_factory()
                    # SIGTERM must not call shutdown on the serve_forever thread.
                    if hasattr(signal, 'SIGTERM'):
                        signal.signal(signal.SIGTERM, lambda *_: server.request_shutdown())
                    atomic_json(session, {'port': server.server_port, 'token': server.token,
                                          'pid': os.getpid()})
                    print('GUI-Hintergrunddienst gestartet.', flush=True)
                    server.serve_forever(poll_interval=.2)
                    return 0
                except BaseException:
                    traceback.print_exc()
                    return 1
                finally:
                    if server is not None:
                        server.queue.close()
                        server.job.cancel()
                        server.server_close()
    finally:
        # Still under the lock: a replacement worker cannot have published state.
        try:
            session.unlink(missing_ok=True)
        finally:
            lock.release()
