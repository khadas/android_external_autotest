# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging, os
from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import kernel_config

class kernel_ConfigVerify(test.test):
    """Examine a kernel build CONFIG list to make sure various things are
    present, missing, built as modules, etc.
    """
    version = 1
    IS_BUILTIN = [
        # Sanity checks; should be present in builds as builtins.
        'INET',
        'MMU',
        'MODULES',
        'PRINTK',
        'SECURITY',
        # Security; adds stack buffer overflow protections.
        'CC_STACKPROTECTOR',
        # Security; enables the SECCOMP application API.
        'SECCOMP',
        # Security; blocks direct physical memory access.
        'STRICT_DEVMEM',
        # Security; provides some protections against SYN flooding.
        'SYN_COOKIES',
        # Security; make sure both PID_NS and NET_NS are enabled
        # for the SUID sandbox.
        'PID_NS',
        'NET_NS',
        # Security; perform additional validation of credentials.
        'DEBUG_CREDENTIALS',
    ]
    IS_MODULE = [
        # Sanity checks; should be present in builds as modules.
        'BLK_DEV_SR',
        'BT',
        'TUN',
    ]
    IS_ENABLED = [
        # Either module or enabled, depending on platform.
        'VIDEO_V4L2',
    ]
    IS_MISSING = [
        # Sanity checks.
        'M386',                 # Never going to optimize to this CPU.
        'CHARLIE_THE_UNICORN',  # Config not in real kernel config var list.
        # Dangerous; allows direct physical memory writing.
        'ACPI_CUSTOM_METHOD',
        # Dangerous; disables brk ASLR.
        'COMPAT_BRK',
        # Dangerous; disables VDSO ASLR.
        'COMPAT_VDSO',
        # Dangerous; allows direct kernel memory writing.
        'DEVKMEM',
        # Dangerous; allows replacement of running kernel.
        'KEXEC',
        # Dangerous; allows replacement of running kernel.
        'HIBERNATION',
        # Assists heap memory attacks; best to keep interface disabled.
        'INET_DIAG',
    ]
    IS_EXCLUSIVE = [
        # Security; no surprise binary formats.
        {
            'regex': 'BINFMT_',
            'builtin': [
                'BINFMT_ELF',
            ],
            'module': [
            ],
            'missing': [
                # Sanity checks; one disabled, one does not exist.
                'BINFMT_MISC',
                'BINFMT_IMPOSSIBLE',
            ],
        },
        # Security; no surprise filesystem formats.
        {
            'regex': '.*_FS$',
            'builtin': [
                'DEBUG_FS',
                'ECRYPT_FS',
                'EXT4_FS',
                'EXT4_USE_FOR_EXT23',
                'PROC_FS',
                'SCSI_PROC_FS',
            ],
            'module': [
                'FAT_FS',
                'FUSE_FS',
                'HFSPLUS_FS',
                'ISO9660_FS',
                'UDF_FS',
                'VFAT_FS',
            ],
            'missing': [
                # Sanity checks; one disabled, one does not exist.
                'EXT2_FS',
                'EXT3_FS',
                'XFS_FS',
                'IMPOSSIBLE_FS',
            ],
        },
        # Security; no surprise partition formats.
        {
            'regex': '.*_PARTITION$',
            'builtin': [
                'EFI_PARTITION',
                'MSDOS_PARTITION',
            ],
            'module': [
            ],
            'missing': [
                # Sanity checks; one disabled, one does not exist.
                'LDM_PARTITION',
                'IMPOSSIBLE_PARTITION',
            ],
        },
    ]

    def run_once(self):
        # Cache the architecture to avoid redundant execs to "uname".
        arch = utils.get_arch()
        userspace_arch = utils.get_arch_userspace()

        # Report the full uname for anyone reading logs.
        logging.info('Running %s kernel, %s userspace: %s',
                     arch, userspace_arch,
                     utils.system_output('uname -a'))

        # Load the list of kernel config variables.
        config = kernel_config.KernelConfig()
        config.initialize()

        # Adjust for kernel-version-specific changes
        kernel_ver = os.uname()[2]
        if utils.compare_versions(kernel_ver, "3.10") >= 0:
            for entry in self.IS_EXCLUSIVE:
                if entry['regex'] == 'BINFMT_':
                    entry['builtin'].append('BINFMT_SCRIPT')

        # Run the static checks.
        map(config.has_builtin, self.IS_BUILTIN)
        map(config.has_module, self.IS_MODULE)
        map(config.is_enabled, self.IS_ENABLED)
        map(config.is_missing, self.IS_MISSING)
        map(config.is_exclusive, self.IS_EXCLUSIVE)

        # Run the dynamic checks.

        # Security; NULL-address hole should be as large as possible.
        # Upstream kernel recommends 64k, which should be large enough to
        # catch nearly all dereferenced structures.
        wanted = '65536'
        if arch.startswith('arm'):
            # ... except on ARM where it shouldn't be larger than 32k due
            # to historical ELF load location.
            wanted = '32768'
        config.has_value('DEFAULT_MMAP_MIN_ADDR', [wanted])

        # Security; make sure NX page table bits are usable.
        if not arch.startswith('arm'):
            if arch == "i386":
                config.has_builtin('X86_PAE')
            else:
                config.has_builtin('X86_64')

        # Security; marks data segments as RO/NX, text as RO.
        if arch.startswith('arm'):
            if utils.compare_versions(kernel_ver, "3.8") >= 0:
                config.has_builtin('DEBUG_RODATA')
                config.has_builtin('DEBUG_SET_MODULE_RONX')
            else:
                config.is_missing('DEBUG_RODATA')
                config.is_missing('DEBUG_SET_MODULE_RONX')
        else:
            config.has_builtin('DEBUG_RODATA')
            config.has_builtin('DEBUG_SET_MODULE_RONX')

        # Kernel: make sure port 0xED is the one used for I/O delay
        if not arch.startswith('arm'):
            config.has_builtin('IO_DELAY_0XED')
            needed = config.get('CONFIG_IO_DELAY_TYPE_0XED', None)
            config.has_value('DEFAULT_IO_DELAY_TYPE', [needed])

        # Raise a failure if anything unexpected was seen.
        if len(config.failures()):
            raise error.TestFail((", ".join(config.failures())))
