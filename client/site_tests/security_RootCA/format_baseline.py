#!/usr/bin/env python
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json


def dump_baseline(baseline):
  return json.dumps(baseline, indent=4, ensure_ascii=False,
                    sort_keys=True, separators=(',', ': ')).encode('utf-8')


if __name__ == '__main__':
  with open('./baseline', 'r+') as fp:
    baseline = json.load(fp)
    formatted = dump_baseline(baseline)
    fp.seek(0)
    fp.write(formatted)
    fp.truncate()
