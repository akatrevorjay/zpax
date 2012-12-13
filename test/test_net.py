import os
import os.path
import sys

from twisted.internet import reactor, defer
from twisted.trial import unittest


pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )


from zpax import net

import testhelper


def delay(t):
    d = defer.Deferred()
    reactor.callLater(t, lambda : d.callback(None) )
    return d

    
all_nodes = 'A B C'.split()


class NetworkNodeTesterBase(object):

    NodeKlass  = None
    need_delay = False

    def setUp(self):
        self._pre_setup()
        
        self.nodes = dict()
        
        for node_uid in all_nodes:
            self.nodes[ node_uid ] = self.NodeKlass( node_uid )

        return self._setup()

    
    def tearDown(self):
        for n in self.nodes.itervalues():
            n.shutdown()

        return self._teardown()


    def _pre_setup(self):
        pass
    
    def _setup(self):
        pass

    def _teardown(self):
        pass


    def delay(self, t):
        if self.need_delay:
            return delay(t)
        else:
            return defer.succeed(None)

        
    def connect(self, recv_self=True):
        zpax_nodes = dict()
        
        for node_uid in all_nodes:
            zpax_nodes[ node_uid ] = ('ipc:///tmp/ts_{}_rtr'.format(node_uid),
                                      'ipc:///tmp/ts_{}_pub'.format(node_uid))
            
        for n in self.nodes.itervalues():
            n.connect( zpax_nodes, recv_self )

            
    @defer.inlineCallbacks
    def test_unicast_connections(self):
        self.connect()
        
        yield self.delay(1) # wait for connections to establish

        msgs = dict()
        
        def gend( nid ):
            def md( from_uid, msg_type, parts ):
                msgs[ nid ].append( (from_uid, msg_type, parts) )
            return md

        for n in all_nodes:
            msgs[ n ] = list()
            self.nodes[n].dispatch_message = gend(n)
            
        def s(src, dst, msg):
            self.nodes[src].unicast_message(dst, 'foomsg', msg)

        s('A', 'B', 'AB')
        s('A', 'C', 'AC')
        s('B', 'A', 'BA')
        s('B', 'C', 'BC')
        s('C', 'A', 'AC')
        s('C', 'B', 'CB')

        yield self.delay(0.05) # process messages

        for l in msgs.itervalues():
            l.sort()

        expected = {'A': [('B', 'foomsg', ['BA']), ('C', 'foomsg', ['AC'])],
                    'B': [('A', 'foomsg', ['AB']), ('C', 'foomsg', ['CB'])],
                    'C': [('A', 'foomsg', ['AC']), ('B', 'foomsg', ['BC'])]}

        self.assertEquals( msgs, expected )

        
    @defer.inlineCallbacks
    def test_broadcast_connections_no_recv_self(self):
        self.connect(False)
        
        yield self.delay(1) # wait for connections to establish

        msgs = dict()
        
        def gend( nid ):
            def md( from_uid, msg_type, parts ):
                msgs[ nid ].append( (from_uid, msg_type, parts) )
            return md

        for n in all_nodes:
            msgs[ n ] = list()
            self.nodes[n].dispatch_message = gend(n)
            
        def s(src, msg):
            self.nodes[src].broadcast_message('foomsg', msg)

        s('A', 'msgA')
        s('B', 'msgB')
        s('C', 'msgC')

        yield self.delay(0.05) # process messages

        for l in msgs.itervalues():
            l.sort()

        expected = {'A': [('B', 'foomsg', ['msgB']), ('C', 'foomsg', ['msgC'])],
                    'B': [('A', 'foomsg', ['msgA']), ('C', 'foomsg', ['msgC'])],
                    'C': [('A', 'foomsg', ['msgA']), ('B', 'foomsg', ['msgB'])]}

        self.assertEquals( msgs, expected )

        
    @defer.inlineCallbacks
    def test_broadcast_connections_recv_self(self):
        self.connect()
        
        yield self.delay(1) # wait for connections to establish

        msgs = dict()
        
        def gend( nid ):
            def md( from_uid, msg_type, parts ):
                msgs[ nid ].append( (from_uid, msg_type, parts) )
            return md

        for n in all_nodes:
            msgs[ n ] = list()
            self.nodes[n].dispatch_message = gend(n)
            
        def s(src, msg):
            self.nodes[src].broadcast_message('foomsg', msg)

        s('A', 'msgA')
        s('B', 'msgB')
        s('C', 'msgC')

        yield self.delay(0.05) # process messages

        for l in msgs.itervalues():
            l.sort()

        expected = {'A': [('A', 'foomsg', ['msgA']), ('B', 'foomsg', ['msgB']), ('C', 'foomsg', ['msgC'])],
                    'B': [('A', 'foomsg', ['msgA']), ('B', 'foomsg', ['msgB']), ('C', 'foomsg', ['msgC'])],
                    'C': [('A', 'foomsg', ['msgA']), ('B', 'foomsg', ['msgB']), ('C', 'foomsg', ['msgC'])]}


        self.assertEquals( msgs, expected )



class ZeroMQNetworkNodeTester(NetworkNodeTesterBase, unittest.TestCase):

    NodeKlass  = net.NetworkNode
    need_delay = True

    def _teardown(self):
        # In ZeroMQ 2.1.11 there is a race condition for socket deletion
        # and recreation that can render sockets unusable. We insert
        # a short delay here to prevent the condition from occuring.
        return delay(0.05)
    
    

class TestHelperNetworkNodeTester(NetworkNodeTesterBase, unittest.TestCase):
#class Foo:
    NodeKlass      = testhelper.NetworkNode

    def _pre_setup(self):
        testhelper.setup()
