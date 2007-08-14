# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

__all__ = ['ComponentTestHelper', 'ComponentUnitTestMixin', 'pipeline_src',
           'pipeline_cnv']

import common

import os
import tempfile
import new
import sys

from twisted.internet import gtk2reactor
HAVE_GTK2REACTOR = True
try:
    gtk2reactor.install(useGtk=False)
except AssertionError:
    if not isinstance(sys.modules['twisted.internet.reactor'],
                      gtk2reactor.Gtk2Reactor):
        HAVE_GTK2REACTOR = False

from twisted.python import failure
from twisted.internet import reactor, defer, interfaces
from twisted.web import client, error

from flumotion.common import registry, log, errors, common
from flumotion.component.producers.pipeline.pipeline import Producer
from flumotion.component.converters.pipeline.pipeline import Converter
from flumotion.twisted import flavors


class ComponentTestException(Exception):
    pass

class WrongReactor(ComponentTestException):
    pass

class StartTimeout(ComponentTestException):
    pass

class FlowTimeout(ComponentTestException):
    pass

class StopTimeout(ComponentTestException):
    pass


def delayed_d(time, val):
    """Insert some delay into callback chain."""

    d = defer.Deferred()
    reactor.callLater(time, d.callback, val)
    return d

def override_value_callback(_result, value):
    """
    Ignore the result returned from the deferred callback chain and
    return the given value.
    """
    return value

def call_and_passthru_callback(result, callable_, *args, **kwargs):
    """Invoke the callable_ and passthrough the original result."""
    callable_(*args, **kwargs)
    return result


class ComponentWrapper(object, log.Loggable):
    logCategory = 'comptest-compwrap'
    _u_name_cnt = 0
    _registry = None

    def __init__(self, type_, class_, props=None, name=None, plugs=None,
                 cfg=None):
        self.comp = None
        self.comp_class = class_
        if cfg is None:
            cfg = {}
        self.cfg = cfg
        self.auto_link = True
        self.debug_msgs = []

        self.sync = None
        self.sync_master = None

        if ComponentWrapper._registry is None:
            ComponentWrapper._registry = registry.getRegistry()

        cfg['type'] = type_
        reg = ComponentWrapper._registry.getComponent(type_)

        if not cfg.has_key('source'):
            cfg['source'] = []

        if not cfg.has_key('eater'):
            cfg['eater'] = dict([(e.getName(), []) for e in reg.getEaters()
                                 if e.getRequired()])

        if not cfg.has_key('feed'):
            cfg['feed'] = reg.getFeeders()[:]

        if plugs is not None:
            cfg['plugs'] = plugs
        if not cfg.has_key('plugs'):
            cfg['plugs'] = dict([(s, []) for s in reg.getSockets()])

        if name:
            cfg['name'] = name
        if not cfg.has_key('name'):
            cfg['name'] = ComponentWrapper.get_unique_name()
        self.name = cfg['name']

        if not cfg.has_key('parent'):
            cfg['parent'] = 'default'

        if not cfg.has_key('avatarId'):
            cfg['avatarId'] = common.componentId(cfg['parent'], self.name)

        if props is not None:
            cfg['properties'] = props
        if not cfg.has_key('properties'):
            cfg['properties'] = {}

        if not cfg.has_key('clock-master'):
            cfg['clock-master'] = None

        self.sync_master = cfg['clock-master']

        if reg.getNeedsSynchronization():
            self.sync = reg.getClockPriority()

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__,
                               self.comp_class.__name__, self.cfg)

    def get_unique_name(cls, prefix='cmp-'):
        name, cls._u_name_cnt = ('%s%d' % (prefix, cls._u_name_cnt),
                                 cls._u_name_cnt + 1)
        return name
    get_unique_name = classmethod(get_unique_name)

    def instantiate(self):
        self.comp = self.comp_class()
        self.debug('instantiate:: %r' % self.comp.state)
        def append(instance, key, value):
            self.debug('append %r: %r' % (value.level, value))
            if key == 'messages':
                if value.debug:
                    self.debug('proxied state debug:: %r' % value.debug)
                    self.debug_msgs.append(value.debug)
            flavors.StateCacheable.append(instance, key, value)
        self.comp.state.append = new.instancemethod(append, self.comp.state)

    def setup(self):
        if self.comp is None:
            self.instantiate()
        return self.comp.setup(self.cfg)

    def feed(self, sink_comp, links=None):
        if links is None:
            links = [('default', 'default')]
        sink_name = sink_comp.name
        for feeder, eater in links:
            if feeder not in self.cfg['feed']:
                raise ComponentTestException('Invalid feeder specified: %r' %
                                             feeder)
            #self.cfg['feed'].append('%s:%s' % (sink_name, eater))
            sink_comp.add_feeder(self, '%s:%s' % (self.name, feeder), eater)
            #self.auto_link = False

    def add_feeder(self, src_comp, feeder_name, eater):
        self.cfg['source'].append(feeder_name)
        self.cfg['eater'].setdefault(eater, []).append(feeder_name)
        self.auto_link = False

    def feedToFD(self, feedName, fd, eaterId=None):
        self.debug('feedToFD(feedName=%s, %d (%s))' % (feedName, fd, eaterId))
        return self.comp.feedToFD(feedName, fd, os.close, eaterId)

    def eatFromFD(self, feedId, fd):
        self.debug('eatFromFD(feedId=%s, %d)' % (feedId, fd))
        return self.comp.eatFromFD(feedId, fd)

    def start(self, *args, **kwargs):
        self.debug('start(*%r, **%r)' % (args, kwargs))
        d = self.comp.start(*args, **kwargs)
        d.addCallback(lambda _: (self.debug('after start: %r' % _), _)[1])
        return d

    def stop(self, *args, **kwargs):
        self.debug('stop(*%r, **%r)' % (args, kwargs))
        if self.comp:
            return self.comp.stop(*args, **kwargs)
        return defer.succeed(None)


