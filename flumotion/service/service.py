# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# flumotion/service/service.py: Service startup functions
#
# Flumotion - a streaming media server
# Copyright (C) 2004 Fluendo (www.fluendo.com)

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# See "LICENSE.GPL" in the source distribution for more information.

# This program is also licensed under the Flumotion license.
# See "LICENSE.Flumotion" in the source distribution for more information.

import errno
import os
import glob
import signal

from flumotion.configure import configure
from flumotion.common import common, errors, log

class Servicer(log.Loggable):
    logCategory = 'servicer'

    def __init__(self, configDir):
        self.configDir = configDir
        self.managersDir = os.path.join(self.configDir, 'managers')
        self.workersDir = os.path.join(self.configDir, 'workers')

    def _parseManagersWorkers(self, command, args):
        # parse the given args and return two lists;
        # one of manager names to act on and one of worker names
        managers = []
        workers = []

        if not args:
            managers = self.getManagers().keys()
            workers = self.getWorkers()
            return (managers, workers)

        which = args[0]
        if which not in ['manager', 'worker']:
            raise errors.SystemError, 'Please specify either manager or worker'
            
        if len(args) < 2:
            raise errors.SystemError, 'Please specify which %s to %s' % (
                which, command)

        name = args[1]
        if which == 'manager':
            managers = self.getManagers()
            if not managers.has_key(name):
                raise errors.SystemError, 'No manager "%s"' % name
            managers = [name, ]
        elif which == 'worker':
            workers = self.getWorkers()
            if not name in workers:
                raise errors.SystemError, 'No worker with name %s' % name
            workers = [name, ]
            
        return (managers, workers)


    def getManagers(self):
        """
        @returns: a dictionary of manager names -> flow names
        """
        managers = {}

        if not os.path.exists(self.managersDir):
            raise errors.SystemError, \
                "Managers directory %s not found." % self.managersDir

        for managerDir in glob.glob(os.path.join(self.managersDir, '*')):
            flows = [] # names of flows
            # find flow files
            flowsDir = os.path.join(managerDir, 'flows')
            if os.path.exists(flowsDir):
                flowFiles = glob.glob(os.path.join(flowsDir, '*.xml'))
                for flowFile in flowFiles:
                    filename = os.path.split(flowFile)[1]
                    name = filename.split(".xml")[0]
                    flows.append(name)
            managerName = os.path.split(managerDir)[1]
            self.debug('Adding flows %r to manager %s' % (flows, managerName))
            managers[managerName] = flows
        return managers

    def getWorkers(self):
        """
        @returns: a list of worker names
        """
        workers = []

        if not os.path.exists(self.workersDir):
            raise errors.SystemError, \
                "Workers directory %s not found." % self.workersDir

        for workerFile in glob.glob(os.path.join(self.workersDir, '*.xml')):
            filename = os.path.split(workerFile)[1]
            name = filename.split(".xml")[0]
            workers.append(name)
        return workers

    def start(self, args):
        """
        Start processes as given in the args.

        If nothing specified, start all managers and workers.
        If first argument is "manager", start given manager,
        or all if none specified.
        If first argument is "worker", start given worker,
        or all if none specified.
        """
        (managers, workers) = self._parseManagersWorkers('start', args)
        managersDict = self.getManagers()
        for name in managers:
            self.startManager(name, managersDict[name])
        for name in workers:
            self.startWorker(name)

    def stop(self, args):
        """
        Stop processes as given in the args.

        If nothing specified, stop all managers and workers.
        If first argument is "manager", stop given manager,
        or all if none specified.
        If first argument is "worker", stop given worker,
        or all if none specified.
        """
        (managers, workers) = self._parseManagersWorkers('stop', args)
        for name in managers:
            self.stopManager(name)
        for name in workers:
            self.stopWorker(name)

    def status(self, args):
        """
        Give status on processes as given in the args.

        If nothing specified, stop all managers and workers.
        If first argument is "manager", stop given manager,
        or all if none specified.
        If first argument is "worker", stop given worker,
        or all if none specified.
        """
        (managers, workers) = self._parseManagersWorkers('status', args)
        for type, list in [('manager', managers), ('worker', workers)]:
            for name in list:
                pid = common.getPid(type, name)
                if not pid:
                    print "%s %s not running" % (type, name)
                    continue
                try:
                    os.kill(pid, 0)
                except OSError, e:
                    if e.errno is not errno.ESRCH:
                        raise
                    print "%s %s dead (stale pid %d)" % (type, name, pid)
                    continue
                print "%s %s is running with pid %d" % (type, name, pid)
     
    def startManager(self, name, flowNames):
        """
        Start the manager as configured in the manager directory for the given
        manager name, together with the given flows.

        @returns: whether or not the manager daemon started
        """
        managerDir = os.path.join(self.managersDir, name)
        planetFile = os.path.join(managerDir, 'planet.xml')
        if not os.path.exists(planetFile):
            raise errors.SystemError, \
                "Planet file %s does not exist" % planetFile
        self.info("Loading planet %s" % planetFile)

        flowsDir = os.path.join(managerDir, 'flows')
        flowFiles = []
        for flowName in flowNames:
            flowFile = os.path.join(flowsDir, "%s.xml" % flowName)
            if not os.path.exists(flowFile):
                raise errors.SystemError, \
                    "Flow file %s does not exist" % flowFile
            flowFiles.append(flowFile)
            self.info("Loading flow %s" % flowFile)
            
        command = "flumotion-manager -v -D %s %s" % (
            planetFile, " ".join(flowFiles))
        retval = self.startProcess(command)

        if retval is 0:
            self.debug("Waiting for pid for manager %s" % name)
            pid = common.waitPidFile('manager', name)
            if pid:
                self.debug("manager %s started with pid %d" % (name, pid))
                return True
            else:
                self.warning("manager %s could not start" % name)
                return False

        return False

    def startWorker(self, name):
        """
        Start the worker as configured in the worker directory for the given
        worker name.

        @returns: whether or not the manager daemon started
        """
        workerFile = os.path.join(self.workersDir, "%s.xml" % name)
        if not os.path.exists(workerFile):
            raise errors.SystemError, \
                "Worker file %s does not exist" % workerFile
        self.info("Loading worker %s" % workerFile)

        command = "flumotion-worker -v -D -n %s %s" % (name, workerFile)
        retval = self.startProcess(command)

        if retval is 0:
            self.debug("Waiting for pid for worker %s" % name)
            pid = common.waitPidFile('worker', name)
            if pid:
                self.debug("worker %s started with pid %d" % (name, pid))
                return True
            else:
                self.warning("worker %s could not start" % name)
                return False

        return False

    def startProcess(self, command):
        """
        Start the given process and block.
        Returns the exit status of the process, or -1 in case of another error.
        """
        status = os.system(command)
        if os.WIFEXITED(status):
            retval = os.WEXITSTATUS(status)
            return retval

        # definately something wrong
        return -1

    def stopManager(self, name):
        """
        Stop the given manager if it is running.
        """
        pid = common.getPid('manager', name)
        if not pid:
            return

        # FIXME: ensure a correct process is running this pid
        self.debug('Killing manager %s with pid %d' % (name, pid))
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError, e:
            if not e.errno == errno.ESRCH:
                raise
            self.warning('No process with pid %d' % pid)
            common.deletePidFile('manager', name)

    def stopWorker(self, name):
        """
        Stop the given worker if it is running.
        """
        pid = common.getPid('worker', name)
        if not pid:
            return

        # FIXME: ensure a correct process is running this pid
        self.debug('Killing worker %s with pid %d' % (name, pid))
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError, e:
            if not e.errno == errno.ESRCH:
                raise
            self.warning('No process with pid %d' % pid)
            common.deletePidFile('worker', name)
  
    def list(self):
        """
        List all service parts managed.
        """
        managers = self.getManagers()
        for name in managers.keys():
            flows = managers[name]
            print "manager %s" % name
            if flows:
                for flow in flows:
                   print "        flow %s" % flow

        workers = self.getWorkers()
        for worker in workers:
            print "worker  %s" % worker

