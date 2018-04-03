from io import StringIO

from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

from zim.fs import File, PathLookupError, Dir
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

class WrapperFSObjectBase(FSObjectBase):
    '''
    This class exists to decouple implementations that want to use FSObjectBase
    and Folder at the same time (not sure why those were coupled)
    '''
    def __init__(self, path, watcher=None):
        FSObjectBase.__init__(self, path, watcher)


class VirtualFSObjectBase(WrapperFSObjectBase):

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

def _find_item(path):
    paths = path.split(os.path.sep)
    paths.remove('')
    paths_len = len(paths)
    if paths_len > 0:

        paths_idx = 0
        if paths_len > 1:
            results = service.files().list(maxResults=1,
                q='\'root\' in parents and title = \'' + paths[paths_idx] +
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
                  'title = \'' + paths[0] + '\'').execute()
            items = results.get('items')
            if len(items):
                return items[0]
            return None

        paths_idx += 1

        last_idx = (paths_len - 1)

        while paths_idx < last_idx:
            results = service.files() \
                .list(maxResults=1,
                q='\'' + next_item['id'] + '\' in parents and title = \'' +
                  paths[paths_idx] + '\' and mimeType = '
                                     '\'application/vnd.google-apps.folder\'').execute()

            items = results.get('items')
            if len(items):
                next_item = items[0]

            paths_idx += 1

        results = service.files() \
            .list(maxResults=1,
            q='\'' + next_item['id'] +
              '\' in parents and title = \'' +
              paths[paths_idx] + '\' and trashed != true').execute()

        items = results.get('items')
        if len(items):
            return items[0]
        return None

def _exists(path):
    return _find_item(path) is not None

