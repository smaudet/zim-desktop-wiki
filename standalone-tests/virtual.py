# import tests

from zim.newfs import virtual as virtfs

# class BasicTests(tests.TestCase):
#
#     def runTest(self):

def test_parent_mtime_ctime_touch():
    virtfile = virtfs.VirtualFile('/notebooks/test/testfile.txt')
    assert virtfile.exists()

    parentItem = virtfile.parent()
    parent = virtfs.service.files().get(fileId=parentItem['id']).execute()
    print(parent['title'])

    assert virtfile.mtime()
    print('orig mtime: ' + virtfile.mtime())
    assert virtfile.ctime()
    assert virtfile.is_folder() == False
    virtfile.touch()
    print('new mtime: '+virtfile.mtime())

def test_copyto():
    virtfile = virtfs.VirtualFile('/notebooks/test/testfile.txt')
    assert virtfile.exists()

    virtfile.copyto('testcopy.txt')

    virtfile2 = virtfs.VirtualFile('/notebooks/test/testcopy.txt')
    assert virtfile2.exists()
    virtfile2.remove()

    isPassed = False
    try:
        virtfile.copyto('/notebooks/other/testfile.txt')
    except Exception as e:
        isPassed = True
    assert isPassed

    res = virtfile.copyto('/notebooks/other2/testfile.txt')
    res = virtfile.copyto('/someother/other/testfile.txt')

    virtfile2 = virtfs.VirtualFile('/notebooks/other2/testfile.txt')
    assert virtfile2.exists()
    virtfile2 = virtfs.VirtualFile('/someother/other/testfile.txt')
    assert virtfile2.exists()

def test_folder_exists():
    virtfile = virtfs.VirtualFile('/notebooks/test/testfile.txt')
    assert virtfile.exists()

    assert virtfile.folder_exists(virtfile.get_folder())
    assert virtfile.folder_exists('/web')
    assert virtfile.folder_exists('/')
    assert virtfile.folder_exists('.')
    assert not virtfile.folder_exists('/notebooks/other')
    assert not virtfile.folder_exists('/completely_bogus')
    assert not virtfile.folder_exists('')

def test_moveto():
    virtfile = virtfs.VirtualFile('/notebooks/test/testfile.txt')
    assert virtfile.exists()

    virtfile.moveto('/notebooks/test/testfile2.txt')

    virtfile2 = virtfs.VirtualFile('/notebooks/test/testfile2.txt')
    assert virtfile2.exists()
    assert not virtfile.exists()

    virtfile2.moveto('/notebooks/test/testfile.txt')

    assert not virtfile2.exists()
    assert virtfile.exists()

def test_create():
    virtfile = virtfs.VirtualFile('/notebooks/test/dontexistyet.txt')
    assert not virtfile.exists()
    virtfile.create('/notebooks/test/dontexistyet.txt', data=u'Hello World')
    virtfile.create('/notebooks/test/testcreate', isFolder=True)
    assert virtfile.exists()
    assert virtfs._exists('/notebooks/test/testcreate')

def test_create_file():
    virtfile = virtfs.VirtualFile('/notebooks/test/lorumipsum.txt')
    assert not virtfile.exists()
    virtfile.create('/notebooks/test/lorumipsum.txt', actual_file='./lorumipsum.txt')
    assert virtfile.exists()

def test_update():
    assert False

def test_read():
    virtfile = virtfs.VirtualFile('/notebooks/test/testfile.txt')
    result = virtfile.read()
    print(result)
    assert result == 'testfile\n'

def test_read_lines():
    virtfile = virtfs.VirtualFile('/notebooks/test/lorumipsum.txt')
    assert virtfile.exists()
    lines = virtfile.readlines()
    assert len(lines) == 10

def test_write():
    try:
        virtfile = virtfs.VirtualFile('/notebooks/test/something_new.txt')
        assert not virtfile.exists()
        virtfile.write(u'Hello One')
        assert virtfile.read() == 'Hello One'
        virtfile.write(u'Hello Two')
        assert virtfile.read() == 'Hello Two'
    finally:
        virtfile = virtfs.VirtualFile('/notebooks/test/something_new.txt')
        if virtfile.exists():
            virtfile.remove()

def test_write_lines():
    try:
        virtfile = virtfs.VirtualFile('/notebooks/test/something_new.txt')
        assert not virtfile.exists()
        virtfile.writelines(['one','two','three'])
        assert virtfile.read() == 'one\ntwo\nthree'
        virtfile.writelines(['four','five','six'])
        assert virtfile.read() == 'four\nfive\nsix'
    finally:
        virtfile = virtfs.VirtualFile('/notebooks/test/something_new.txt')
        if virtfile.exists():
            virtfile.remove()

def cleanup():
    # virtfile = virtfs.VirtualFile('/notebooks/test/testfile2.txt')
    # virtfile.remove()
    pass


def test_make_folder():
    virtfolder = virtfs.VirtualFolder('/notebooks/test')
    assert virtfolder.exists()

def test_get_folder_file():
    virtfolder = virtfs.VirtualFolder('/notebooks/test')
    file = virtfolder.file('notebook.zim')
    assert file.exists()

if __name__ == '__main__':

    # test_parent_mtime_ctime_touch()

    # test_copyto()

    # test_folder_exists()

    # test_moveto()

    # test_create()

    # test_create_file()

    # test_read()

    # test_read_lines()

    # test_write()

    # test_write_lines()

    # test_make_folder()

    test_get_folder_file()

    # cleanup()

    #TODO general code cleanup

    #TODO general file util methods (not instance based)

    #TODO test folder moveto/copyto

    #TODO test folder list_{names,files,folders}, file, folder, child, isequal

    #TODO general code cleanup