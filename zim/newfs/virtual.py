from zim.fs import File
from zim.newfs import FSObjectBase, FileNotFoundError, FileUnicodeError, Folder, FileExistsError

import os
import httplib2

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/drive'
APPLICATION_NAME='StorageAPI'
exec_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../../'))
CLIENT_SECRET_FILE = os.path.join(exec_path,'client_secret.json')

def get_credentials():
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
    credential_path = os.path.join(credential_dir, 'zim-storage-api.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

service = None

def _get_client():
    global service
    creds = get_credentials()
    http = creds.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=http)


class VirtualFSObjectBase(FSObjectBase):

    def write(self):
        raise NotImplementedError

    def _set_mtime(self, mtime):
        pass

    def __init__(self, path, watcher=None):
        super(VirtualFSObjectBase, self).__init__(path, watcher)
        self.needsUpdate = True
        self.path = path
        self.item = None
        if service is None:
            _get_client()

    def get_path(self):
        raise NotImplementedError

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
        raise NotImplementedError

    def parent(self):
        raise NotImplementedError

    def ctime(self):
        raise NotImplementedError

    def mtime(self):
        raise NotImplementedError

    def exists(self):
        raise NotImplementedError

    def iswritable(self):
        return True

    def touch(self):
        raise NotImplementedError

    def moveto(self, other):
        raise NotImplementedError

    def copyto(self, other):
        raise NotImplementedError


class VirtualFolder(VirtualFSObjectBase, Folder):
    def get_path(self):
        pass

    def isequal(self, other):
        pass

    def parent(self):
        pass

    def ctime(self):
        pass

    def mtime(self):
        pass

    def exists(self):
        pass

    def touch(self):
        pass

    def moveto(self, other):
        pass

    def copyto(self, other):
        pass


class VirtualFile(VirtualFSObjectBase, File):

    def read(self):
        if self.needsUpdate:
            self.find_item()
        if self.item:
            return service.files().get(alt='media',fileId=self.item['id'])
        return None

    def readlines(self):
        raise NotImplementedError

    def rename(self, newpath):
        raise NotImplementedError

    def write(self):
        raise NotImplementedError

    def writelines(self, lines):
        raise NotImplementedError

    def remove(self):
        if self.needsUpdate:
            self.find_item()
        if self.item:
            self.item = service.files().remove(self.item['id'])

    def get_folder(self):
        return os.path.split(self.path)[0]

    def get_path(self):
        return os.path.split(self.path)[1]

    def isequal(self, other):

        if isinstance(other, VirtualFile):
            if other.needsUpdate:
                other.find_item()
            if self.needsUpdate:
                self.find_item()
            return self.item['id'] == other.item['id']

        return False

    def parent(self):
        if self.needsUpdate:
            self.find_item()
        return self.item['parents'][0]

    def ctime(self):
        if self.needsUpdate:
            self.find_item()
        return self.item['createdDate']

    def mtime(self):
        if self.needsUpdate:
            self.find_item()
        return self.item['modifiedDate']

    def is_folder(self):
        return self.item is not None and self.item['mimeType'] == \
               'application/vnd.google-apps.folder'

    def find_item(self):
        self.item = None
        paths = self.path.split(os.path.sep)
        paths.remove('')
        paths_len = len(paths)
        if paths_len > 0:

            paths_idx = 0
            if paths_len > 1:
                results = service.files().list(maxResults=1,
                    q='\'root\' in parents and title = \''+paths[paths_idx]+
                      '\' and mimeType = '
                      '\'application/vnd.google-apps.folder\'').execute()

                items = results.get('items')
                if len(items) > 0:
                    next_item = items[0]
                else:
                    raise Exception('invalid folder')
            else:
                results = service.files().list(maxResults=1,
                                               q='\'root\' in parents and '
                                                 'title = \''+paths[0] +'\'').execute()
                items = results.get('items')
                if len(items):
                    self.item = items[0]
                    self.needsUpdate = False

            paths_idx += 1

            last_idx = (paths_len - 1)

            while paths_idx < last_idx :
                results = service.files()\
                    .list(maxResults=1,
                        q='\''+next_item['id']+'\' in parents and title = \'' +
                        paths[paths_idx] + '\' and mimeType = '
                       '\'application/vnd.google-apps.folder\'').execute()

                items = results.get('items')
                if len(items):
                    next_item = items[0]

                paths_idx+=1

            results = service.files() \
                .list(maxResults=1,
                      q='\'' + next_item['id'] +
                        '\' in parents and title = \'' +
                        paths[paths_idx] + '\'').execute()

            if self.item is None:
                items = results.get('items')
                if len(items):
                    self.item = items[0]
                    self.needsUpdate = False

    def exists(self):
        if self.needsUpdate:
            self.find_item()
        return self.item is not None and not self.item['labels']['trashed']

    def touch(self):
        if self.needsUpdate:
            self.find_item()
        self.item = service.files().touch(fileId=self.item['id']).execute()

    def moveto(self, other):
        folder, title = os.path.split(other)
        if self.get_folder() != folder:
            #find folder - needs to be tested
            result = service.files().list(maxResults=20, title=folder).execute()
            item = result.get('items')[0]
            new_parent = item.id
            previous_parents = ",".join([parent["id"] for parent in self.item.parents])
            service.files().update(fileId=self.item.id, title=title,
                                   addParents=new_parent,
                                   removeParents=previous_parents)
        else:
            service.files().update(fileId=self.item.id, title=title)
        self.needsUpdate = True

    def copyto(self, other):
        service.files().copy().execute()
        pass

