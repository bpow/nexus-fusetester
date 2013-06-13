#!/usr/bin/python

from errno import *
import stat
import sys
import fuse
import time
import logging
import dxpy
import json
import posixpath
import errno

fuse.fuse_python_api = (0, 2)
log = logging.getLogger()

class MyStat(fuse.Stat):
	def __init__(self):
		now = int(time.time())
		self.st_mode = stat.S_IFDIR | 0555
		self.st_ino = 0
		self.st_dev = 0
		self.st_nlink = 2
		self.st_uid = 0
		self.st_gid = 0
		self.st_size = 4096
		self.st_atime = now
		self.st_mtime = now
		self.st_ctime = now

class DxFS(fuse.Fuse):
	def __init__(self, *args, **kw):
		fuse.Fuse.__init__(self, *args, **kw)
		self.project = dxpy.DXProject()
		self.dxlscache = {}
	
	def getattr(self, path):
		path = path.decode('utf8')
		log.info('getattr for ' + path)
		st = MyStat()
		if ('/' == path):
			log.info('  getattr was for root directory')
			return st
		else:
			dirname = posixpath.dirname(path)
			basename = posixpath.basename(path)
			
			try:
				parent_ls = self.dxlscache[dirname]
			except KeyError:
				parent_ls = self.project.list_folder(dirname, describe=True)
				self.dxlscache[dirname] = parent_ls
			if path in parent_ls['folders']:
				log.info("  getattr was for a directory, and I found it")
				return st
			else:
				for o in parent_ls['objects']:
					if o['describe']['name'] == basename:
						st.st_mode = stat.S_IFREG | 0555
						st.st_nlink = 1
						st.st_size = o['describe']['size']
						log.info("  gettr was for a file!")
						return st
				log.warn("Did not find '%s' in '%s'"%(basename, dirname))
				return -errno.ENOENT

	def readdir(self, path, offset):
		#readdir will always refresh the cached listing for a directory
		path = path.decode('utf8')
		dxls = self.project.list_folder(path, describe=True)
		self.dxlscache[path] = dxls
		log.info('readdir for ' + path)
		dirents = ['.', '..']
		dirents.extend([posixpath.basename(f) for f in dxls['folders']])
		dirents.extend([f['describe']['name'] for f in dxls['objects'] if f['describe']['class'] == 'file'])
		for f in dirents[offset:]:
			log.info('yielding ' + f)
			yield fuse.Direntry(f.encode('utf8', 'replace'))
	
	def read(self, path, length, offset):
		path = path.decode('utf8')
		log.info("reading from '%s', %d bytes from %s"%(path, length, offset))
		file_id = dxpy.find_one_data_object(folder=posixpath.dirname(path), name=posixpath.basename(path), recurse=False)
		# TODO - cache dxfiles
		dxfile = dxpy.DXFile(file_id['id'])
		dxfile.seek(offset)
		return dxfile.read(length)


logging.basicConfig(filename='dxfuse.log', level=logging.DEBUG)
server = DxFS()
server.parse()
server.main()
