# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A module to support automatic firmware update.

See FirmwareUpdater object below.
"""
import array
import json
import os

from autotest_lib.client.common_lib.cros import chip_utils
from autotest_lib.client.cros.faft.utils import (flashrom_handler,
                                                 shell_wrapper)


class FirmwareUpdaterError(Exception):
    """Error in the FirmwareUpdater module."""
    pass


class BrokenShellballError(FirmwareUpdaterError):
    """Error in the shellball"""
    pass


class InvalidManifestError(FirmwareUpdaterError):
    """Error in the manifest, specifically"""
    def __init__(self, shellball, description):
        if shellball:
            shellball = os.path.basename(shellball)
            msg = ('Invalid output from %s --manifest: %s'
                   % (shellball, description))
        else:
            msg = 'Invalid contents in manifest.json: %s' % description
        super(InvalidManifestError, self).__init__(msg)


class FirmwareUpdater(object):
    """An object to support firmware update.

    This object will create a temporary directory in /var/tmp/faft/autest with
    two subdirectory keys/ and work/. You can modify the keys in keys/
    directory. If you want to provide a given shellball to do firmware update,
    put shellball under /var/tmp/faft/autest with name chromeos-firmwareupdate.

    @type os_if: autotest_lib.client.cros.faft.utils.os_interface.OSInterface
    """

    DAEMON = 'update-engine'
    CBFSTOOL = 'cbfstool'
    HEXDUMP = 'hexdump -v -e \'1/1 "0x%02x\\n"\''

    DEFAULT_SHELLBALL = '/usr/sbin/chromeos-firmwareupdate'
    DEFAULT_SUBDIR = 'autest'  # subdirectory of /var/tmp/faft/
    DEFAULT_SECTION_FOR_TARGET = {'bios': 'a', 'ec': 'rw'}

    def __init__(self, os_if):
        """Initialize the updater tools, but don't load the image data yet."""
        self.os_if = os_if
        self._temp_path = self.os_if.state_dir_file(self.DEFAULT_SUBDIR)
        self._cbfs_work_path = os.path.join(self._temp_path, 'cbfs')
        self._keys_path = os.path.join(self._temp_path, 'keys')
        self._work_path = os.path.join(self._temp_path, 'work')
        self._bios_path = 'bios.bin'
        self._ec_path = 'ec.bin'

        self.pubkey_path = os.path.join(self._keys_path, 'root_key.vbpubk')
        self._real_bios_handler = self._create_handler('bios')
        self._real_ec_handler = self._create_handler('ec')
        self.initialized = False

    def init(self):
        """Extract the shellball and other files, unless they already exist."""

        if self.os_if.is_dir(self._work_path):
            # If work dir is present, assume the whole temp dir is usable as-is.
            self._detect_image_paths()
        else:
            # If work dir is missing, assume the whole temp dir is unusable, and
            # recreate it.
            self._create_temp_dir()
            self.extract_shellball()

        self.initialized = True

    def _get_handler(self, target):
        """Return the handler for the target, after initializing it if needed.

        @param target: image type ('bios' or 'ec')
        @return: the handler for that target

        @type target: str
        @rtype: flashrom_handler.FlashromHandler
        """
        if target == 'bios':
            if not self._real_bios_handler.initialized:
                bios_file = self._get_image_path('bios')
                self._real_bios_handler.init(bios_file)
            return self._real_bios_handler
        elif target == 'ec':
            if not self._real_ec_handler.initialized:
                ec_file = self._get_image_path('ec')
                self._real_ec_handler.init(ec_file, allow_fallback=True)
            return self._real_ec_handler
        else:
            raise FirmwareUpdaterError("Unhandled target: %r" % target)

    def _create_handler(self, target, suffix=None):
        """Return a new (not pre-populated) handler for the given target,
        such as for use in checking installed versions.

        @param target: image type ('bios' or 'ec')
        @param suffix: additional piece for subdirectory of handler
                       Example: 'tmp' -> 'autest/<target>.tmp/'
        @return: a new handler for that target

        @type target: str
        @rtype: flashrom_handler.FlashromHandler
        """
        if suffix:
            subdir = '%s/%s.%s' % (self.DEFAULT_SUBDIR, target, suffix)
        else:
            subdir = '%s/%s' % (self.DEFAULT_SUBDIR, target)
        return flashrom_handler.FlashromHandler(
                self.os_if, self.pubkey_path, self._keys_path, target=target,
                subdir=subdir)

    def _get_image_path(self, target):
        """Return the handler for the given target

        @param target: image type ('bios' or 'ec')
        @return: the path of the image file for that target

        @type target: str
        @rtype: str
        """
        if target == 'bios':
            return os.path.join(self._work_path, self._bios_path)
        elif target == 'ec':
            return os.path.join(self._work_path, self._ec_path)
        else:
            raise FirmwareUpdaterError("Unhandled target: %r" % target)

    def _get_default_section(self, target):
        """Return the default section to work with, for the given target

        @param target: image type ('bios' or 'ec')
        @return: the default section for that target

        @type target: str
        @rtype: str
        """
        if target in self.DEFAULT_SECTION_FOR_TARGET:
            return self.DEFAULT_SECTION_FOR_TARGET[target]
        else:
            raise FirmwareUpdaterError("Unhandled target: %r" % target)

    def _create_temp_dir(self):
        """Create (or recreate) the temporary directory.

        The default /usr/sbin/chromeos-firmwareupdate is copied into _temp_dir,
        and devkeys are copied to _key_path. The caller is responsible for
        extracting the copied shellball.
        """
        self.cleanup_temp_dir()

        self.os_if.create_dir(self._temp_path)
        self.os_if.create_dir(self._cbfs_work_path)
        self.os_if.create_dir(self._work_path)
        self.os_if.copy_dir('/usr/share/vboot/devkeys', self._keys_path)

        working_shellball = os.path.join(self._temp_path,
                                         'chromeos-firmwareupdate')
        self.os_if.copy_file(self.DEFAULT_SHELLBALL, working_shellball)

    def cleanup_temp_dir(self):
        """Cleanup temporary directory."""
        if self.os_if.is_dir(self._temp_path):
            self.os_if.remove_dir(self._temp_path)

    def stop_daemon(self):
        """Stop update-engine daemon."""
        self.os_if.log('Stopping %s...' % self.DAEMON)
        cmd = 'status %s | grep stop || stop %s' % (self.DAEMON, self.DAEMON)
        self.os_if.run_shell_command(cmd)

    def start_daemon(self):
        """Start update-engine daemon."""
        self.os_if.log('Starting %s...' % self.DAEMON)
        cmd = 'status %s | grep start || start %s' % (self.DAEMON, self.DAEMON)
        self.os_if.run_shell_command(cmd)

    def get_ec_hash(self):
        """Retrieve the hex string of the EC hash."""
        ec = self._get_handler('ec')
        return ec.get_section_hash('rw')

    def get_section_fwid(self, target='bios', section=None):
        """Get one fwid from in-memory image, for the given target.

        @param target: the image type to get from: 'bios (default) or 'ec'
        @param section: section to return.  Default: A for bios, RW for EC

        @type target: str | None
        @rtype: str
        """
        if section is None:
            section = self._get_default_section(target)
        image_path = self._get_image_path(target)
        if target == 'ec' and not os.path.isfile(image_path):
            # If the EC image is missing, report a specific error message.
            raise FirmwareUpdaterError("Shellball does not contain ec.bin")

        handler = self._get_handler(target)
        handler.new_image(image_path)
        fwid = handler.get_section_fwid(section)
        if fwid is not None:
            return str(fwid)
        else:
            return None

    def get_all_fwids(self, target='bios'):
        """Get all non-empty fwids from in-memory image, for the given target.

        @param target: the image type to get from: 'bios' (default) or 'ec'
        @return: fwid for the sections

        @type target: str
        @rtype: dict | None
        """
        image_path = self._get_image_path(target)
        if target == 'ec' and not os.path.isfile(image_path):
            # If the EC image is missing, report a specific error message.
            raise FirmwareUpdaterError("Shellball does not contain ec.bin")

        handler = self._get_handler(target)
        handler.new_image(image_path)

        fwids = {}
        for section in handler.fv_sections:
            fwid = handler.get_section_fwid(section)
            if fwid is not None:
                fwids[section] = fwid
        return fwids

    def get_all_installed_fwids(self, target='bios', filename=None):
        """Get all non-empty fwids from disk or flash, for the given target.

        @param target: the image type to get from: 'bios' (default) or 'ec'
        @param filename: filename to read instead of using the actual flash
        @return: fwid for the sections

        @type target: str
        @type filename: str
        @rtype: dict
        """
        handler = self._create_handler(target, 'installed')
        if filename:
            filename = os.path.join(self._temp_path, filename)
        handler.new_image(filename)

        fwids = {}
        for section in handler.fv_sections:
            fwid = handler.get_section_fwid(section)
            if fwid is not None:
                fwids[section] = fwid
        return fwids

    def modify_fwids(self, target='bios', sections=None):
        """Modify the fwid in the image, but don't flash it.

        @param target: the image type to modify: 'bios' (default) or 'ec'
        @param sections: section(s) to modify.  Default: A for bios, RW for ec
        @return: fwids for the modified sections, as {section: fwid}

        @type target: str
        @type sections: tuple | list
        @rtype: dict
        """
        if sections is None:
            sections = [self._get_default_section(target)]

        image_fullpath = self._get_image_path(target)
        if target == 'ec' and not os.path.isfile(image_fullpath):
            # If the EC image is missing, report a specific error message.
            raise FirmwareUpdaterError("Shellball does not contain ec.bin")

        handler = self._get_handler(target)
        fwids = handler.modify_fwids(sections)

        handler.dump_whole(image_fullpath)
        handler.new_image(image_fullpath)

        return fwids

    def modify_ecid_and_flash_to_bios(self):
        """Modify ecid, put it to AP firmware, and flash it to the system.

        This method is used for testing EC software sync for EC EFS (Early
        Firmware Selection). It creates a slightly different EC RW image
        (a different EC fwid) in AP firmware, in order to trigger EC
        software sync on the next boot (a different hash with the original
        EC RW).

        The steps of this method:
         * Modify the EC fwid by appending a '~', like from
           'fizz_v1.1.7374-147f1bd64' to 'fizz_v1.1.7374-147f1bd64~'.
         * Resign the EC image.
         * Store the modififed EC RW image to CBFS component 'ecrw' of the
           AP firmware's FW_MAIN_A and FW_MAIN_B, and also the new hash.
         * Resign the AP image.
         * Flash the modified AP image back to the system.
        """
        self.cbfs_setup_work_dir()

        fwid = self.get_section_fwid('ec', 'rw')
        if fwid.endswith('~'):
            raise FirmwareUpdaterError('The EC fwid is already modified')

        # Modify the EC FWID and resign
        fwid = fwid[:-1] + '~'
        ec = self._get_handler('ec')
        ec.set_section_fwid('rw', fwid)
        ec.resign_ec_rwsig()

        # Replace ecrw to the new one
        ecrw_bin_path = os.path.join(self._cbfs_work_path,
                                     chip_utils.ecrw.cbfs_bin_name)
        ec.dump_section_body('rw', ecrw_bin_path)

        # Replace ecrw.hash to the new one
        ecrw_hash_path = os.path.join(self._cbfs_work_path,
                                      chip_utils.ecrw.cbfs_hash_name)
        with open(ecrw_hash_path, 'w') as f:
            f.write(self.get_ec_hash())

        # Store the modified ecrw and its hash to cbfs
        self.cbfs_replace_chip(chip_utils.ecrw.fw_name, extension='')

        # Resign and flash the AP firmware back to the system
        self.cbfs_sign_and_flash()

    def corrupt_diagnostics_image(self, local_filename):
        """Corrupts a diagnostics image in the CBFS working directory.

        @param local_filename: Filename for storing the diagnostics image in the
            CBFS working directory
        """
        local_path = os.path.join(self._cbfs_work_path, local_filename)

        # Invert the last few bytes of the image. Note that cbfstool will
        # silently ignore bytes added after the end of the ELF, and it will
        # refuse to use an ELF with noticeably corrupted headers as a payload.
        num_bytes = 4
        with open(local_path, 'rb+') as image:
            image.seek(-num_bytes, os.SEEK_END)
            last_bytes = array.array('B')
            last_bytes.fromfile(image, num_bytes)

            for i in range(len(last_bytes)):
                last_bytes[i] = last_bytes[i] ^ 0xff

            image.seek(-num_bytes, os.SEEK_END)
            last_bytes.tofile(image)

    def resign_firmware(self, version=None, work_path=None):
        """Resign firmware with version.

        Args:
            version: new firmware version number, default to no modification.
            work_path: work path, default to the updater work path.
        """
        if work_path is None:
            work_path = self._work_path
        self.os_if.run_shell_command(
                '/usr/share/vboot/bin/resign_firmwarefd.sh '
                '%s %s %s %s %s %s %s %s' %
                (os.path.join(work_path, self._bios_path),
                 os.path.join(self._temp_path, 'output.bin'),
                 os.path.join(self._keys_path, 'firmware_data_key.vbprivk'),
                 os.path.join(self._keys_path, 'firmware.keyblock'),
                 os.path.join(self._keys_path,
                              'dev_firmware_data_key.vbprivk'),
                 os.path.join(self._keys_path, 'dev_firmware.keyblock'),
                 os.path.join(self._keys_path, 'kernel_subkey.vbpubk'),
                 ('%d' % version) if version is not None else ''))
        self.os_if.copy_file(
                '%s' % os.path.join(self._temp_path, 'output.bin'),
                '%s' % os.path.join(work_path, self._bios_path))

    def _read_manifest(self, shellball=None):
        """This gets the manifest from the shellball or the extracted directory.

        @param shellball: Path of the shellball to read from (via --manifest).
                          If None (default), read from extracted manifest.json.
        @return: the manifest information, or None

        @type shellball: str | None
        @rtype: dict
        """

        if shellball:
            output = self.os_if.run_shell_command_get_output(
                    'sh %s --manifest' % shellball)
            manifest_text = '\n'.join(output or [])
        else:
            manifest_file = os.path.join(self._work_path, 'manifest.json')
            manifest_text = self.os_if.read_file(manifest_file)

        if not (manifest_text and manifest_text.strip()):
            raise InvalidManifestError(
                    shellball,
                    'data is an empty string: %r' % manifest_text)

        try:
            return json.loads(manifest_text)
        except ValueError as e:
            raise InvalidManifestError(
                    shellball,
                    "json is malformed: %s\n%s" % (e, manifest_text))

    def _detect_image_paths(self, shellball=None):
        """Scans shellball manifest to find correct bios and ec image paths.

        @param shellball: Path of the shellball to read from (via --manifest).
                          If None (default), read from extracted manifest.json.
        @type shellball: str | None
        """
        model_result = self.os_if.run_shell_command_get_output(
                'mosys platform model')

        if not model_result:
            return

        model = model_result[0]

        if not model:
            return

        manifest_dict = self._read_manifest(shellball)

        # Manifest must not be empty
        if not manifest_dict:
            raise InvalidManifestError(
                    shellball,
                    'manifest is empty: %r' % manifest_dict)

        # Model must be present
        if model not in manifest_dict:
            models = ','.join(sorted(manifest_dict.keys()))
            raise InvalidManifestError(
                    shellball,
                    'model %r not found in manifest keys: %s'
                    % (model, models))

        model_dict = manifest_dict[model]

        # Host section is mandatory, and must have an image
        if 'host' in model_dict:
            host_dict = model_dict['host']
            if 'image' not in host_dict:
                raise InvalidManifestError(
                        shellball,
                        "model %r has a 'host' with no 'image': %s"
                        % (model, host_dict))
            if not host_dict['image']:
                raise InvalidManifestError(
                        shellball,
                        "model %r has a 'host' with empty 'image': %s"
                        % (model, host_dict))
            self._bios_path = host_dict['image']
        else:
            raise InvalidManifestError(
                    shellball,
                    "model %r has no 'host': %s" % (model, model_dict))

        # EC section is optional, but if present, it must have an image
        if 'ec' in model_dict:
            ec_dict = model_dict['ec']
            if 'image' not in ec_dict:
                raise InvalidManifestError(
                        shellball,
                        "model %r has an 'ec' with no 'image': %s"
                        % (model, ec_dict))
            if not ec_dict['image']:
                raise InvalidManifestError(
                        shellball,
                        "model %r has an 'ec' with empty 'image': %s"
                        % (model, ec_dict))
            self._ec_path = ec_dict['image']

    def _check_shellball(self, shellball, description='shellball'):
        """Check the size of the shellball, to make sure it's properly formed.

        @param shellball: path of the shellball file
        @param description: partial phrase to describe the shellball
        """
        stat_output = self.os_if.run_shell_command_get_output(
                'stat -c %%s %s' % shellball)
        if not stat_output:
            raise FirmwareUpdaterError(
                    'The %s does not exist: %s'
                    % (description, shellball))

        shellball_size = int(stat_output[0].strip())
        if not shellball_size:
            raise BrokenShellballError(
                    "The %s is empty (zero bytes): %s"
                    % (description, shellball))

    def extract_shellball(self, append=None):
        """Extract the working shellball.

        Args:
            append: decide which shellball to use with format
                chromeos-firmwareupdate-[append]. Use 'chromeos-firmwareupdate'
                if append is None.
        Returns:
            string: the full path of the shellball
        """
        working_shellball = os.path.join(self._temp_path,
                                         'chromeos-firmwareupdate')
        if append:
            working_shellball = working_shellball + '-%s' % append

        self._check_shellball(working_shellball, 'shellball to be extracted')

        self.os_if.run_shell_command(
                'sh %s --sb_extract %s' % (working_shellball, self._work_path))

        # use the json file that was extracted, to catch extraction problems.
        self._detect_image_paths()
        return working_shellball

    def repack_shellball(self, append=None):
        """Repack shellball with new fwid.

        New fwid follows the rule: [orignal_fwid]-[append].

        Args:
            append: save the new shellball with a suffix, for example,
                chromeos-firmwareupdate-[append]. Use 'chromeos-firmwareupdate'
                if append is None.
        Returns:
            string: The full path to the shellball
        """

        working_shellball = os.path.join(self._temp_path,
                                         'chromeos-firmwareupdate')
        if append:
            new_shellball = working_shellball + '-%s' % append
            self.os_if.copy_file(working_shellball, new_shellball)
            working_shellball = new_shellball

        self.os_if.run_shell_command(
                'sh %s --sb_repack %s' % (working_shellball, self._work_path))

        self._check_shellball(working_shellball, 'repacked shellball')

        # use the shellball that was repacked, to catch repacking problems.
        self._detect_image_paths(working_shellball)
        return working_shellball

    def reset_shellball(self):
        """Extract shellball, then revert the AP and EC handlers' data."""
        self._create_temp_dir()
        self.extract_shellball()
        self.reload_images()

    def reload_images(self):
        """Reload handlers from the on-disk images, in case they've changed."""
        bios_file = os.path.join(self._work_path, self._bios_path)
        self._real_bios_handler.deinit()
        self._real_bios_handler.init(bios_file)
        if self._real_ec_handler.is_available():
            ec_file = os.path.join(self._work_path, self._ec_path)
            self._real_ec_handler.deinit()
            self._real_ec_handler.init(ec_file, allow_fallback=True)

    def run_firmwareupdate(self, mode, append=None, options=None):
        """Do firmwareupdate with updater in temp_dir.

        @param append: decide which shellball to use with format
                chromeos-firmwareupdate-[append].
                Use'chromeos-firmwareupdate' if append is None.
        @param mode: ex.'autoupdate', 'recovery', 'bootok', 'factory_install'...
        @param options: ex. ['--noupdate_ec', '--force'] or [] or None.

        @type append: str
        @type mode: str
        @type options: list | tuple | None
        """
        if mode == 'bootok':
            # Since CL:459837, bootok is moved to chromeos-setgoodfirmware.
            set_good_cmd = '/usr/sbin/chromeos-setgoodfirmware'
            if os.path.isfile(set_good_cmd):
                return self.os_if.run_shell_command_get_status(set_good_cmd)

        updater = os.path.join(self._temp_path, 'chromeos-firmwareupdate')
        if append:
            updater = '%s-%s' % (updater, append)

        self._check_shellball(updater, 'shellball to be executed')

        if options is None:
            options = []
        if isinstance(options, tuple):
            options = list(options)

        def _has_emulate(option):
            return option == '--emulate' or option.startswith('--emulate=')

        if self.os_if.test_mode and not filter(_has_emulate, options):
            # if in test mode, forcibly use --emulate, if not already used.
            fake_bios = os.path.join(self._temp_path, 'rpc-test-fake-bios.bin')
            if not os.path.exists(fake_bios):
                bios_reader = self._create_handler('bios', 'tmp')
                bios_reader.dump_flash(fake_bios)
            options = ['--emulate', fake_bios] + options

        update_cmd = '/bin/sh %s --mode %s %s' % (updater, mode,
                                                  ' '.join(options))

        return self.os_if.run_shell_command_get_status(update_cmd)

    def cbfs_setup_work_dir(self):
        """Sets up cbfs on DUT.

        Finds bios.bin on the DUT and sets up a temp dir to operate on
        bios.bin.  If a bios.bin was specified, it is copied to the DUT
        and used instead of the native bios.bin.

        Returns:
            The cbfs work directory path.
        """

        self.os_if.remove_dir(self._cbfs_work_path)
        self.os_if.copy_dir(self._work_path, self._cbfs_work_path)

        return self._cbfs_work_path

    def cbfs_extract_chip(self, fw_name, extension='.bin'):
        """Extracts chip firmware blob from cbfs.

        For a given chip type, looks for the corresponding firmware
        blob and hash in the specified bios.  The firmware blob and
        hash are extracted into self._cbfs_work_path.

        The extracted blobs will be <fw_name><extension> and
        <fw_name>.hash located in cbfs_work_path.

        Args:
            fw_name: Chip firmware name to be extracted.
            extension: Extension of the name of the cbfs component.

        Returns:
            Boolean success status.
        """

        bios = os.path.join(self._cbfs_work_path, self._bios_path)
        fw = fw_name
        cbfs_extract = '%s %s extract -r FW_MAIN_A -n %s%%s -f %s%%s' % (
                self.CBFSTOOL, bios, fw, os.path.join(self._cbfs_work_path,
                                                      fw))

        cmd = cbfs_extract % (extension, extension)
        if self.os_if.run_shell_command_get_status(cmd) != 0:
            return False

        cmd = cbfs_extract % ('.hash', '.hash')
        if self.os_if.run_shell_command_get_status(cmd) != 0:
            return False

        return True

    def cbfs_extract_diagnostics(self, diag_name, local_filename):
        """Runs cbfstool to extract a diagnostics image.

        @param diag_name: Name of the diagnostics image in CBFS
        @param local_filename: Filename for storing the diagnostics image in the
            CBFS working directory
        """
        bios_path = os.path.join(self._cbfs_work_path, self._bios_path)
        cbfs_extract = '%s %s extract -m x86 -r RW_LEGACY -n %s -f %s' % (
                self.CBFSTOOL, bios_path, diag_name,
                os.path.join(self._cbfs_work_path, local_filename))

        self.os_if.run_shell_command(cbfs_extract)

    def cbfs_get_chip_hash(self, fw_name):
        """Returns chip firmware hash blob.

        For a given chip type, returns the chip firmware hash blob.
        Before making this request, the chip blobs must have been
        extracted from cbfs using cbfs_extract_chip().
        The hash data is returned as hexadecimal string.

        Args:
            fw_name:
                Chip firmware name whose hash blob to get.

        Returns:
            Boolean success status.

        Raises:
            shell_wrapper.ShellError: Underlying remote shell
                operations failed.
        """

        hexdump_cmd = '%s %s.hash' % (
                self.HEXDUMP, os.path.join(self._cbfs_work_path, fw_name))
        hashblob = self.os_if.run_shell_command_get_output(hexdump_cmd)
        return hashblob

    def cbfs_replace_chip(self, fw_name, extension='.bin'):
        """Replaces chip firmware in CBFS (bios.bin).

        For a given chip type, replaces its firmware blob and hash in
        bios.bin.  All files referenced are expected to be in the
        directory set up using cbfs_setup_work_dir().

        Args:
            fw_name: Chip firmware name to be replaced.
            extension: Extension of the name of the cbfs component.

        Returns:
            Boolean success status.

        Raises:
            shell_wrapper.ShellError: Underlying remote shell
                operations failed.
        """

        bios = os.path.join(self._cbfs_work_path, self._bios_path)
        rm_hash_cmd = '%s %s remove -r FW_MAIN_A,FW_MAIN_B -n %s.hash' % (
                self.CBFSTOOL, bios, fw_name)
        rm_bin_cmd = '%s %s remove -r FW_MAIN_A,FW_MAIN_B -n %s%s' % (
                self.CBFSTOOL, bios, fw_name, extension)
        expand_cmd = '%s %s expand -r FW_MAIN_A,FW_MAIN_B' % (self.CBFSTOOL,
                                                              bios)
        add_hash_cmd = ('%s %s add -r FW_MAIN_A,FW_MAIN_B -t raw -c none '
                        '-f %s.hash -n %s.hash') % (
                                self.CBFSTOOL, bios,
                                os.path.join(self._cbfs_work_path,
                                             fw_name), fw_name)
        add_bin_cmd = ('%s %s add -r FW_MAIN_A,FW_MAIN_B -t raw -c lzma '
                       '-f %s%s -n %s%s') % (
                               self.CBFSTOOL, bios,
                               os.path.join(self._cbfs_work_path, fw_name),
                               extension, fw_name, extension)
        truncate_cmd = '%s %s truncate -r FW_MAIN_A,FW_MAIN_B' % (
                self.CBFSTOOL, bios)

        self.os_if.run_shell_command(rm_hash_cmd)
        self.os_if.run_shell_command(rm_bin_cmd)
        try:
            self.os_if.run_shell_command(expand_cmd)
        except shell_wrapper.ShellError:
            self.os_if.log(
                    ('%s may be too old, '
                     'continuing without "expand" support') % self.CBFSTOOL)

        self.os_if.run_shell_command(add_hash_cmd)
        self.os_if.run_shell_command(add_bin_cmd)
        try:
            self.os_if.run_shell_command(truncate_cmd)
        except shell_wrapper.ShellError:
            self.os_if.log(
                    ('%s may be too old, '
                     'continuing without "truncate" support') % self.CBFSTOOL)

        return True

    def cbfs_replace_diagnostics(self, diag_name, local_filename):
        """Runs cbfstool to replace a diagnostics image in the firmware image.

        @param diag_name: Name of the diagnostics image in CBFS
        @param local_filename: Filename for storing the diagnostics image in the
            CBFS working directory
        """
        bios_path = os.path.join(self._cbfs_work_path, self._bios_path)
        rm_cmd = '%s %s remove -r RW_LEGACY -n %s' % (
                self.CBFSTOOL, bios_path, diag_name)
        expand_cmd = '%s %s expand -r RW_LEGACY' % (self.CBFSTOOL, bios_path)
        add_cmd = ('%s %s add-payload -r RW_LEGACY -c lzma -n %s -f %s') % (
                self.CBFSTOOL, bios_path, diag_name,
                os.path.join(self._cbfs_work_path, local_filename))
        truncate_cmd = '%s %s truncate -r RW_LEGACY' % (
                self.CBFSTOOL, bios_path)

        self.os_if.run_shell_command(rm_cmd)

        try:
            self.os_if.run_shell_command(expand_cmd)
        except shell_wrapper.ShellError:
            self.os_if.log(
                    '%s may be too old, continuing without "expand" support'
                    % self.CBFSTOOL)

        self.os_if.run_shell_command(add_cmd)

        try:
            self.os_if.run_shell_command(truncate_cmd)
        except shell_wrapper.ShellError:
            self.os_if.log(
                    '%s may be too old, continuing without "truncate" support'
                    % self.CBFSTOOL)

    def cbfs_sign_and_flash(self):
        """Signs CBFS (bios.bin) and flashes it."""
        self.resign_firmware(work_path=self._cbfs_work_path)
        bios = self._get_handler('bios')
        bios.new_image(os.path.join(self._cbfs_work_path, self._bios_path))
        bios.write_whole()
        return True

    def copy_bios(self, filename):
        """Copy the shellball BIOS to the given name in the temp dir

        @param filename: the filename to use for the copy
        @return: the full path of the BIOS

        @type filename: str
        @rtype: str
        """
        if not isinstance(filename, basestring):
            raise FirmwareUpdaterError(
                    "Filename must be a string: %s" % repr(filename))
        src_bios = os.path.join(self._work_path, self._bios_path)
        dst_bios = os.path.join(self._temp_path, filename)
        self.os_if.copy_file(src_bios, dst_bios)
        return dst_bios

    def get_temp_path(self):
        """Get temp directory path."""
        return self._temp_path

    def get_keys_path(self):
        """Get keys directory path."""
        return self._keys_path

    def get_work_path(self):
        """Get work directory path."""
        return self._work_path

    def get_bios_relative_path(self):
        """Gets the relative path of the bios image in the shellball."""
        return self._bios_path

    def get_ec_relative_path(self):
        """Gets the relative path of the ec image in the shellball."""
        return self._ec_path
