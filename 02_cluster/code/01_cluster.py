# -*- coding: utf-8 -*-

from collections import namedtuple
import copy
import functools
import heapq
import itertools
import logging
from queue import Queue
import random
import threading
import traceback
import sys

"""
基础: python 优先队列的使用方法
>>> import heapq
>>> pqueue = []
>>> heapq.heappush(pqueue, (1, 'A'))
>>> heapq.heappush(pqueue, (7, 'B'))
>>> heapq.heappush(pqueue, (3, 'C'))
>>> heapq.heappush(pqueue, (6, 'D'))
>>> heapq.heappush(pqueue, (2, 'E'))
>>> heapq.heappush(pqueue, (3, 'F'))
>>>
>>> pqueue[0]
(1, 'A')
>>> pqueue[0]
(1, 'A')
>>> pqueue[1]
(2, 'E')
>>> pqueue[2]
(3, 'C')
>>> pqueue[3]
(7, 'B')
>>> pqueue[4]
(6, 'D')
>>> pqueue[0]
(1, 'A')
>>>
>>> heapq.heappop(pqueue)
(1, 'A')
>>> heapq.heappop(pqueue)
(2, 'E')
>>> heapq.heappop(pqueue)
(3, 'C')
>>> heapq.heappop(pqueue)
(3, 'F')
>>> heapq.heappop(pqueue)
(6, 'D')
>>> heapq.heappop(pqueue)
(7, 'B')
>>> heapq.heappop(pqueue)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
IndexError: index out of range

>>> import random
>>> rnd = random.Random(10)
>>> rnd.uniform(0, 1.0)
0.5714025946899135
>>> rnd.uniform(0, 1.0)
0.4288890546751146
>>> rnd.uniform(0, 1.0)
0.5780913011344704
>>> rnd.uniform(0, 1.0)
0.20609823213950174
>>> rnd.uniform(0, 1.0)
0.81332125135732
>>>
>>> rnd.uniform(-0.02, 0.02)
0.012943554901337816
>>> rnd.uniform(-0.02, 0.02)
0.006138901356047031
>>> rnd.uniform(-0.02, 0.02)
-0.013590817739247214
>>> rnd.uniform(-0.02, 0.02)
0.0008267743855969838
>>> rnd.uniform(-0.02, 0.02)
-0.0068890875351162745
>>>
"""

# data types
"""
Proposal(caller='N2', client_id=100000, input=('get', 'b'))
"""
Proposal = namedtuple('Proposal', ['caller', 'client_id', 'input'])  # 提案
Ballot = namedtuple('Ballot', ['n', 'leader'])  # 选票

# message types
Accepted = namedtuple('Accepted', ['slot', 'ballot_num'])
Accept = namedtuple('Accept', ['slot', 'ballot_num', 'proposal'])
Decision = namedtuple('Decision', ['slot', 'proposal'])  # 决断
Invoked = namedtuple('Invoked', ['client_id', 'output'])  # 调用

"""
Invoke(caller=self.node.address, client_id=self.client_id, input_value=self.n)
Invoke(caller='N2', client_id=100000, input_value=('get', 'b'))
"""
Invoke = namedtuple('Invoke', ['caller', 'client_id', 'input_value'])

"""
Join()
"""
Join = namedtuple('Join', [])
Active = namedtuple('Active', [])  # 存活

"""
Prepare(ballot_num=Ballot(n=0, leader='N2')) to ['N0', 'N1', 'N2']
"""
Prepare = namedtuple('Prepare', ['ballot_num'])  # 准备
Promise = namedtuple('Promise', ['ballot_num', 'accepted_proposals'])  # 诺言

"""
Propose(slot=1, proposal=Proposal(caller='N2', client_id=100000, input=('get', 'b')))
"""
Propose = namedtuple('Propose', ['slot', 'proposal'])  # 提出提案