class VirtualFile(VirtualFSObjectBase, File):

    def update_item(self):
        if self.needsUpdate:
            self.find_item()

    def read(self):
        self.update_item()
        if self.item:
            return service.files().get_media(fileId=self.item['id']).execute()
        raise FileNotFoundError(self.path)

    def readlines(self):
        self.update_item()
        if self.item:
            return service.files().get_media(
                fileId=self.item['id']).execute().split('\n')
        raise FileNotFoundError(self.path)

    def rename(self, newpath):
        self.moveto(newpath)

    def write(self, text):
        self.update_item()
        if not self.exists():
            self.create(self.path, data=text)
        else:
            self.update(data=text)

    def writelines(self, lines):
        if lines is not None and len(lines) > 0:
            return self.write(unicode('\n'.join(lines)))
        return None

    def remove(self):
        if self.needsUpdate:
            self.find_item()
        if self.item:
            self.item = service.files().delete(fileId=self.item['id']).execute()

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
                        paths[paths_idx] + '\' and trashed != true').execute()

            if self.item is None:
                items = results.get('items')
                if len(items):
                    self.item = items[0]
                    self.needsUpdate = False

    def get_item(self):
        if self.needsUpdate:
            self.find_item()
        return self.item

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
            parents = self.get_folders_for_name(folder)
            body = {
                'parents': [parents[-1]], 'title': title
            }
            service.files().update(fileId=self.item['id'], body=body).execute()
        else:
            body = {
                'title': title
            }
            service.files().update(fileId=self.item['id'], body=body).execute()
        self.needsUpdate = True

    def folder_exists(self, name):

        #TODO local caching?

        if name == '/':
            return True

        if name == '':
            return False

        # noinspection PyBroadException
        try:
            parents = self.get_folders_for_name(name)
            return len(parents) > 0
        except Exception:
            return False

    def update(self, data=None, mime_type='text/plain', chunk_size=1024 * 1024):
        if data is not None:
            data_stream = StringIO()
            data_stream.write(data)
            media_body = MediaIoBaseUpload(data_stream, mimetype=mime_type,
                chunksize=chunk_size, resumable=True)
            body = {
                'title': self.get_path(),
                'mimeType': mime_type
            }
            return service.files().update(fileId=self.item['id'], body=body,
                media_body=media_body).execute()
        return None

    def create(self, name, data=None, actual_file=None, isFolder=False,
        mime_type='text/plain', chunk_size=1024 * 1024):

        folder_path, filename = os.path.split(name)
        parents = self.get_folders_for_name(folder_path)
        if isFolder:
            body = {
                'title': filename,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents' : [parents[-1]]
            }
            return service.files().insert(body=body).execute()
        elif actual_file is not None:
            actual_file = os.path.abspath(actual_file)
            media_body = MediaFileUpload(actual_file, mimetype=mime_type,
                resumable=True)
            body = {
                'title': filename,
                'mimeType': mime_type,
                'parents' : [parents[-1]]
            }
            return service.files().insert(body=body,
                media_body=media_body).execute()
        elif data is not None:
            data_stream = StringIO()
            data_stream.write(data)
            media_body = MediaIoBaseUpload(data_stream, mimetype=mime_type,
                chunksize=chunk_size, resumable=True)
            body = {
                'title': filename,
                'mimeType': mime_type,
                'parents' : [parents[-1]]
            }
            return service.files().insert(body=body,
                media_body=media_body).execute()
        return None

    def copyto(self, other):
        item = self.get_item()
        if item is not None:
            folderPath, filename = os.path.split(other)
            if folderPath == '':
                folderPath = self.get_folder()
            # check folder exists and is same
            if folderPath != self.get_folder():
                if not self.folder_exists(folderPath):
                    raise Exception('Folder' + folderPath + ' doesn\'t exist')
                else:
                    parents = self.get_folders_for_name(folderPath)
                    body = {'title': filename, 'parents': [parents[-1]]}
                    return service.files().copy(fileId=item['id'], body=body).execute()
            else:
                body = {'title': filename}
                return service.files().copy(fileId=item['id'], body=body).execute()

    def get_folders_for_name(self, name):
        if not os.path.isabs(name):
            # assume relative to current file
            name = os.path.abspath(os.path.join(self.get_folder(), name))

        paths = name.split(os.path.sep)
        paths.remove('')
        paths_len = len(paths)

        parents = []
        if paths_len > 0:

            paths_idx = 0
            if paths_len > 1:
                results = service.files().list(maxResults=1,
                    q='\'root\' in parents and title = \'' + paths[paths_idx] +
                      '\' and mimeType = '
                      '\'application/vnd.google-apps.folder\'').execute()

                items = results.get('items')
                if len(items) > 0:
                    next_item = items[0]
                    parents.append(next_item)
                else:
                    raise Exception('Invalid folder: '+paths[paths_idx])
            else:
                results = service.files().list(maxResults=1,
                    q='\'root\' in parents and '
                      'title = \'' + paths[0] + '\'').execute()
                items = results.get('items')
                if len(items):
                    return [items[0]]
                else:
                    return parents

            paths_idx += 1

            last_idx = (paths_len - 1)

            while paths_idx <= last_idx:
                results = service.files() \
                    .list(maxResults=1,
                    q='\'' + next_item['id'] + '\' in parents and title = \'' +
                      paths[paths_idx] + '\' and mimeType = '
                                         '\'application/vnd.google-apps.folder\'').execute()

                items = results.get('items')
                if len(items):
                    next_item = items[0]
                    parents.append(next_item)
                else:
                    raise Exception('Invalid folder: '+paths[paths_idx])

                paths_idx += 1

        return parents

class VirtualFolder(VirtualFile, Folder):

    def __iter__(self):
        pass

    def list_names(self):
        pass

    def list_files(self):
        pass

    def list_folders(self):
        pass

    def file(self, path):
        pass

    def folder(self, path):
        pass

    def child(self, path):
        pass

    def isequal(self, other):
        pass

    # def uri(self):
    #     pass

    def file(self, path):
        '''Get a L{File} object for a path below this folder

        @param path: a (relative) file path as string, tuple or
        L{FilePath} object. When C{path} is a L{File} object already
        this method still enforces it is below this folder.
        So this method can be used as check as well.

        @returns: a L{File} object
        @raises PathLookupError: if the path is not below this folder
        '''
        new_path = os.path.join(self.path, path)
        if not _exists(new_path):
            raise PathLookupError('%s path does not exist' % new_path)
        return VirtualFile(new_path)

    def subdir(self, path):
        '''Get a L{Dir} object for a path below this folder

        @param path: a (relative) file path as string, tuple or
        L{FilePath} object. When C{path} is a L{Dir} object already
        this method still enforces it is below this folder.
        So this method can be used as check as well.

        @returns: a L{Dir} object
        @raises PathLookupError: if the path is not below this folder

        '''

        dir = Dir((self.path, path))
        if not dir.path.startswith(self.path):
            raise PathLookupError('%s is not below %s' % (dir, self))
        return dir
