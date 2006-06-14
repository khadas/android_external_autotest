# This requires aio headers to build.
# Should work automagically out of deps now.

# NOTE - this should also have the ability to mount a filesystem, 
# run the tests, unmount it, then fsck the filesystem

import test
from autotest_utils import *

class fsx(test.test):
	version = 2

	def initialize(self):
		self.job.setup_dep(['libaio'])
		ldflags = '-L ' + self.autodir + '/deps/libaio/lib'
		cflags = '-I ' + self.autodir + '/deps/libaio/include'
		var_ldflags = 'LDFLAGS="' + self.ldflags + '"'
		var_cflags  = 'CFLAGS="' + self.cflags + '"'
		self.make_flags = var_ldflags + ' ' + var_cflags
	
	
	# http://www.zip.com.au/~akpm/linux/patches/stuff/ext3-tools.tar.gz
	def setup(self, tarball = 'ext3-tools.tar.gz'):
		self.tarball = unmap_url(self.bindir, tarball, self.tmpdir)
		extract_tarball_to_dir(self.tarball, self.srcdir)
		os.chdir(self.srcdir)
		system(self.make_flags + ' make fsx-linux')


	def execute(self, repeat = '100000'):
		args = '-N ' + repeat
		os.chdir(self.tmpdir)
		libs = self.autodir+'/deps/libaio/lib/'
		ld_path = prepend_path(libs, environ('LD_LIBRARY_PATH'))
		var_ld_path = 'LD_LIBRARY_PATH=' + ld_path
		cmd = self.srcdir + '/fsx-linux ' + args + ' poo'
		system(var_ld_path + ' ' + cmd)

		# Do a profiling run if necessary
		profilers = self.job.profilers
		if profilers.present():
			profilers.start(self)
			system(var_ld_path + ' ' + cmd)
			profilers.stop(self)
			profilers.report(self)