"""
Welcome(state=self.initial_state, slot=1, decisions={})
"""
Welcome = namedtuple('Welcome', ['state', 'slot', 'decisions'])

Decided = namedtuple('Decided', ['slot'])  # 决定
Preempted = namedtuple('Preempted', ['slot', 'preempted_by'])  # 抢占
Adopted = namedtuple('Adopted', ['ballot_num', 'accepted_proposals'])  # 通过
Accepting = namedtuple('Accepting', ['leader'])

# constants - these times should really be in terms of average round-trip time
JOIN_RETRANSMIT = 0.7
CATCHUP_INTERVAL = 0.6
ACCEPT_RETRANSMIT = 1.0
PREPARE_RETRANSMIT = 1.0
INVOKE_RETRANSMIT = 0.5
LEADER_TIMEOUT = 1.0
NULL_BALLOT = Ballot(-1, -1)  # sorts before all real ballots
NOOP_PROPOSAL = Proposal(None, None, None)  # no-op to fill otherwise empty slots


class Node(object):
    unique_ids = itertools.count()

    def __init__(self, network, address):
        self.network = network
        self.address = address or next(self.__class__.unique_ids)
        self.logger = SimTimeLogger(logging.getLogger(self.address), {'network': self.network})
        self.logger.info('starting')
        self.roles = []
        self.send = functools.partial(self.network.send, self)

    def __str__(self):
        return 'Node address: %s, roles: %s' % (self.address, self.roles)

    def register(self, roles):
        self.roles.append(roles)

    def unregister(self, roles):
        self.roles.remove(roles)

    def receive(self, sender, message):
        print(self)  # node address: N0, roles: [<cluster.Seed object at 0x100f3bb90>]
        print(sender)  # N4
        handler_name = 'do_%s' % type(message).__name__
        print(handler_name)  # do_Join

        for comp in self.roles[:]:
            if not hasattr(comp, handler_name):
                continue
            comp.logger.debug("received %s from %s", message, sender)
            fn = getattr(comp, handler_name)
            fn(sender=sender, **message._asdict())


class Timer(object):

    def __init__(self, expires, address, callback):
        self.expires = expires
        self.address = address  # address 消息接收者 N0
        self.callback = callback  # callback(sender.address, message) 消息发送者 N1
        self.cancelled = False

    def __repr__(self):
        return '(expires: %s, address: %s)' % (self.expires, self.address)

    def __cmp__(self, other):
        return cmp(self.expires, other.expires)

    def cancel(self):
        self.cancelled = True


