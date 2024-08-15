import unittest
import os
from libnfs import NFS
import socket

nfs_address = os.getenv("NFS_ADDRESS")

class TestNFS(unittest.TestCase):
    def test_nfs_stat_type(self):
        nfs = NFS(nfs_address)
        self.assertIsInstance(nfs.stat("."), os.stat_result)

    def test_nfs_stat_context_manager(self):
        with NFS(nfs_address) as nfs:
            self.assertIsInstance(nfs.stat("."), os.stat_result)

    def test_nfs_open(self):
        nfs = NFS(nfs_address)
        f = nfs.open("helloworld.txt", 'r')
        print(f.read())
        f.close()
        self.assertTrue(True)

    def test_nfs_open_context_manager(self):
        with NFS(nfs_address) as nfs:
            with nfs.open('helloworld.txt', 'r') as f:
                print(f.read())
                self.assertTrue(True)

    def test_nfs_listdir(self):
        nfs = NFS(nfs_address)
        print(nfs.listdir("."))
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()