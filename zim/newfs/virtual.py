from zim.fs import File
from zim.newfs import FSObjectBase, FileNotFoundError, FileUnicodeError, Folder, FileExistsError

import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
APPLICATION_NAME='StorageAPI'
CLIENT_SECRET_FILE='client_secret.json'

class VirtualFSObjectBase(FSObjectBase):

    needsUpdate = True

    @staticmethod
    def _get_credentials():
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'drive-python-quickstart.json')

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else: # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials


    def __init__(self, path, watcher=None):
        FSObjectBase.__init__(self, path, watcher=watcher)
        # self.encodedpath = _encode_path(self.path)

    def isequal(self, other):
        """Check file paths are equal based on stat results (inode
        number etc.). Intended to detect when two files or dirs are the
        same on case-insensitive filesystems. Does not explicitly check
        the content is the same.
        @param other: an other L{FilePath} object
        @returns: C{True} when the two paths are one and the same file
        """
        raise NotImplementedError

    def remove(self):
        pass

    def parent(self):
        raise NotImplementedError

    def ctime(self):
        raise NotImplementedError

    def mtime(self):
        raise NotImplementedError

    def exists(self):
        result = client.get()
        return result.trashed

    def iswritable(self):
        return True

    def touch(self):
        raise NotImplementedError

    def moveto(self, other):
        raise NotImplementedError

    def copyto(self, other):
        raise NotImplementedError

    def _set_mtime(self, mtime):
        raise NotImplementedError


class VirtualFolder(VirtualFSObjectBase, Folder):
    pass


class VirtualFile(VirtualFSObjectBase, File):
    pass