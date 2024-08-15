# nfs-python
A NFS client for Python utilizing libnfs.
Forked from https://github.com/sahlberg/libnfs-python with some improvements to abide closer to python's `os` module.

## Usage
``` py
from libnfs import NFS

address = "nfs://nfs-server/export"

# Using a context manager
with NFS(address) as nfs:
   with nfs.open('helloworld.txt', 'r') as f:
      print(f.read())

# Without a context manager
nfs = NFS(address)
f = nfs.open('helloworld.txt', 'r')
print(f.read())
f.close()
nfs.close()
```