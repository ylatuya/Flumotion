# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# flumotion/worker/main.py: main function of flumotion-worker
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

import optparse
import os

from twisted.internet import reactor

from flumotion.utils import log
from flumotion.worker import worker
from flumotion.twisted import cred

def main(args):
    parser = optparse.OptionParser()

    group = optparse.OptionGroup(parser, "Worker options")
    group.add_option('-H', '--host',
                     action="store", type="string", dest="host",
                     default="localhost",
                     help="Manager to connect to [default localhost]")
    group.add_option('-P', '--port',
                     action="store", type="int", dest="port",
                     default=8890,
                     help="Manager port to connect to [default 8890]")
    group.add_option('-T', '--transport',
                     action="store", type="string", dest="transport",
                     default="ssl",
                     help="Transport protocol to use (tcp/ssl)")

    group.add_option('-u', '--username',
                     action="store", type="string", dest="username",
                     default="",
                     help="Username to use")
    group.add_option('-d', '--password',
                     action="store", type="string", dest="password",
                     default="",
                     help="Password to use, - for interactive")
     
    parser.add_option_group(group)
    group = optparse.OptionGroup(parser, "Job options")
    group.add_option('-j', '--job',
                     action="store", type="string", dest="job",
                     help="Run job")
    group.add_option('-w', '--worker',
                     action="store", type="string", dest="worker",
                     help="Worker unix socket to connect to")
    parser.add_option_group(group)
    
    log.debug('manager', 'Parsing arguments (%r)' % ', '.join(args))
    options, args = parser.parse_args(args)

    if options.job:
        # we were started from the worker as a job
        _startJob(options)
    else:
        # we are the main worker
        _startWorker(options)

def _startJob(options):
    from flumotion.worker import job
    job_client_factory = job.JobClientFactory(options.job)
    reactor.connectUNIX(options.worker, job_client_factory)
    log.debug('job', 'Starting reactor')
    reactor.run()
    log.debug('job', 'Reactor stopped')

def _connectWorkerReactorTCP(options, brain):
    log.info('worker',
        'Connecting to manager %s:%d with TCP' % (options.host, options.port))
    reactor.connectTCP(options.host, options.port, brain.worker_client_factory)

def _connectWorkerReactorSSL(options, brain):
    from twisted.internet import ssl
    log.info('worker',
        'Connecting to manager %s:%d with SSL' % (options.host, options.port))
    reactor.connectSSL(options.host, options.port, brain.worker_client_factory,
        ssl.ClientContextFactory())

def _startWorker(options):
    # create a brain and have it remember the manager to direct jobs to
    brain = worker.WorkerBrain(options.host, options.port, options.transport)

    # connect the brain to the manager
    if options.transport == "tcp":
        _connectWorkerReactorTCP(options, brain)
    elif options.transport == "ssl":
        _connectWorkerReactorSSL(options, brain)
    else:
        log.error('worker', 'Unknown transport protocol: %s' % options.transport)

    # FIXME: allow for different credentials types
    credentials = cred.Username(options.username, options.password)
    brain.login(credentials)

    log.debug('worker', 'Starting reactor')
    reactor.run()

    log.debug('worker', 'Reactor stopped, shutting down jobs')
    # XXX: Is this really necessary
    brain.job_heaven.shutdown()

    pids = [kid.getPid() for kid in brain.kindergarten.getKids()]
    
    log.debug('worker', 'Waiting for jobs to finish')
    while pids:
        pid = os.wait()[0]
	# FIXME: properly catch OSError: [Errno 10] No child processes
        pids.remove(pid)

    log.debug('worker', 'All jobs finished, closing down')