class ComponentTestHelper(object, log.Loggable):
    logCategory = 'comptest-helper'

    guard_timeout = 60.0
    guard_delay = 0.5
    start_delay = None

    def __init__(self):
        self._comps = []
        self._byname = {}
        self._master = None

    def set_flow(self, comp_chain, auto_link=True):
        if len(comp_chain) == 0:
            return

        self._comps = comp_chain

        if auto_link:
            for c_src, c_sink in zip(comp_chain[:-1], comp_chain[1:]):
                if c_sink.auto_link:
                    c_src.feed(c_sink)

        masters = [c for c in self._comps if c.sync_master is not None]
        need_sync = sorted([c for c in self._comps if c.sync is not None],
                           key=(lambda e: e.sync), reverse=True)

        if need_sync:
            if masters:
                master = masters[0]
            else:
                master = need_sync[0]

            master.sync = None # ...? :/
            self._master = master

            master = master.cfg['avatarId']
            for c in need_sync:
                c.cfg['clock-master'] = master
        elif masters:
            for c in masters:
                c.cfg['clock-master'] = None

        for c in self._comps:
            self._byname[c.name] = c
            c.log('updated config for %r: %r' % (c, c.cfg))

    def _make_pipes(self):
        fds = {}
        def feed_starter(c, feed_name, w_fd, feed_id):
            def _feed_starter():
                self.debug('_feed_starter: %r, %r' % (feed_name, feed_id))
                return c.feedToFD(feed_name, w_fd, eaterId=feed_id)
            return _feed_starter
        for c in self._comps:
            eaters = c.cfg['eater']
            for eater_id in eaters:
                for src in eaters[eater_id]:
                    e_name, e_feed = src.split(':')
                    self.debug('creating pipe: %r, %r, %r' %
                               (src, e_feed, eater_id))
                    r_fd, w_fd = os.pipe()
                    fds[src] = (r_fd, feed_starter(self._byname[e_name],
                                                   e_feed, w_fd, eater_id))
        self._fds = fds

    def start_flow(self):
        delay = self.start_delay

        def all_ready_p(results):
            self.debug('** 1: all_ready_p: %r' % results)
            pass

        def setup_failed(failure):
            self.info('*! 1: setup_failed: %r' % (failure,))
            failure.trap(defer.FirstError)
            return failure.value.subFailure

        def start_master_clock(_):
            self.debug('** 2: start_master_clock: %r (%r)' % (_, self._master))
            if self._master is not None:
                self.debug('About to ask to provide_master_clock()...')
                d = self._master.comp.provide_master_clock(7600 - 1) # ...hack?
                def _passthrough_debug(_res):
                    self.debug('After provide_master_clock() : %r' % (_res,))
                    return _res
                d.addCallback(_passthrough_debug)
                return d
            return None

        def add_delay(value):
            self.debug('** 3: add_delay: %r' % (value,))
            if delay:
                return delayed_d(delay, value)
            return defer.succeed(value)

        def do_start(clocking, c):
            self.debug('** 4: do_start_cb: %r, %r' % (clocking, c))
            for src in c.cfg['source']:
                r_fd, feed_starter = self._fds[src]
                c.eatFromFD(src, r_fd)
                feed_starter()
            comp_clocking = clocking
            if not c.sync:
                comp_clocking = None
            self.debug('*_ 4: do_start_cb: %r, %r' % (comp_clocking, c))
            d = c.start(comp_clocking)

            # if component starts ok, repeat/pass clocking info to a
            # subsequent component
            d.addCallback(override_value_callback, clocking)
            return d

        def do_stop(failure):
            self.debug('** X: do_stop: %r' % failure)
            rcomps = self._comps[:]
            rcomps.reverse()
            for c in rcomps:
                c.stop()
            return failure

        self._make_pipes()

        self.debug('About to start the flow...')
        # P(ossible)TODO: make it report setup failures in all the
        # components, not only in the first to fail...?
        d = defer.DeferredList([c.setup() for c in self._comps],
                               fireOnOneErrback=1, consumeErrors=1)
        d.addCallbacks(all_ready_p, setup_failed)
        d.addCallback(start_master_clock)
        for c in self._comps:
            d.addCallback(add_delay)
            d.addCallback(do_start, c)
        d.addErrback(do_stop)
        return d

    def stop_flow(self):
        rcomps = self._comps[:]
        rcomps.reverse()
        d = defer.DeferredList([c.stop() for c in rcomps],
                               fireOnOneErrback=1, consumeErrors=1)
        def stop_flow_report(results):
            self.debug('stop_flow_report: %r' % (results,))
            return results
        def stop_flow_failed(failure):
            self.info('stop_flow_failed: %r' % (failure,))
            failure.trap(defer.FirstError)
            self.info('stop_flow_failed! %r' % (failure.value.subFailure,))
            return failure.value.subFailure
        d.addCallbacks(stop_flow_report, stop_flow_failed)
        return d

    def run_flow(self, duration, tasks=None,
                 start_d=None, start_flow=True, stop_flow=True):
        if not HAVE_GTK2REACTOR:
            raise WrongReactor("gtk2reactor isn't available")

        self.debug('run_flow: tasks: %r' % (tasks,))
        flow_d = start_d

        if tasks is None:
            tasks = []

        if flow_d is None:
            if start_flow:
                flow_d = self.start_flow()
            else:
                flow_d = defer.succeed(True)

        flow_started_finished = [False, False]

        guard_d = None
        timeout_d = defer.Deferred()
        stop_d = defer.Deferred()
        stop_timeout_d = defer.Deferred()
        chained_d = None
        immediate_d = None

        callids = [None, None, None] # callLater ids: stop_d,
                                     # timeout_d, fire_chained

        if tasks:
            # if have tasks, run simultaneously with the main timer deferred
            chained_d = defer.DeferredList([stop_d] + tasks,
                                           fireOnOneErrback=1, consumeErrors=1)
            def chained_failed(failure):
                self.info('chained_failed: %r' % (failure,))
                failure.trap(defer.FirstError)
                return failure.value.subFailure
            chained_d.addErrback(chained_failed)
        else:
            # otherwise, just idle...
            chained_d = stop_d

        def start_complete(result):
            self.debug('start_complete: %r' % (result,))
            flow_started_finished[0] = True
            callids[0] = reactor.callLater(duration, stop_d.callback, None)
            if tasks:
                def _fire_chained():
                    callids[2] = None
                    for t in tasks:
                        try:
                            t.callback(result)
                        except defer.AlreadyCalledError:
                            pass
                callids[2] = reactor.callLater(0, _fire_chained)
            return chained_d

        def flow_complete(result):
            self.debug('flow_complete: %r' % (result,))
            flow_started_finished[1] = True
            return result

        def flow_timed_out():
            self.debug('flow_timed_out!')
            if not flow_started_finished[0]:
                timeout_d.errback(StartTimeout('flow start timed out'))
            elif not flow_started_finished[1]:
                timeout_d.errback(FlowTimeout('flow run timed out'))
            else:
                stop_timeout_d.errback(StopTimeout('flow stop timed out'))

        def clean_calls(result):
            self.debug('clean_calls: %r' % (result,))
            for i, cid in enumerate(callids):
                if cid is not None:
                    if cid.active():
                        cid.cancel()
                    callids[i] = None
            return result

        flow_d.addCallbacks(start_complete)
        flow_d.addCallback(flow_complete)

        guard_d = defer.DeferredList([flow_d, timeout_d], consumeErrors=1,
                                     fireOnOneErrback=1, fireOnOneCallback=1)

        def guard_failed(failure):
            self.info('guard_failed: %r' % (failure,))
            failure.trap(defer.FirstError)
            return failure.value.subFailure
        if stop_flow:
            def _force_stop_flow(result):
                self.debug('_force_stop_flow: %r' % (result,))
                d = defer.DeferredList([self.stop_flow(), stop_timeout_d],
                                       fireOnOneErrback=1, fireOnOneCallback=1,
                                       consumeErrors=1)
                def _return_orig_result(stop_result):
                    if isinstance(result, failure.Failure):
                        # always return the run's failure first
                        # what do I return if both the run and stop failed?
                        self.debug('_return_orig[R]: %r' % (result,))
                        return result
                    elif isinstance(stop_result, failure.Failure):
                        # return failure from stop
                        self.debug('_return_orig[S]: %r' % (stop_result,))
                        return stop_result
                    return result
                def force_stop_failed(failure):
                    self.info('force_stop_failed: %r' % (failure,))
                    failure.trap(defer.FirstError)
                    return failure.value.subFailure
                d.addCallbacks(lambda r: r[0], force_stop_failed)
                d.addBoth(_return_orig_result)
                return d
            guard_d.addBoth(_force_stop_flow)

        guard_d.addErrback(guard_failed)
        guard_d.addBoth(clean_calls)

        callids[1] = reactor.callLater(self.guard_timeout, flow_timed_out)
        return guard_d

