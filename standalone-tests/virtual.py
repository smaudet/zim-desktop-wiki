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

if __name__ == '__main__':

    # test_parent_mtime_ctime_touch()

    test_copyto()

    #TODO moveto, parent correct return