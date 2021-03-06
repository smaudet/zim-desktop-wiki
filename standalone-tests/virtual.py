# import tests

from zim.newfs import virtual as virtfs

# class BasicTests(tests.TestCase):
#
#     def runTest(self):


if __name__ == '__main__':
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

    #todo copyto, moveto, parent correct return