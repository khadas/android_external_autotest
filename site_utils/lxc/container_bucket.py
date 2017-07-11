# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import socket
import time

import common
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.graphite import autotest_es
from autotest_lib.site_utils.lxc import Container
from autotest_lib.site_utils.lxc import config as lxc_config
from autotest_lib.site_utils.lxc import constants
from autotest_lib.site_utils.lxc import lxc
from autotest_lib.site_utils.lxc import utils as lxc_utils
from autotest_lib.site_utils.lxc.cleanup_if_fail import cleanup_if_fail

try:
    from chromite.lib import metrics
except ImportError:
    metrics = utils.metrics_mock


class ContainerBucket(object):
    """A wrapper class to interact with containers in a specific container path.
    """

    def __init__(self, container_path=constants.DEFAULT_CONTAINER_PATH):
        """Initialize a ContainerBucket.

        @param container_path: Path to the directory used to store containers.
                               Default is set to AUTOSERV/container_path in
                               global config.
        """
        self.container_path = os.path.realpath(container_path)


    def get_all(self):
        """Get details of all containers.

        @return: A dictionary of all containers with detailed attributes,
                 indexed by container name.
        """
        info_collection = lxc.get_container_info(self.container_path)
        containers = {}
        for info in info_collection:
            container = Container(self.container_path, info)
            containers[container.name] = container
        return containers


    def get(self, name):
        """Get a container with matching name.

        @param name: Name of the container.

        @return: A container object with matching name. Returns None if no
                 container matches the given name.
        """
        return self.get_all().get(name, None)


    def exist(self, name):
        """Check if a container exists with the given name.

        @param name: Name of the container.

        @return: True if the container with the given name exists, otherwise
                 returns False.
        """
        return self.get(name) != None


    def destroy_all(self):
        """Destroy all containers, base must be destroyed at the last.
        """
        containers = self.get_all().values()
        for container in sorted(
            containers, key=lambda n: 1 if n.name == constants.BASE else 0):
            logging.info('Destroy container %s.', container.name)
            container.destroy()


    @metrics.SecondsTimerDecorator(
        '%s/create_from_base_duration' % constants.STATS_KEY)
    def create_from_base(self, name, disable_snapshot_clone=False,
                         force_cleanup=False):
        """Create a container from the base container.

        @param name: Name of the container.
        @param disable_snapshot_clone: Set to True to force to clone without
                using snapshot clone even if the host supports that.
        @param force_cleanup: Force to cleanup existing container.

        @return: A Container object for the created container.

        @raise ContainerError: If the container already exist.
        @raise error.CmdError: If lxc-clone call failed for any reason.
        """
        if self.exist(name) and not force_cleanup:
            raise error.ContainerError('Container %s already exists.' % name)

        use_snapshot = (constants.SUPPORT_SNAPSHOT_CLONE and not
                        disable_snapshot_clone)

        try:
            return self.clone_container(path=self.container_path,
                                        name=constants.BASE,
                                        new_path=self.container_path,
                                        new_name=name,
                                        snapshot=use_snapshot,
                                        cleanup=force_cleanup)
        except error.CmdError:
            if not use_snapshot:
                raise
            else:
                # Snapshot clone failed, retry clone without snapshot.
                container = self.clone_container(path=self.container_path,
                                                 name=constants.BASE,
                                                 new_path=self.container_path,
                                                 new_name=name,
                                                 snapshot=False,
                                                 cleanup=force_cleanup)
                # Report metadata about retry success.
                autotest_es.post(
                    use_http=True,
                    type_str=constants.CONTAINER_CREATE_RETRY_METADB_TYPE,
                    metadata={'drone': socket.gethostname(),
                              'name': name,
                              'success': True})
                return container


    def clone_container(self, path, name, new_path, new_name, snapshot=False,
                        cleanup=False):
        """Clone one container from another.

        @param path: LXC path for the source container.
        @param name: Name of the source container.
        @param new_path: LXC path for the cloned container.
        @param new_name: Name for the cloned container.
        @param snapshot: Whether to snapshot, or create a full clone.
        @param cleanup: If a container with the given name and path already
                exist, clean it up first.

        @return: A Container object for the created container.

        @raise ContainerError: If the container already exists.
        @raise error.CmdError: If lxc-clone call failed for any reason.
        """
        # Cleanup existing container with the given name.
        container_folder = os.path.join(new_path, new_name)

        if lxc_utils.path_exists(container_folder):
            if not cleanup:
                raise error.ContainerError('Container %s already exists.' %
                                           new_name)
            container = Container(new_path, {'name': name})
            try:
                container.destroy()
            except error.CmdError as e:
                # The container could be created in a incompleted state. Delete
                # the container folder instead.
                logging.warn('Failed to destroy container %s, error: %s',
                             name, e)
                utils.run('sudo rm -rf "%s"' % container_folder)

        snapshot_arg = '-s' if snapshot else ''
        # overlayfs is the default clone backend storage. However it is not
        # supported in Ganeti yet. Use aufs as the alternative.
        aufs_arg = '-B aufs' if utils.is_vm() and snapshot else ''
        cmd = (('sudo lxc-clone --lxcpath %s --newpath %s '
                '--orig %s --new %s %s %s') %
               (path, new_path, name, new_name, snapshot_arg, aufs_arg))

        utils.run(cmd)
        return self.get(new_name)


    @cleanup_if_fail()
    def setup_base(self, name=constants.BASE, force_delete=False):
        """Setup base container.

        @param name: Name of the base container, default to base.
        @param force_delete: True to force to delete existing base container.
                             This action will destroy all running test
                             containers. Default is set to False.
        """
        if not self.container_path:
            raise error.ContainerError(
                    'You must set a valid directory to store containers in '
                    'global config "AUTOSERV/ container_path".')

        if not os.path.exists(self.container_path):
            os.makedirs(self.container_path)

        base_path = os.path.join(self.container_path, name)
        if self.exist(name) and not force_delete:
            logging.error(
                    'Base container already exists. Set force_delete to True '
                    'to force to re-stage base container. Note that this '
                    'action will destroy all running test containers')
            # Set proper file permission. base container in moblab may have
            # owner of not being root. Force to update the folder's owner.
            # TODO(dshi): Change root to current user when test container can be
            # unprivileged container.
            utils.run('sudo chown -R root "%s"' % base_path)
            utils.run('sudo chgrp -R root "%s"' % base_path)
            return

        # Destroy existing base container if exists.
        if self.exist(name):
            # TODO: We may need to destroy all snapshots created from this base
            # container, not all container.
            self.destroy_all()

        # Download and untar the base container.
        tar_path = os.path.join(self.container_path, '%s.tar.xz' % name)
        path_to_cleanup = [tar_path, base_path]
        for path in path_to_cleanup:
            if os.path.exists(path):
                utils.run('sudo rm -rf "%s"' % path)
        container_url = constants.CONTAINER_BASE_URL_FMT % name
        lxc.download_extract(container_url, tar_path, self.container_path)
        # Remove the downloaded container tar file.
        utils.run('sudo rm "%s"' % tar_path)
        # Set proper file permission.
        # TODO(dshi): Change root to current user when test container can be
        # unprivileged container.
        utils.run('sudo chown -R root "%s"' % base_path)
        utils.run('sudo chgrp -R root "%s"' % base_path)

        # Update container config with container_path from global config.
        config_path = os.path.join(base_path, 'config')
        utils.run('sudo sed -i "s|container_dir|%s|g" "%s"' %
                  (self.container_path, config_path))


    @metrics.SecondsTimerDecorator(
        '%s/setup_test_duration' % constants.STATS_KEY)
    @cleanup_if_fail()
    def setup_test(self, name, job_id, server_package_url, result_path,
                   control=None, skip_cleanup=False, job_folder=None,
                   dut_name=None):
        """Setup test container for the test job to run.

        The setup includes:
        1. Install autotest_server package from given url.
        2. Copy over local shadow_config.ini.
        3. Mount local site-packages.
        4. Mount test result directory.

        TODO(dshi): Setup also needs to include test control file for autoserv
                    to run in container.

        @param name: Name of the container.
        @param job_id: Job id for the test job to run in the test container.
        @param server_package_url: Url to download autotest_server package.
        @param result_path: Directory to be mounted to container to store test
                            results.
        @param control: Path to the control file to run the test job. Default is
                        set to None.
        @param skip_cleanup: Set to True to skip cleanup, used to troubleshoot
                             container failures.
        @param job_folder: Folder name of the job, e.g., 123-debug_user.
        @param dut_name: Name of the dut to run test, used as the hostname of
                         the container. Default is None.
        @return: A Container object for the test container.

        @raise ContainerError: If container does not exist, or not running.
        """
        start_time = time.time()

        if not os.path.exists(result_path):
            raise error.ContainerError('Result directory does not exist: %s',
                                       result_path)
        result_path = os.path.abspath(result_path)

        # Save control file to result_path temporarily. The reason is that the
        # control file in drone_tmp folder can be deleted during scheduler
        # restart. For test not using SSP, the window between test starts and
        # control file being picked up by the test is very small (< 2 seconds).
        # However, for tests using SSP, it takes around 1 minute before the
        # container is setup. If scheduler is restarted during that period, the
        # control file will be deleted, and the test will fail.
        if control:
            control_file_name = os.path.basename(control)
            safe_control = os.path.join(result_path, control_file_name)
            utils.run('cp %s %s' % (control, safe_control))

        # Create test container from the base container.
        container = self.create_from_base(name)

        # Update the hostname of the test container to be `dut-name`.
        # Some TradeFed tests use hostname in test results, which is used to
        # group test results in dashboard. The default container name is set to
        # be the name of the folder, which is unique (as it is composed of job
        # id and timestamp. For better result view, the container's hostname is
        # set to be a string containing the dut hostname.
        if dut_name:
            config_file = os.path.join(container.container_path, name, 'config')
            lxc_utsname_setting = (
                'lxc.utsname = ' +
                (constants.CONTAINER_UTSNAME_FORMAT %
                 dut_name.replace('.', '-')))
            utils.run(
                constants.APPEND_CMD_FMT % {'content': lxc_utsname_setting,
                                            'file': config_file})

        # Deploy server side package
        usr_local_path = os.path.join(container.rootfs, 'usr', 'local')
        autotest_pkg_path = os.path.join(usr_local_path,
                                         'autotest_server_package.tar.bz2')
        autotest_path = os.path.join(usr_local_path, 'autotest')
        # sudo is required so os.makedirs may not work.
        utils.run('sudo mkdir -p %s'% usr_local_path)

        lxc.download_extract(
            server_package_url, autotest_pkg_path, usr_local_path)
        deploy_config_manager = lxc_config.DeployConfigManager(container)
        deploy_config_manager.deploy_pre_start()

        # Copy over control file to run the test job.
        if control:
            container_drone_temp = os.path.join(autotest_path, 'drone_tmp')
            utils.run('sudo mkdir -p %s'% container_drone_temp)
            container_control_file = os.path.join(
                    container_drone_temp, control_file_name)
            # Move the control file stored in the result folder to container.
            utils.run('sudo mv %s %s' % (safe_control, container_control_file))

        if constants.IS_MOBLAB:
            site_packages_path = constants.MOBLAB_SITE_PACKAGES
            site_packages_container_path = (
                constants.MOBLAB_SITE_PACKAGES_CONTAINER[1:])
        else:
            site_packages_path = os.path.join(common.autotest_dir,
                                              'site-packages')
            site_packages_container_path = os.path.join(
                    lxc_config.CONTAINER_AUTOTEST_DIR, 'site-packages')
        mount_entries = [(site_packages_path, site_packages_container_path,
                          True),
                         (os.path.join(common.autotest_dir, 'puppylab'),
                          os.path.join(lxc_config.CONTAINER_AUTOTEST_DIR,
                                       'puppylab'),
                          True),
                         (result_path,
                          os.path.join(constants.RESULT_DIR_FMT % job_folder),
                          False),
                        ]
        for mount_config in deploy_config_manager.mount_configs:
            mount_entries.append((mount_config.source, mount_config.target,
                                  mount_config.readonly))
        # Update container config to mount directories.
        for source, destination, readonly in mount_entries:
            container.mount_dir(source, destination, readonly)

        # Update file permissions.
        # TODO(dshi): crbug.com/459344 Skip following action when test container
        # can be unprivileged container.
        utils.run('sudo chown -R root "%s"' % autotest_path)
        utils.run('sudo chgrp -R root "%s"' % autotest_path)

        container.start(name)
        deploy_config_manager.deploy_post_start()

        container.modify_import_order()

        container.verify_autotest_setup(job_folder)

        autotest_es.post(use_http=True,
                         type_str=constants.CONTAINER_CREATE_METADB_TYPE,
                         metadata={'drone': socket.gethostname(),
                                   'job_id': job_id,
                                   'time_used': time.time() - start_time,
                                   'success': True})

        logging.debug('Test container %s is set up.', name)
        return container
