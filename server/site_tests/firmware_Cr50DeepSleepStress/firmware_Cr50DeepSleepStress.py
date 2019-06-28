# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import pprint
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_Cr50DeepSleepStress(FirmwareTest):
    """Verify cr50 deep sleep after running power_SuspendStress.

    Cr50 should enter deep sleep every suspend. Verify that by checking the
    idle deep sleep count.

    @param suspend_count: The number of times to reboot or suspend the device.
    @param reset_type: a str with the cycle type: 'mem' or 'reboot'
    """
    version = 1

    SLEEP_DELAY = 20
    MIN_RESUME = 15
    MIN_SUSPEND = 15
    MEM = 'mem'

    def initialize(self, host, cmdline_args, suspend_count, reset_type):
        """Make sure the test is running with access to the cr50 console"""
        super(firmware_Cr50DeepSleepStress, self).initialize(host, cmdline_args)
        if not hasattr(self, 'cr50'):
            raise error.TestNAError('Test can only be run on devices with '
                                    'access to the Cr50 console')
        # Reset the device
        self.servo.get_power_state_controller().reset()

        # Save the original version, so we can make sure cr50 doesn't rollback.
        self.original_cr50_version = self.cr50.get_active_version_info()


    def check_cr50_state(self, expected_count, expected_version):
        """Check the reboot count and version match the expected values"""
        count = self.cr50.get_deep_sleep_count()
        version = self.cr50.get_active_version_info()

        logging.info('running %s', version)
        logging.info('After %s reboots, Cr50 resumed from deep sleep %s times',
                expected_count, count)

        mismatch = []
        if count != expected_count:
            mismatch.append('count mismatch: expected %s got %s' %
                    (expected_count, count))
        if version != expected_version:
            mismatch.append('version mismatch: expected %s got %s' %
                    (expected_version, version))

        if mismatch:
            raise error.TestFail('Deep Sleep Failure: "%s"' %
                    '" and "'.join(mismatch))


    def run_reboots(self, suspend_count):
        """Reboot the device the requested number of times

        @param suspend_count: the number of times to reboot the device.
        """
        if self.cr50.using_ccd():
            raise error.TestNAError('Reboot deep sleep tests can only be run '
                    'with a servo flex')
        # This test may be running on servo v4 with servo micro. That servo v4
        # may have a type A cable or type C cable for data communication with
        # the DUT. If it is using a type C cable, that cable will look like a
        # debug accessory. Run ccd_disable, to stop debug accessory mode and
        # prevent CCD from interfering with deep sleep. Running ccd_disable on
        # a type A servo v4 or any other servo version isn't harmful.
        self.cr50.ccd_disable()

        original_mainfw_type = 'developer' if self.checkers.crossystem_checker(
                {'mainfw_type': 'developer'}) else 'normal'

        for i in range(suspend_count):
            # Power off the device
            self.servo.get_power_state_controller().power_off()
            time.sleep(self.MIN_SUSPEND)

            # Power on the device
            self.servo.power_short_press()
            time.sleep(self.MIN_RESUME)
            self.log_basic_cr50_sleep_information()

            # Make sure it didn't boot into a different mode
            self.check_state((self.checkers.crossystem_checker,
                              {'mainfw_type': original_mainfw_type}))


    def run_suspend_resume(self, host, suspend_count):
        """Suspend the device the requested number of times

        @param host: the host object representing the DUT.
        @param suspend_count: the number of times to suspend the device.
        """
        client_at = autotest.Autotest(host)

        # Disable CCD so Cr50 can enter deep sleep
        self.cr50.ccd_disable()

        # power suspend stress needs to ssh into the DUT. If ethernet goes
        # down, raise a test error, so we can tell the difference between
        # dts ethernet issues and the dut going down during the suspend stress.
        if not host.ping_wait_up(60):
            raise error.TestError('DUT is not pingable after disabling ccd')

        # Duration is set to 0, because it is required but unused when
        # iterations is given.
        client_at.run_test('power_SuspendStress', tag='idle',
                           duration=0,
                           min_suspend=self.MIN_SUSPEND,
                           min_resume=self.MIN_RESUME,
                           check_connection=False,
                           suspend_iterations=suspend_count,
                           suspend_state=self.MEM)
        # Reenable CCD
        self.cr50.ccd_enable()


    def get_expected_ds_count(self, host, reset_type, suspend_count):
        """Returns the expected deep sleep count"""
        is_arm = self.check_ec_capability('arm')
        # x86 devices should suspend once per reset. ARM will only suspend
        # if the device enters s5.
        return 0 if (reset_type != 'reboot' and is_arm) else suspend_count


    def log_basic_cr50_sleep_information(self):
        """Log ccdstate and sleepmask.

        Run ccdstate and sleepmask to get some basic information about what
        cr50 thinks the device is doing.
        sleepmask will show what may be preventing cr50 from entering sleep.
        ccdstate will show what cr50 thinks the AP state is. If the AP is 'on'
        cr50 won't enter deep sleep.
        """
        logging.info(self.cr50.send_safe_command_get_output('sleepmask',
                ['sleepmask.*>'])[0])
        logging.info(pprint.pformat(self.cr50.get_ccdstate()))


    def run_once(self, host, suspend_count, reset_type):
        """Verify deep sleep after suspending for the given number of cycles

        The test either suspends to s3 or reboots the device depending on
        reset_type. There are two valid reset types: mem and reboot. The test
        will make sure that the device is off or in s3 long enough to ensure
        Cr50 should be able to enter deep sleep. At the end of the test, it
        checks that Cr50 entered deep sleep the same number of times it
        suspended.

        @param host: the host object representing the DUT.
        @param suspend_count: The number of cycles to suspend or reboot the
                device.
        @param reset_type: a str with the cycle type: 'mem' or 'reboot'
        """
        if self.MIN_SUSPEND + self.MIN_RESUME < self.SLEEP_DELAY:
            logging.info('Minimum suspend-resume cycle is %ds. This is '
                         'shorter than the Cr50 idle timeout. Cr50 may not '
                         'enter deep sleep every cycle',
                         self.MIN_SUSPEND + self.MIN_RESUME)
        if not suspend_count:
            raise error.TestFail('Need to provide non-zero suspend_count')

        # Clear the deep sleep count
        logging.info('Clear Cr50 deep sleep count')
        self.cr50.clear_deep_sleep_count()
        self.log_basic_cr50_sleep_information()

        if reset_type == 'reboot':
            self.run_reboots(suspend_count)
        elif reset_type == 'mem':
            self.run_suspend_resume(host, suspend_count)
        else:
            raise error.TestNAError('Invalid reset_type. Use "mem" or "reboot"')

        self.log_basic_cr50_sleep_information()
        # Cr50 should enter deep sleep once per suspend cycle if deep sleep is
        # supported
        expected_ds_count = self.get_expected_ds_count(host, reset_type,
                suspend_count)
        self.check_cr50_state(expected_ds_count, self.original_cr50_version)
