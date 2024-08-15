#   Copyright (C) 2014 by Ronnie Sahlberg <ronniesahlberg@gmail.com>
#   Copyright (C) 2024 by Chris Grams <chrisagrams@gmail.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU Lesser General Public License as published by
#   the Free Software Foundation; either version 2.1 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public License
#   along with this program; if not, see <http://www.gnu.org/licenses/>.

import errno
import os
import stat
import sys
from .libnfs import *


def __ret_to_stat_result__(stat):
    return os.stat_result((
        stat.nfs_mode,       # st_mode
        stat.nfs_ino,        # st_ino
        stat.nfs_dev,        # st_dev
        stat.nfs_nlink,      # st_nlink
        stat.nfs_uid,        # st_uid
        stat.nfs_gid,        # st_gid
        stat.nfs_size,       # st_size
        stat.nfs_atime,      # st_atime
        stat.nfs_mtime,      # st_mtime
        stat.nfs_ctime,      # st_ctime
        stat.nfs_atime_nsec, # st_atime_ns
        stat.nfs_ctime_nsec, # st_ctime_ns
        stat.nfs_mtime_nsec, # st_mtime_ns
        stat.nfs_blocks,     # st_blocks
        stat.nfs_blksize,    # st_blksize
        stat.nfs_blocks,     # st_blocks
        stat.nfs_rdev        # st_rdev
    ))

class NFSFileHandle(object):
    def __init__(self, nfs, path, mode='r', codec=None):

        self._nfs = nfs
        self._name = path

        if codec:
            self._codec = codec
        elif sys.version_info[0] > 2:
            self._codec = 'utf-8'
        else:
            self._codec = None
        self._binary = True if 'b' in mode else False

        if path[:6] == "nfs://":
            _pos = path.rfind('/')
            _dir = path[:_pos]
            path = path[_pos:]
            self._private_context = NFS(_dir)
            self._nfs = self._private_context._nfs

        _plus = True if '+' in mode else False
        _mode = 0
        if 'r' in mode:
            _mode = os.O_RDWR if _plus else os.O_RDONLY
        if 'w' in mode:
            _mode = os.O_RDWR if _plus else os.O_WRONLY
            _mode |= os.O_CREAT|os.O_TRUNC
        if 'a' in mode:
            _mode = os.O_RDWR if _plus else os.O_WRONLY
            _mode |= os.O_CREAT|os.O_APPEND

        self._nfsfh = new_NFSFileHandle()
        _status = nfs_open(self._nfs, path, _mode, self._nfsfh)
        if _status == -errno.ENOENT and _mode & os.O_CREAT:
            _status = nfs_create(self._nfs, path, _mode, 0o664, self._nfsfh)
        if _status == -errno.ENOENT:
                raise IOError(errno.ENOENT, 'No such file or directory');
        if _status != 0:
            _errmsg = "open failed: %s" % (os.strerror(-_status),)
            raise ValueError(_errmsg)
        self._nfsfh = NFSFileHandle_value(self._nfsfh)
        self._closed = False
        self._need_flush = False
        self._writing = True if _mode & (os.O_RDWR|os.O_WRONLY) else False
    
    def __del__(self):
        pass

    def __enter__(self):
         return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
         self.close()

    def close(self):
        if self._need_flush:
            self.flush()
        nfs_close(self._nfs, self._nfsfh)
        self._closed = True

    def write(self, data):
        if self._closed:
            raise ValueError('I/O operation on closed file');
        if not self._writing:
            raise IOError('Trying to write on file open for reading');

        if not isinstance(data, bytearray):
            if self._codec:
                data = bytearray(data.encode(self._codec))
            else:
                data = bytearray(data)
        nfs_write(self._nfs, self._nfsfh, len(data), data)
        self._need_flush = True

    def read(self, size=-1):
        if size < 0:
            _pos = self.tell()

            _st = nfs_stat_64()
            nfs_fstat64(self._nfs, self._nfsfh, _st)

            size = _st.nfs_size - _pos

        buf = bytearray(size)
        count = nfs_read(self._nfs, self._nfsfh, len(buf), buf)
        if self._binary:
            return buf[:count]

        if self._codec:
            return buf[:count].decode(self._codec)
        else:
            return str(buf[:count])

    def fstat(self):
        _stat = nfs_stat_64()
        nfs_fstat64(self._nfs, self._nfsfh, _stat)
        return __ret_to_stat_result__(_stat)

    def tell(self):
        _pos = new_uint64_t_ptr()
        nfs_lseek(self._nfs, self._nfsfh, 0, os.SEEK_CUR, _pos)
        _pos = uint64_t_ptr_value(_pos)
        return _pos

    def seek(self, offset, whence=os.SEEK_CUR):
        _pos = new_uint64_t_ptr()
        nfs_lseek(self._nfs, self._nfsfh, offset, whence, _pos)

    def truncate(self, offset=-1):
        if offset < 0:
            offset = self.tell()
        nfs_ftruncate(self._nfs, self._nfsfh, offset)

    def fileno(self):
        _st = nfs_stat_64()
        nfs_fstat64(self._nfs, self._nfsfh, _st)
        return _st.nfs_ino

    def flush(self):
        if self._closed:
            raise ValueError('I/O operation on closed file');
        nfs_fsync(self._nfs, self._nfsfh)
        self._need_flush = False

    def isatty(self):
        return False

    @property
    def name(self):
        return self._name

    @property
    def closed(self):
        return self._closed

    @property
    def error(self):
        return nfs_get_error(self._nfs)


