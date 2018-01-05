from zim.fs import File
from zim.newfs import FSObjectBase, FileNotFoundError, FileUnicodeError, Folder, FileExistsError

from .base import _encode_path


class VirtualFSObjectBase(FSObjectBase):
    def __init__(self, path, watcher=None):
        FSObjectBase.__init__(self, path, watcher=watcher)
        self.encodedpath = _encode_path(self.path)

    def _stat(self):
        try:
            #FIXME
            #  return os.stat(self.encodedpath)
            pass
        except OSError:
            raise FileNotFoundError(self)

    def _set_mtime(self, mtime):
        # FIXME
        # os.utime(self.encodedpath, (mtime, mtime))
        pass

    def parent(self):
        dirname = self.dirname
        if dirname is None:
            raise ValueError('Can not get parent of root')
        else:
            return VirtualFolder(dirname, watcher=self.watcher)

    def ctime(self):
        return self._stat().st_ctime

    def mtime(self):
        return self._stat().st_mtime

    def iswritable(self):
        if self.exists():
            # FIXME
            # return os.access(self.encodedpath, os.W_OK)
            pass
        else:
            return self.parent().iswritable()  # recurs

    def isequal(self, other):
        # Do NOT assume paths are the same - could be hard link
        # or it could be a case-insensitive filesystem
        try:
            # FIXME
            # stat_result = os.stat(self.encodedpath)
            # other_stat_result = os.stat(other.encodedpath)
            pass
        except OSError:
            return False
        else:
            return stat_result == other_stat_result

    def moveto(self, other):
        # Using shutil.move instead of os.rename because move can cross
        # file system boundaries, while rename can not
        if isinstance(self, File):
            if isinstance(other, Folder):
                other = other.file(self.basename)

            assert isinstance(other, File)
        else:
            assert isinstance(other, Folder)

        if not isinstance(other, VirtualFSObjectBase):
            raise NotImplementedError('TODO: support cross object type move')

        assert not other.path == self.path  # case sensitive
        logger.info('Rename %s to %s', self.path, other.path)

        if not FS_CASE_SENSITIVE \
                and self.path.lower() == other.path.lower():
            # Rename to other case - need in between step
            other = self.__class__(other, watcher=self.watcher)
            tmp = self.parent().new_file(self.basename)
            # FIXME
            # shutil.move(self.encodedpath, tmp.encodedpath)
            # shutil.move(tmp.encodedpath, other.encodedpath)
        # elif os.path.exists(_encode_path(other.path)):
        #     #FIXME
        #     raise FileExistsError(other)
        else:
            # normal case
            other = self.__class__(other, watcher=self.watcher)
            other.parent().touch()
            # FIXME
            # shutil.move(self.encodedpath, other.encodedpath)

        if self.watcher:
            self.watcher.emit('moved', self, other)

        self._cleanup()
        return other

class VirtualFolder(VirtualFSObjectBase, Folder):
    pass


class AtomicWriteContext(object):
	# Functions for atomic write as a context manager
	# used by LocalFile.read and .readlines
	# Exposed as separate object to make it testable.
	# Should not be needed outside this module

	def __init__(self, file, mode='w'):
		self.path = file.encodedpath
		self.tmppath = self.path + '.zim-new~'
		self.mode = mode

	def __enter__(self):
		self.fh = open(self.tmppath, self.mode)
		return self.fh

	def __exit__(self, *exc_info):
		# flush to ensure write is done
		self.fh.flush()
		os.fsync(self.fh.fileno())
		self.fh.close()

		if not any(exc_info) and os.path.isfile(self.tmppath):
			# do the replace magic
			_replace_file(self.tmppath, self.path)
		else:
			# errors happened - try to clean up
			try:
				os.remove(self.tmppath)
			except:
				pass

class VirtualFile(VirtualFSObjectBase, File):

    def __init__(self, path, endofline=_EOL, watcher=None):
        VirtualFSObjectBase.__init__(self, path, watcher=watcher)
        self._mimetype = None
        self.endofline = endofline

    def exists(self):
        # FIXME
        # return os.path.isfile(self.encodedpath)
        pass

    def size(self):
        return self._stat().st_size

    def read_binary(self):
        try:
            with open(self.encodedpath, 'rb') as fh:
                return fh.read()
        except IOError:
            if not self.exists():
                raise FileNotFoundError(self)
            else:
                raise

    def read(self):
        try:
            with open(self.encodedpath, 'rU') as fh:
                try:
                    text = fh.read().decode('UTF-8')
                except UnicodeDecodeError as err:
                    raise FileUnicodeError(self, err)
                else:
                    return text.lstrip(u'\ufeff').replace('\x00', '')
                # Strip unicode byte order mark
                # Internally we use Unix line ends - so strip out \r
                # And remove any NULL byte since they screw up parsing
        except IOError:
            if not self.exists():
                raise FileNotFoundError(self)
            else:
                raise

    def readlines(self):
        try:
            with open(self.encodedpath, 'rU') as fh:
                return [
                    l.decode('UTF-8').lstrip(u'\ufeff').replace('\x00', '')
                    for l in fh]
            # Strip unicode byte order mark
            # Internally we use Unix line ends - so strip out \r
            # And remove any NULL byte since they screw up parsing
        except IOError:
            if not self.exists():
                raise FileNotFoundError(self)
            else:
                raise

    def write(self, text):
        text = text.encode('UTF-8')
        if self.endofline != _EOL:
            if self.endofline == 'dos':
                text = text.replace('\n', '\r\n')
            mode = 'wb'
        else:
            mode = 'w'  # trust newlines to be handled

        with self._write_decoration():
            with AtomicWriteContext(self, mode=mode) as fh:
                fh.write(text)

    def writelines(self, lines):
        lines = map(lambda l: l.encode('UTF-8'), lines)
        if self.endofline != _EOL:
            if self.endofline == 'dos':
                lines = map(lambda l: l.replace('\n', '\r\n'), lines)
            mode = 'wb'
        else:
            mode = 'w'  # trust newlines to be handled

        with self._write_decoration():
            with AtomicWriteContext(self, mode=mode) as fh:
                fh.writelines(lines)

    def write_binary(self, data):
        with self._write_decoration():
            with AtomicWriteContext(self, mode='wb') as fh:
                fh.write(data)

    def touch(self):
        # overloaded because atomic write can cause mtime < ctime
        if not self.exists():
            with self._write_decoration():
                with open(self.encodedpath, 'w') as fh:
                    fh.write('')

    def copyto(self, other):
        if isinstance(other, Folder):
            other = other.file(self.basename)

        assert isinstance(other, File)
        assert other.path != self.path

        logger.info('Copy %s to %s', self.path, other.path)

        if isinstance(other, VirtualFile):
            #FIXME
            # if os.path.exists(other.encodedpath):
            #     raise FileExistsError(other)

            other.parent().touch()
            # FIXME
            # shutil.copy2(self.encodedpath, other.encodedpath)
            pass
        else:
            self._copyto(other)

        if self.watcher:
            self.watcher.emit('created', other)

        return other

    def remove(self):

        # FIXME
        # if os.path.isfile(self.encodedpath):
        #     os.remove(self.encodedpath)

        if self.watcher:
            self.watcher.emit('removed', self)

        self._cleanup()