class Network(object):
    PROP_DELAY = 0.03
    PROP_JITTER = 0.02
    DROP_PROB = 0.05

    def __init__(self, seed):
        """
        {
            'N0': address: N0, roles: [<cluster.Seed object at 0x1066e6b50>],
            'N1': address: N1, roles: [<cluster.Bootstrap object at 0x1066e6d10>],
            'N2': address: N2, roles: [<cluster.Bootstrap object at 0x1066e6fd0>],
            'N3': address: N3, roles: [<cluster.Bootstrap object at 0x10675b2d0>],
            'N4': address: N4, roles: [<cluster.Bootstrap object at 0x10675b590>],
            'N5': address: N5, roles: [<cluster.Bootstrap object at 0x10675b850>],
            'N6': address: N6, roles: [<cluster.Bootstrap object at 0x10675bb10>]
        }
        """
        self.nodes = {}
        self.rnd = random.Random(seed)
        self.timers = []
        self.now = 1000.0

    def __repr__(self):
        return 'Network nodes: %s, timers: %s' % (self.nodes, self.timers)

    def new_node(self, address=None):
        node = Node(self, address=address)
        self.nodes[node.address] = node
        return node

    def run(self):
        i = 0
        while self.timers:
            i += 1
            if i >= 40:
                break
            next_timer = self.timers[0]
            print('************** network run %s**************' % (self.timers))
            print(next_timer)
            if next_timer.expires > self.now:
                self.now = next_timer.expires
            heapq.heappop(self.timers)
            if next_timer.cancelled:
                continue
            if not next_timer.address or next_timer.address in self.nodes:
                print('执行回调')
                print(next_timer.callback)
                r = next_timer.callback()
                print(r)

    def stop(self):
        self.timers = []

    # set_timer(None, 1.0, request)
    def set_timer(self, address, seconds, callback):
        """
        address 消息接收者 N0
        callback(sender.address, message) 消息发送者 N1
        """
        # print('*' * 10)
        # print(address)
        # print(seconds)
        # print(callback)
        # print('*' * 10)
        timer = Timer(self.now + seconds, address, callback)
        heapq.heappush(self.timers, timer)
        return timer

    def send(self, sender, destinations, message):
        """
        sender 消息发送者 N1
        destinations 消息接收者 ['N0']
        """
        # Bootstrap -> Role -> Node -> Network
        # (['N0'], Join())          -> (N1, ['N0'], Join())
        sender.logger.debug("sending %s to %s", message, destinations)

        # print(self)  # <cluster.Network object at 0x10cb02b10>
        # print(sender)  # address: N1, roles: [<cluster.Bootstrap object at 0x10cb02e10>]
        # print(destinations)  # ['N0']
        # print(message)  # Join()
        # print()  # Join()

        # avoid aliasing by making a closure containing distinct deep copy of message for each dest
        def sendto(dest, message):
            print(dest)  # N0
            print(message)  # Join()
            if dest == sender.address:
                print('发送地址和接收地址一样')
                # reliably deliver local messages with no delay
                self.set_timer(sender.address, 0, lambda: sender.receive(sender.address, message))
            elif self.rnd.uniform(0, 1.0) > self.DROP_PROB:
                delay = self.PROP_DELAY + self.rnd.uniform(-self.PROP_JITTER, self.PROP_JITTER)
                self.set_timer(dest, delay, functools.partial(self.nodes[dest].receive,
                                                              sender.address, message))
        for dest in (d for d in destinations if d in self.nodes):
            sendto(dest, copy.deepcopy(message))