class NFS(object):
    def __init__(self, url):
        self._nfs = nfs_init_context()
        self._url = nfs_parse_url_dir(self._nfs, url)
        ret = nfs_mount(self._nfs, self._url.server, self._url.path)
        if ret != 0:
            raise IOError(nfs_get_error(self._nfs))

    def __del__(self):
        self._cleanup()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
         self._cleanup()

    def _cleanup(self):
        if self._url:
            nfs_destroy_url(self._url)
            self._url = None
        if self._nfs:
            nfs_destroy_context(self._nfs)
            self._nfs = None

    def open(self, path, mode='r', codec=None):
        return NFSFileHandle(self._nfs, path, mode=mode, codec=codec)

    def stat(self, path):
        _stat = nfs_stat_64()
        ret = nfs_stat64(self._nfs, path, _stat)
        if ret == -errno.ENOENT:
                raise IOError(errno.ENOENT, 'No such file or directory');
        return __ret_to_stat_result__(_stat)

    def lstat(self, path):
        _stat = nfs_stat_64()
        ret = nfs_lstat64(self._nfs, path, _stat)
        if ret == -errno.ENOENT:
                raise IOError(errno.ENOENT, 'No such file or directory');
        return __ret_to_stat_result__(_stat)

    def unlink(self, path):
        ret = nfs_unlink(self._nfs, path)
        if ret == -errno.ENOENT:
                raise IOError(errno.ENOENT, 'No such file or directory');
        return ret

    def mkdir(self, path):
        ret = nfs_mkdir(self._nfs, path)
        if ret == -errno.ENOENT:
                raise IOError(errno.ENOENT, 'No such file or directory');
        return ret

    def rmdir(self, path):
        ret = nfs_rmdir(self._nfs, path)
        if ret == -errno.ENOENT:
                raise IOError(errno.ENOENT, 'No such file or directory');
        return ret

    def listdir(self, path):
        d = new_NFSDirHandle()
        ret = nfs_opendir(self._nfs, path, d)
        if ret == -errno.ENOENT:
                raise IOError(errno.ENOENT, 'No such file or directory');
        d = NFSDirHandle_value(d)

        ret = []
        while True:
                entry = nfs_readdir(self._nfs, d)
                if entry == None:
                    break
                # os.listdir does not include '.' nor '..', make this behave the same
                if entry.name != '.' and entry.name != '..':
                    ret.append(entry.name)
        return ret

    def makedirs(self, path):
        npath = "/"
        for p in path.split(os.path.sep):
            npath = os.path.join(npath, p)
            self.mkdir(npath)

    def rename(self, src, dst):
        """Rename file"""
        ret = nfs_rename(self._nfs, src, dst)
        if ret == -errno.ENOENT:
            raise IOError(errno.ENOENT, 'No such file or directory')
        return ret


@property
def error(self):
    return nfs_get_error(self._nfs)

def open(url, mode='r', codec=None):
    return NFSFileHandle(None, url, mode=mode, codec=codec)

