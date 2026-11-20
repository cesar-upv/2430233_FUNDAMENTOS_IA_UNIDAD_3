"""OS observations, advisory locks and temporary sleep prevention for campaigns."""

from contextlib import contextmanager
from datetime import UTC, datetime
import os
from pathlib import Path
import platform


def process_identity(pid):
    """Return a process birth token, None when gone, or 'unknown' if unreadable."""
    if type(pid) is not int or pid < 1:
        raise ValueError('Invalid worker PID.')
    if platform.system() == 'Linux':
        try:
            # comm may contain spaces and parentheses; fields after its last ')'
            # start at field 3, and the process start tick is field 22.
            fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
            return None if fields[0] == 'Z' else fields[19]
        except FileNotFoundError:
            return None
        except (OSError, IndexError):
            return 'unknown'
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None if kernel.GetLastError() == 87 else 'unknown'
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return 'unknown'
            if code.value != 259:
                return None
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                return 'unknown'
            return str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
    return 'unknown'


def observation():
    memory = ac = None
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes

        class Power(ctypes.Structure):
            _fields_ = [('ac', wintypes.BYTE), ('flags', wintypes.BYTE),
                        ('percent', wintypes.BYTE), ('reserved', wintypes.BYTE),
                        ('life', wintypes.DWORD), ('full', wintypes.DWORD)]

        class Memory(ctypes.Structure):
            _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
                (name, ctypes.c_ulonglong) for name in
                ('total', 'available', 'page_total', 'page_available', 'virtual', 'virtual_available', 'extended')]

        power, status = Power(), Memory()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(power)) and power.ac != 255:
            ac = bool(power.ac)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            memory = status.available
    elif platform.system() == 'Linux':
        values = Path('/proc/meminfo').read_text().splitlines()
        memory = next((int(line.split()[1]) * 1024 for line in values if line.startswith('MemAvailable:')), None)
        supplies = list(Path('/sys/class/power_supply').glob('*/online'))
        if supplies:
            ac = any(p.read_text().strip() == '1' for p in supplies)
        elif not list(Path('/sys/class/power_supply').glob('*/capacity')):
            ac = True  # Desktop without a reported battery.
    return {'at_utc': datetime.now(UTC).isoformat(), 'host': platform.node(),
            'os': platform.platform(), 'available_ram_bytes': memory, 'ac_online': ac,
            'affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None}


@contextmanager
def exclusive_lock(path):
    """An OS lock is released even after an abrupt process exit; keep the lock file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError(f'Another campaign process holds {path}') from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def awake():
    """Prevent idle sleep on Windows; Linux callers use systemd-inhibit externally."""
    if os.name != 'nt':
        yield
        return
    import ctypes
    previous = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    if not previous:
        raise OSError('Windows could not inhibit idle sleep.')
    try:
        yield
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(previous)