class SimTimeLogger(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        return "T=%.3f %s" % (self.extra['network'].now, msg), kwargs

    def getChild(self, name):
        return self.__class__(self.logger.getChild(name),
                              {'network': self.extra['network']})


class Role(object):

    def __init__(self, node):
        self.node = node
        self.node.register(self)
        self.running = True
        self.logger = node.logger.getChild(type(self).__name__)

    def set_timer(self, seconds, callback):
        # self.set_timer(JOIN_RETRANSMIT, self.join)
        # self.node.address 消息的发送者
        return self.node.network.set_timer(self.node.address, seconds, lambda: self.running and callback())

    def stop(self):
        self.running = False
        self.node.unregister(self)


class Acceptor(Role):
    """
    The Acceptor implements the acceptor role in the protocol,
    so it must store the ballot number representing its most recent promise,
    along with the set of accepted proposals for each slot.
    """

    def __init__(self, node):
        super(Acceptor, self).__init__(node)
        self.ballot_num = NULL_BALLOT  # NULL_BALLOT = Ballot(-1, -1) namedtuple('Ballot', ['n', 'leader']) 选票
        self.accepted_proposals = {}  # {slot: (ballot_num, proposal)}

    def do_Prepare(self, sender, ballot_num):
        if ballot_num > self.ballot_num:
            self.ballot_num = ballot_num
            # we've heard from a scout, so it might be the next leader
            self.node.send([self.node.address], Accepting(leader=sender))

        self.node.send([sender], Promise(ballot_num=self.ballot_num, accepted_proposals=self.accepted_proposals))

    def do_Accept(self, sender, ballot_num, slot, proposal):
        if ballot_num >= self.ballot_num:
            self.ballot_num = ballot_num
            acc = self.accepted_proposals
            if slot not in acc or acc[slot][0] < ballot_num:
                acc[slot] = (ballot_num, proposal)

        self.node.send([sender], Accepted(
            slot=slot, ballot_num=self.ballot_num))


class Replica(Role):

    def __init__(self, node, execute_fn, state, slot, decisions, peers):
        super(Replica, self).__init__(node)
        self.execute_fn = execute_fn
        self.state = state
        self.slot = slot
        self.decisions = decisions
        self.peers = peers
        self.proposals = {}
        # next slot num for a proposal (may lead slot)
        self.next_slot = slot
        self.latest_leader = None
        self.latest_leader_timeout = None

    def __str__(self):
        return 'Replica state: %s, slot: %s, decisions: %s, proposals: %s, next_slot: %s, latest_leader: %s, latest_leader_timeout: %s, running: %s' % (self.state, self.slot, self.decisions, self.proposals, self.next_slot, self.latest_leader, self.latest_leader_timeout, self.running)

    # making proposals

    def do_Invoke(self, sender, caller, client_id, input_value):
        proposal = Proposal(caller, client_id, input_value)
        slot = next((s for s, p in self.proposals.items() if p == proposal), None)
        print(slot)
        # propose, or re-propose if this proposal already has a slot
        self.propose(proposal, slot)

    def propose(self, proposal, slot=None):
        """Send (or resend, if slot is specified) a proposal to the leader"""
        if not slot:
            slot, self.next_slot = self.next_slot, self.next_slot + 1
        self.proposals[slot] = proposal
        # print(self.proposals)
        """
        {
            1: Proposal(caller='N2', client_id=100000, input=('get', 'b')),
            2: Proposal(caller='N2', client_id=100001, input=('get', 'a'))
        }
        """

        # find a leader we think is working - either the latest we know of, or
        # ourselves (which may trigger a scout to make us the leader)
        leader = self.latest_leader or self.node.address
        self.logger.info("proposing %s at slot %d to leader %s" % (proposal, slot, leader))
        self.node.send([leader], Propose(slot=slot, proposal=proposal))

    # handling decided proposals

    def do_Decision(self, sender, slot, proposal):
        assert not self.decisions.get(self.slot, None), \
                "next slot to commit is already decided"
        if slot in self.decisions:
            assert self.decisions[slot] == proposal, \
                "slot %d already decided with %r!" % (slot, self.decisions[slot])
            return
        self.decisions[slot] = proposal
        self.next_slot = max(self.next_slot, slot + 1)

        # re-propose our proposal in a new slot if it lost its slot and wasn't a no-op
        our_proposal = self.proposals.get(slot)
        if our_proposal is not None and our_proposal != proposal and our_proposal.caller:
            self.propose(our_proposal)

        # execute any pending, decided proposals
        while True:
            commit_proposal = self.decisions.get(self.slot)
            if not commit_proposal:
                break  # not decided yet
            commit_slot, self.slot = self.slot, self.slot + 1

            self.commit(commit_slot, commit_proposal)

    def commit(self, slot, proposal):
        """Actually commit a proposal that is decided and in sequence"""
        decided_proposals = [p for s, p in self.decisions.iteritems() if s < slot]
        if proposal in decided_proposals:
            self.logger.info("not committing duplicate proposal %r at slot %d", proposal, slot)
            return  # duplicate

        self.logger.info("committing %r at slot %d" % (proposal, slot))
        if proposal.caller is not None:
            # perform a client operation
            self.state, output = self.execute_fn(self.state, proposal.input)
            self.node.send([proposal.caller], Invoked(client_id=proposal.client_id, output=output))

    # tracking the leader

    def do_Adopted(self, sender, ballot_num, accepted_proposals):
        self.latest_leader = self.node.address
        self.leader_alive()

    def do_Accepting(self, sender, leader):
        self.latest_leader = leader
        self.leader_alive()

    def do_Active(self, sender):
        if sender != self.latest_leader:
            return
        self.leader_alive()

    def leader_alive(self):
        if self.latest_leader_timeout:
            self.latest_leader_timeout.cancel()

        def reset_leader():
            idx = self.peers.index(self.latest_leader)
            self.latest_leader = self.peers[(idx + 1) % len(self.peers)]
            self.logger.debug("leader timed out; tring the next one, %s", self.latest_leader)
        self.latest_leader_timeout = self.set_timer(LEADER_TIMEOUT, reset_leader)

    # adding new cluster members

    def do_Join(self, sender):
        if sender in self.peers:
            self.node.send([sender], Welcome(
                state=self.state, slot=self.slot, decisions=self.decisions))


class Commander(Role):

    def __init__(self, node, ballot_num, slot, proposal, peers):
        super(Commander, self).__init__(node)
        self.ballot_num = ballot_num
        self.slot = slot
        self.proposal = proposal
        self.acceptors = set([])
        self.peers = peers
        self.quorum = len(peers) / 2 + 1

    def start(self):
        self.node.send(set(self.peers) - self.acceptors, Accept(
                            slot=self.slot, ballot_num=self.ballot_num, proposal=self.proposal))
        self.set_timer(ACCEPT_RETRANSMIT, self.start)

    def finished(self, ballot_num, preempted):
        if preempted:
            self.node.send([self.node.address], Preempted(slot=self.slot, preempted_by=ballot_num))
        else:
            self.node.send([self.node.address], Decided(slot=self.slot))
        self.stop()

    def do_Accepted(self, sender, slot, ballot_num):
        if slot != self.slot:
            return
        if ballot_num == self.ballot_num:
            self.acceptors.add(sender)
            if len(self.acceptors) < self.quorum:
                return
            self.node.send(self.peers, Decision(slot=self.slot, proposal=self.proposal))
            self.finished(ballot_num, False)
        else:
            self.finished(ballot_num, True)


class Scout(Role):

    def __init__(self, node, ballot_num, peers):
        super(Scout, self).__init__(node)
        self.ballot_num = ballot_num
        self.accepted_proposals = {}
        self.acceptors = set([])
        self.peers = peers
        self.quorum = len(peers) / 2 + 1
        self.retransmit_timer = None

    def start(self):
        self.logger.info("scout starting")
        self.send_prepare()

    def send_prepare(self):
        self.node.send(self.peers, Prepare(ballot_num=self.ballot_num))
        self.retransmit_timer = self.set_timer(PREPARE_RETRANSMIT, self.send_prepare)

    def update_accepted(self, accepted_proposals):
        acc = self.accepted_proposals
        for slot, (ballot_num, proposal) in accepted_proposals.iteritems():
            if slot not in acc or acc[slot][0] < ballot_num:
                acc[slot] = (ballot_num, proposal)

    def do_Promise(self, sender, ballot_num, accepted_proposals):
        if ballot_num == self.ballot_num:
            self.logger.info("got matching promise; need %d" % self.quorum)
            self.update_accepted(accepted_proposals)
            self.acceptors.add(sender)
            if len(self.acceptors) >= self.quorum:
                # strip the ballot numbers from self.accepted_proposals, now that it
                # represents a majority
                accepted_proposals = dict((s, p) for s, (b, p) in self.accepted_proposals.items())
                # We're adopted; note that this does *not* mean that no other leader is active.
                # Any such conflicts will be handled by the commanders.
                self.node.send([self.node.address],
                               Adopted(ballot_num=ballot_num, accepted_proposals=accepted_proposals))
                self.stop()
        else:
            # this acceptor has promised another leader a higher ballot number, so we've lost
            self.node.send([self.node.address], Preempted(slot=None, preempted_by=ballot_num))
            self.stop()


class Leader(Role):

    def __init__(self, node, peers, commander_cls=Commander, scout_cls=Scout):
        super(Leader, self).__init__(node)
        self.ballot_num = Ballot(0, node.address)
        self.active = False
        self.proposals = {}
        self.commander_cls = commander_cls
        self.scout_cls = scout_cls
        self.scouting = False
        self.peers = peers

    def __str__(self):
        return 'Leader ballot_num: %s, active: %s, scouting: %s, running: %s' % (self.ballot_num, self.active, self.scouting, self.running)

    def start(self):
        # reminder others we're active before LEADER_TIMEOUT expires
        def active():
            if self.active:
                print('qwe')
                self.node.send(self.peers, Active())
            print('asd')
            self.set_timer(LEADER_TIMEOUT / 2.0, active)
            print(self.node.network.timers)
        active()

    def spawn_scout(self):
        assert not self.scouting
        self.scouting = True
        self.scout_cls(self.node, self.ballot_num, self.peers).start()
        print(self.node.roles)

    def do_Adopted(self, sender, ballot_num, accepted_proposals):
        self.scouting = False
        self.proposals.update(accepted_proposals)
        # note that we don't re-spawn commanders here; if there are undecided
        # proposals, the replicas will re-propose
        self.logger.info("leader becoming active")
        self.active = True

    def spawn_commander(self, ballot_num, slot):
        proposal = self.proposals[slot]
        self.commander_cls(self.node, ballot_num, slot, proposal, self.peers).start()

    def do_Preempted(self, sender, slot, preempted_by):
        if not slot:  # from the scout
            self.scouting = False
        self.logger.info("leader preempted by %s", preempted_by.leader)
        self.active = False
        self.ballot_num = Ballot((preempted_by or self.ballot_num).n + 1, self.ballot_num.leader)

    def do_Propose(self, sender, slot, proposal):
        if slot not in self.proposals:
            if self.active:
                self.proposals[slot] = proposal
                self.logger.info("spawning commander for slot %d" % (slot,))
                self.spawn_commander(self.ballot_num, slot)
            else:
                if not self.scouting:
                    self.logger.info("got PROPOSE when not active - scouting")
                    self.spawn_scout()
                else:
                    self.logger.info("got PROPOSE while scouting; ignored")
        else:
            self.logger.info("got PROPOSE for a slot already being proposed")


class Bootstrap(Role):

    def __init__(self, node, peers, execute_fn,
                 replica_cls=Replica, acceptor_cls=Acceptor, leader_cls=Leader,
                 commander_cls=Commander, scout_cls=Scout):
        super(Bootstrap, self).__init__(node)  # address: N1, roles: [<cluster.Bootstrap object at 0x1056edcd0>]
        self.execute_fn = execute_fn  # <function key_value_state_machine at 0x1055da668>
        self.peers = peers  # ['N0', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6']
        self.peers_cycle = itertools.cycle(peers)  # <itertools.cycle object at 0x105710320>
        self.replica_cls = replica_cls  # <class 'cluster.Replica'>
        self.acceptor_cls = acceptor_cls  # <class 'cluster.Acceptor'>
        self.leader_cls = leader_cls  # <class 'cluster.Leader'>
        self.commander_cls = commander_cls  # <class 'cluster.Commander'>
        self.scout_cls = scout_cls  # <class 'cluster.Scout'>

    def __str__(self):
        return 'Bootstrap running: %s' % self.running

    def start(self):
        self.join()

    def join(self):
        # print([next(self.peers_cycle)])  # ['N0']
        # print(Join())  # Join()
        self.node.send([next(self.peers_cycle)], Join())
        self.set_timer(JOIN_RETRANSMIT, self.join)
        print(self.node.network.timers)
        print(self.node.roles)

    def do_Welcome(self, sender, state, slot, decisions):
        self.acceptor_cls(self.node)

        replica = self.replica_cls(self.node, execute_fn=self.execute_fn, peers=self.peers,
                         state=state, slot=slot, decisions=decisions)
        print(replica)

        leader = self.leader_cls(self.node, peers=self.peers, commander_cls=self.commander_cls,
                        scout_cls=self.scout_cls)
        print(leader)
        leader.start()

        print(self.node.roles)

        self.stop()
        print(self)
        print(self.node.roles)


class Seed(Role):

    """
    Seed(node, initial_state={}, peers=peers, execute_fn=key_value_state_machine)
    """
    def __init__(self, node, initial_state, execute_fn, peers, bootstrap_cls=Bootstrap):
        super(Seed, self).__init__(node)  # address: N0, roles: [<cluster.Seed object at 0x109c88b10>]
        self.initial_state = initial_state  # {}
        self.execute_fn = execute_fn  # <function key_value_state_machine at 0x109b74668>
        self.peers = peers  # ['N0', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6']
        self.bootstrap_cls = bootstrap_cls  # <class 'cluster.Bootstrap'>
        self.seen_peers = set([])  # set([])
        self.exit_timer = None  # None

    def __str__(self):
        return 'Seed initial_state: %s, seen_peers: %s, exit_timer: %s' % (self.initial_state, self.seen_peers, self.exit_timer)

    def do_Join(self, sender):
        self.seen_peers.add(sender)  # N4
        print(self)
        if len(self.seen_peers) <= len(self.peers) / 2:
            return

        # cluster is ready - welcome everyone
        self.node.send(list(self.seen_peers), Welcome(
            state=self.initial_state, slot=1, decisions={}))
        print(self.node.network.timers)

        # stick around for long enough that we don't hear any new JOINs from
        # the newly formed cluster
        if self.exit_timer:
            self.exit_timer.cancel()
        self.exit_timer = self.set_timer(JOIN_RETRANSMIT * 2, self.finish)
        print(self)
        print(self.node.network.timers)

    def finish(self):
        # bootstrap this node into the cluster we just seeded
        bs = self.bootstrap_cls(self.node, peers=self.peers, execute_fn=self.execute_fn)
        print(self.node.roles)
        bs.start()
        self.stop()


class Requester(Role):

    client_ids = itertools.count(start=100000)

    def __init__(self, node, n, callback):
        """
        Requester(node, input, req_done).start()
        """
        super(Requester, self).__init__(node)
        self.client_id = next(self.__class__.client_ids)
        self.n = n
        self.output = None
        self.callback = callback

    def start(self):
        self.node.send([self.node.address], Invoke(caller=self.node.address,
                                                   client_id=self.client_id, input_value=self.n))
        self.invoke_timer = self.set_timer(INVOKE_RETRANSMIT, self.start)

    def do_Invoked(self, sender, client_id, output):
        if client_id != self.client_id:
            return
        self.logger.debug("received output %r" % (output,))
        self.invoke_timer.cancel()
        self.callback(output)
        self.stop()


class Member(object):

    def __init__(self, state_machine, network, peers, seed=None,
                 seed_cls=Seed, bootstrap_cls=Bootstrap):
        """
        state_machine: 状态机操作方法 function
        network
        peers: 节点列表 []
        seed: 种子状态 {}
        seed_cls=Seed 用于构建新的系统
        bootstrap_cls=Bootstrap 用于将一个节点加入已有系统
        """
        self.network = network
        self.node = network.new_node()
        if seed is not None:
            self.startup_role = seed_cls(self.node, initial_state=seed, peers=peers, execute_fn=state_machine)
        else:
            self.startup_role = bootstrap_cls(self.node, execute_fn=state_machine, peers=peers)
        self.requester = None

    def start(self):
        self.startup_role.start()
        self.thread = threading.Thread(target=self.network.run)
        self.thread.start()

    def invoke(self, input_value, request_cls=Requester):
        assert self.requester is None
        q = Queue()
        self.requester = request_cls(self.node, input_value, q.put)
        self.requester.start()
        output = q.get()
        self.requester = None
        return output
