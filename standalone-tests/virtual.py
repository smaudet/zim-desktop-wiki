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

if __name__ == '__main__':

    # test_parent_mtime_ctime_touch()

    test_copyto()

    # test_folder_exists()

    #TODO moveto, parent correct return