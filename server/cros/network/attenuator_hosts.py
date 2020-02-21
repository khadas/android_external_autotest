# Copyright (c) 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Attenuator hostnames with fixed loss overhead on a given antenna line. """

# This map represents the fixed loss overhead on a given antenna line.
# The map maps from:
#     attenuator hostname -> attenuator number -> frequency -> loss in dB.
HOST_FIXED_ATTENUATIONS = {
        'chromeos1-dev-host4-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 56},
                2: {2437: 53, 5220: 59, 5765: 59},
                3: {2437: 57, 5220: 56, 5765: 56}},
        'chromeos1-dev-host15-attenuator': {
                0: {2437: 32, 5220: 36, 5765: 38},
                1: {2437: 35, 5220: 34, 5765: 36},
                2: {2437: 32, 5220: 36, 5765: 38},
                3: {2437: 35, 5220: 34, 5765: 36}},
        'chromeos1-dev-host16-attenuator': {
                0: {2437: 32, 5220: 37, 5765: 39},
                1: {2437: 35, 5220: 34, 5765: 36},
                2: {2437: 32, 5220: 37, 5765: 39},
                3: {2437: 35, 5220: 34, 5765: 36}},
        'chromeos1-dev-host17-attenuator': {
                0: {2437: 33, 5220: 36, 5765: 38},
                1: {2437: 35, 5220: 34, 5765: 36},
                2: {2437: 33, 5220: 36, 5765: 38},
                3: {2437: 35, 5220: 34, 5765: 36}},
        'chromeos1-dev-host18-attenuator': {
                0: {2437: 32, 5220: 36, 5765: 37},
                1: {2437: 35, 5220: 34, 5765: 35},
                2: {2437: 32, 5220: 36, 5765: 37},
                3: {2437: 35, 5220: 34, 5765: 35}},
        'chromeos1-dev-host19-attenuator': {
                0: {2437: 52, 5220: 57, 5765: 60},
                1: {2437: 55, 5220: 54, 5765: 56},
                2: {2437: 52, 5220: 57, 5765: 60},
                3: {2437: 55, 5220: 54, 5765: 55}},
        'chromeos1-dev-host20-attenuator': {
                0: {2437: 53, 5220: 57, 5765: 62},
                1: {2437: 57, 5220: 55, 5765: 55},
                2: {2437: 53, 5220: 57, 5765: 61},
                3: {2437: 57, 5220: 55, 5765: 55}},
        'chromeos1-test-host2-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 58},
                1: {2437: 57, 5220: 57, 5765: 59},
                2: {2437: 53, 5220: 59, 5765: 58},
                3: {2437: 57, 5220: 57, 5765: 59}},
        # Row 3 rack 8 is OTA grover setups
        'chromeos15-row3-rack8-host1-attenuator': {
                0: {2437: 28, 5220: 32, 5765: 34},
                1: {2437: 32, 5220: 31, 5765: 33},
                2: {2437: 28, 5220: 32, 5765: 34},
                3: {2437: 31, 5220: 31, 5765: 32}},
        'chromeos15-row3-rack8-host2-attenuator': {
                0: {2437: 28, 5220: 32, 5765: 34},
                1: {2437: 31, 5220: 30, 5765: 32},
                2: {2437: 27, 5220: 31, 5765: 33},
                3: {2437: 31, 5220: 30, 5765: 32}},
        'chromeos15-row3-rack8-host3-attenuator': {
                0: {2437: 27, 5220: 31, 5765: 32},
                1: {2437: 31, 5220: 30, 5765: 31},
                2: {2437: 27, 5220: 31, 5765: 32},
                3: {2437: 31, 5220: 30, 5765: 31}},
        'chromeos15-row3-rack8-host4-attenuator': {
                0: {2437: 28, 5220: 33, 5765: 34},
                1: {2437: 32, 5220: 31, 5765: 32},
                2: {2437: 28, 5220: 33, 5765: 34},
                3: {2437: 31, 5220: 31, 5765: 32}},
        'chromeos15-row3-rack8-host5-attenuator': {
                0: {2437: 27, 5220: 31, 5765: 33},
                1: {2437: 31, 5220: 30, 5765: 31},
                2: {2437: 27, 5220: 31, 5765: 33},
                3: {2437: 31, 5220: 29, 5765: 31}},
        'chromeos15-row3-rack8-host6-attenuator': {
                0: {2437: 28, 5220: 32, 5765: 34},
                1: {2437: 31, 5220: 30, 5765: 32},
                2: {2437: 28, 5220: 32, 5765: 35},
                3: {2437: 31, 5220: 31, 5765: 32}},
        # Row 3 racks 9 to 14 are conductive grover setups
        'chromeos15-row3-rack9-host1-attenuator': {
                0: {2437: 53, 5220: 60, 5765: 59},
                1: {2437: 57, 5220: 57, 5765: 58},
                2: {2437: 53, 5220: 59, 5765: 60},
                3: {2437: 57, 5220: 57, 5765: 60}},
        'chromeos15-row3-rack9-host2-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 60},
                2: {2437: 53, 5220: 58, 5765: 58},
                3: {2437: 57, 5220: 58, 5765: 61}},
        'chromeos15-row3-rack9-host3-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 59},
                2: {2437: 53, 5220: 58, 5765: 59},
                3: {2437: 57, 5220: 58, 5765: 60}},
        'chromeos15-row3-rack9-host4-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 60},
                2: {2437: 53, 5220: 58, 5765: 59},
                3: {2437: 57, 5220: 57, 5765: 60}},
        'chromeos15-row3-rack9-host5-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 59},
                2: {2437: 53, 5220: 58, 5765: 60},
                3: {2437: 57, 5220: 58, 5765: 60}},
        'chromeos15-row3-rack9-host6-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 57, 5765: 60},
                2: {2437: 53, 5220: 59, 5765: 60},
                3: {2437: 57, 5220: 58, 5765: 58}},
        'chromeos15-row3-rack10-host1-attenuator': {
                0: {2437: 52, 5220: 55, 5765: 56},
                1: {2437: 55, 5220: 53, 5765: 57},
                2: {2437: 52, 5220: 55, 5765: 57},
                3: {2437: 55, 5220: 53, 5765: 57}},
        'chromeos15-row3-rack10-host2-attenuator': {
                0: {2437: 52, 5220: 56, 5765: 58},
                1: {2437: 55, 5220: 54, 5765: 58},
                2: {2437: 52, 5220: 56, 5765: 58},
                3: {2437: 55, 5220: 54, 5765: 57}},
        'chromeos15-row3-rack10-host3-attenuator': {
                0: {2437: 52, 5220: 55, 5765: 60},
                1: {2437: 55, 5220: 54, 5765: 59},
                2: {2437: 52, 5220: 55, 5765: 61},
                3: {2437: 55, 5220: 53, 5765: 59}},
        'chromeos15-row3-rack10-host4-attenuator': {
                0: {2437: 51, 5220: 55, 5765: 59},
                1: {2437: 55, 5220: 53, 5765: 58},
                2: {2437: 51, 5220: 54, 5765: 59},
                3: {2437: 55, 5220: 53, 5765: 58}},
        'chromeos15-row3-rack10-host5-attenuator': {
                0: {2437: 51, 5220: 55, 5765: 60},
                1: {2437: 55, 5220: 53, 5765: 58},
                2: {2437: 51, 5220: 55, 5765: 60},
                3: {2437: 55, 5220: 53, 5765: 58}},
        'chromeos15-row3-rack10-host6-attenuator': {
                0: {2437: 52, 5220: 55, 5765: 57},
                1: {2437: 55, 5220: 54, 5765: 59},
                2: {2437: 52, 5220: 55, 5765: 57},
                3: {2437: 55, 5220: 54, 5765: 57}},
        'chromeos15-row3-rack11-host1-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 57},
                1: {2437: 56, 5220: 56, 5765: 58},
                2: {2437: 53, 5220: 58, 5765: 57},
                3: {2437: 56, 5220: 56, 5765: 57}},
        'chromeos15-row3-rack11-host2-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 56},
                1: {2437: 56, 5220: 56, 5765: 58},
                2: {2437: 53, 5220: 59, 5765: 56},
                3: {2437: 56, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack11-host3-attenuator': {
                0: {2437: 52, 5220: 57, 5765: 59},
                1: {2437: 55, 5220: 55, 5765: 54},
                2: {2437: 52, 5220: 57, 5765: 59},
                3: {2437: 55, 5220: 55, 5765: 54}},
        'chromeos15-row3-rack11-host4-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 57, 5765: 59},
                3: {2437: 56, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack11-host5-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 58},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 53, 5220: 58, 5765: 59},
                3: {2437: 56, 5220: 55, 5765: 55}},
        'chromeos15-row3-rack11-host6-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 59},
                1: {2437: 55, 5220: 55, 5765: 54},
                2: {2437: 52, 5220: 57, 5765: 59},
                3: {2437: 55, 5220: 55, 5765: 54}},
        'chromeos15-row3-rack12-host1-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 58},
                1: {2437: 55, 5220: 57, 5765: 55},
                2: {2437: 57, 5220: 59, 5765: 58},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack12-host2-attenuator': {
                0: {2437: 52, 5220: 59, 5765: 56},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 59, 5765: 57},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack12-host3-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 57},
                1: {2437: 55, 5220: 57, 5765: 55},
                2: {2437: 52, 5220: 59, 5765: 59},
                3: {2437: 55, 5220: 59, 5765: 55}},
        'chromeos15-row3-rack12-host4-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 56},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 58, 5765: 56},
                3: {2437: 55, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack12-host5-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 58},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 59, 5765: 59},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack12-host6-attenuator': {
                0: {2437: 52, 5220: 59, 5765: 57},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 58, 5765: 56},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack13-host1-attenuator': {
                0: {2437: 59, 5220: 59, 5765: 59},
                1: {2437: 52, 5220: 54, 5765: 54},
                2: {2437: 59, 5220: 59, 5765: 59},
                3: {2437: 52, 5220: 54, 5765: 54}},
        'chromeos15-row3-rack13-host2-attenuator': {
                0: {2437: 64, 5220: 62, 5765: 62},
                1: {2437: 58, 5220: 57, 5765: 57},
                2: {2437: 64, 5220: 62, 5765: 62},
                3: {2437: 58, 5220: 57, 5765: 57}},
        'chromeos15-row3-rack13-host3-attenuator': {
                0: {2437: 60, 5220: 58, 5765: 58},
                1: {2437: 52, 5220: 57, 5765: 57},
                2: {2437: 60, 5220: 58, 5765: 58},
                3: {2437: 52, 5220: 57, 5765: 57}},
        'chromeos15-row3-rack13-host4-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 58},
                1: {2437: 59, 5220: 60, 5765: 60},
                2: {2437: 52, 5220: 58, 5765: 58},
                3: {2437: 59, 5220: 60, 5765: 60}},
        'chromeos15-row3-rack13-host5-attenuator': {
                0: {2437: 58, 5220: 60, 5765: 60},
                1: {2437: 53, 5220: 58, 5765: 58},
                2: {2437: 58, 5220: 60, 5765: 60},
                3: {2437: 53, 5220: 58, 5765: 58}},
        'chromeos15-row3-rack13-host6-attenuator': {
                0: {2437: 52, 5220: 56, 5765: 58},
                1: {2437: 53, 5220: 56, 5765: 57},
                2: {2437: 52, 5220: 56, 5765: 58},
                3: {2437: 53, 5220: 56, 5765: 57}},
        'chromeos15-row3-rack14-host1-attenuator': {
                0: {2437: 53, 5220: 56, 5765: 56},
                1: {2437: 52, 5220: 56, 5765: 56},
                2: {2437: 53, 5220: 56, 5765: 56},
                3: {2437: 52, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack14-host2-attenuator': {
                0: {2437: 59, 5220: 59, 5765: 59},
                1: {2437: 59, 5220: 60, 5765: 60},
                2: {2437: 59, 5220: 59, 5765: 59},
                3: {2437: 59, 5220: 60, 5765: 60}},
        'chromeos15-row3-rack14-host3-attenuator': {
                0: {2437: 52, 5220: 56, 5765: 56},
                1: {2437: 64, 5220: 63, 5765: 63},
                2: {2437: 52, 5220: 56, 5765: 56},
                3: {2437: 64, 5220: 63, 5765: 63}},
        'chromeos15-row3-rack14-host4-attenuator': {
                0: {2437: 52, 5220: 55, 5765: 55},
                1: {2437: 58, 5220: 58, 5765: 58},
                2: {2437: 52, 5220: 55, 5765: 55},
                3: {2437: 58, 5220: 58, 5765: 58}},
        'chromeos15-row3-rack14-host5-attenuator': {
                0: {2437: 57, 5220: 58, 5765: 58},
                1: {2437: 52, 5220: 55, 5765: 55},
                2: {2437: 57, 5220: 58, 5765: 58},
                3: {2437: 52, 5220: 55, 5765: 55}},
        'chromeos15-row3-rack14-host6-attenuator': {
                0: {2437: 57, 5220: 57, 5765: 57},
                1: {2437: 52, 5220: 55, 5765: 55},
                2: {2437: 57, 5220: 57, 5765: 57},
                3: {2437: 52, 5220: 55, 5765: 55}},
}