class ComponentUnitTestMixin:
    if not HAVE_GTK2REACTOR:
        skip = 'gtk2reactor is required for this test case'

def cleanup_reactor(force=False):
    if not HAVE_GTK2REACTOR and not force:
        return
    log.debug('comptest', 'running cleanup_reactor...')
    delayed = reactor.getDelayedCalls()
    for dc in delayed:
        dc.cancel()
    # the rest is taken from twisted trial...
    sels = reactor.removeAll()
    if sels:
        log.info('comptest', 'leftover selectables...: %r %r' %
                 (sels, reactor.waker))
        for sel in sels:
            if interfaces.IProcessTransport.providedBy(sel):
                sel.signalProcess('KILL')

def pipeline_src(pipelinestr='fakesrc datarate=1024 is-live=true ! '
                 'video/x-raw-rgb,framerate=(fraction)8/1,width=32,height=24'):
    fs_name = ComponentWrapper.get_unique_name('ppln-src-')

    return ComponentWrapper('pipeline-producer', Producer, name=fs_name,
                            props={'pipeline': pipelinestr})

def pipeline_cnv(pipelinestr='identity'):
    fs_name = ComponentWrapper.get_unique_name('ppln-cnv-')

    return ComponentWrapper('pipeline-converter', Converter, name=fs_name,
                            props={'pipeline': pipelinestr})

