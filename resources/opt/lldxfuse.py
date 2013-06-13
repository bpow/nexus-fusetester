#!/usr/bin/python

import errno
import stat
import sys
import llfuse
import time
import dxpy
import os
import json


class DXFuseFile(object):
	def __init__(self, name, inode, parent_inode, file_id):
		self.name = name
		self.inode = inode
		self.file_id = file_id
		self.dxfile = None
		self.describe = dxpy.describe(file_id)
	def open(self):
		self.dxfile = dxpy.DXFile(self.file_id)
		return self.dxfile

class DXFuse(llfuse.Operations):
	def __init__(self, file_mappings):
		super(DXFuse, self).__init__()
		self.starttime = int(time.time())
		self.max_inode = llfuse.ROOT_INODE
		self.inode2entry = dict()
		self.entries = []
		for (file_id, name) in file_mappings.items():
			self.max_inode += 1
			e = DXFuseFile(name, self.max_inode, llfuse.ROOT_INODE, file_id)
			self.entries.append(e)
			self.inode2entry[self.max_inode] = e
	def opendir(self, inode):
		return inode
	def access(self, inode, mode, ctx):
		return inode
	def lookup(self, parent_inode, name):
		if parent_inode != llfuse.ROOT_INODE:
			# this is a flat filesystem! only the root should have children
			raise llfuse.FUSEError(errno.ENOENT)
		if name == '.':
			return parent_inode
		elif name == '..':
			return parent_inode # am I supposed to do something else?
		else:
			for entry in self.entries:
				if entry.name == name:
					return self.getattr(entry.inode)
		raise llfuse.FUSEError(errno.ENOENT)

	def getattr(self, inode):
		attr = llfuse.EntryAttributes()
		attr.st_ino = inode
		attr.generation = 0
		attr.entry_timeout = 300
		attr.attr_timeout = 300
		attr.st_mode = stat.S_IFREG | 0555
		attr.st_nlink = 1
		attr.st_uid = os.getuid()
		attr.st_gid = os.getgid()
		attr.st_rdev = 0
		attr.st_blksize = 512
		if inode == llfuse.ROOT_INODE:
			attr.st_mode = stat.S_IFDIR | 0555
			attr.st_size = 4096
			attr.st_blocks = 8
			attr.st_atime = self.starttime
			attr.st_mtime = self.starttime
			attr.st_ctime = self.starttime
		else:
			try:
				e = self.inode2entry[inode]
			except KeyError:
				llfuse.FUSEError(errno.ENOENT)
			attr.st_size = e.describe['size']
			attr.st_blocks = e.describe['size'] // 512
			attr.st_atime = e.describe['modified']
			attr.st_mtime = e.describe['modified']
			attr.st_ctime = e.describe['created']
		return attr

	def readdir(self, inode, offset):
		if inode != llfuse.ROOT_INODE:
			# this is a flat filesystem! only the root should have children
			raise llfuse.FUSEError(errno.ENOENT)
		for (i, e) in enumerate(self.entries[offset:]):
			yield (e.name, self.getattr(e.inode), offset+i+1)

	def open(self, inode, flags):
		self.inode2entry[inode].open()
		return inode

	def read(self, inode, offset, length):
		f = self.inode2entry[inode].dxfile
		f.seek(offset)
		return f.read(length)

	def statfs(self):
		st = llfuse.StatvfsData()
		st.f_bsize = 512
		st.f_frsize = 512
		size = sum([int(e.describe['size']) for e in self.entries])
		st.f_blocks = size // st.f_frsize
		st.f_bfree = 0
		st.f_bavail = 0
		st.f_files = len(self.entries)
		st.f_ffree = 0
		st.f_favail = 0
		return st

def daemonize(workingdir='/'):
	# first fork
	try:
		pid = os.fork()
		if pid > 0:
			sys.exit(0)
	except OSError, e:
		print >>sys.stderr, "Unable to fork (1) process for lldxfuse: (%d) %s"%(e.errno, e.strerr)
		sys.exit(1)
	# disassociate
	os.chdir(workingdir)
	os.umask(0)
	os.setsid()
	# second fork
	try:
		pid = os.fork()
		if pid > 0:
			sys.exit(0)
	except OSError, e:
		print >>sys.stderr, "Unable to fork (2) process for lldxfuse: (%d) %s"%(e.errno, e.strerr)
		sys.exit(1)
	# TODO: should redirect file descriptors

def mount(mountpoint, file_mappings, background=True):
	server = DXFuse(file_mappings)
	llfuse.init(server, mountpoint, [ b'fsname=dxfuse', b'subtype=dnanexus', b'ro' ])
	if background:
		daemonize('/')
	llfuse.main()
	llfuse.close()

if "__main__" == __name__:
	if len(sys.argv) != 3:
		print >>sys.stderr, """Usage: lldxfuse [ mountpoint ] [ mappings ]
  Where [ mappings ] is a json-formatted dictionary of file-ids mapped to a local name within the filesystem
Example:
  ./lldxfuse mnt '{"file-B6Bq2z2G5v152VkYp4154194": "test.bam", "file-B6Bq8jXG57143Z91744341K3": "test.bam.bai"}'
"""
	mountpoint = sys.argv[1]
	file_mappings = json.loads(sys.argv[2])
	mount(mountpoint, file_mappings)
