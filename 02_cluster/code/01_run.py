# -*- coding: utf-8 -*-

from cluster import *
import sys

def key_value_state_machine(state, input_value):
    if input_value[0] == 'get':
        return state, state.get(input_value[1], None)
    elif input_value[0] == 'set':
        state[input_value[1]] = input_value[2]
        return state, input_value[2]

sequences_running = 0
def do_sequence(network, node, key):
    # print(node)  # address: N6, roles: [<cluster.Bootstrap object at 0x10c08acd0>]
    global sequences_running
    sequences_running += 1
    reqs = [
        (('get', key), None),
        (('set', key, 10), 10),
        (('get', key), 10),
        (('set', key, 20), 20),
        (('set', key, 30), 30),
        (('get', key), 30),
    ]
    def request():
        if not reqs:
            global sequences_running
            sequences_running -= 1
            if not sequences_running:
                network.stop()
            return
        input, exp_output = reqs.pop(0)
        def req_done(output):
            print('qwe')
            if output == exp_output:
                sys.exit()
            assert output == exp_output, "%r != %r" % (output, exp_output)
            request()
        Requester(node, input, req_done).start()

    network.set_timer(None, 1.0, request)


def main():
    logging.basicConfig(
        # format="%(name)s - %(message)s", level=logging.DEBUG, filename='log.log')
        format="%(name)s - %(message)s", level=logging.DEBUG)

    network = Network(int(sys.argv[1]))  # int(sys.argv[1]) = 10
    print(network)

    peers = ['N%d' % i for i in range(3)]  # ['N0', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6']
    for p in peers:
        node = network.new_node(address=p)
        if p == 'N0':
            seed = Seed(node, initial_state={}, peers=peers, execute_fn=key_value_state_machine)
            print(seed)
        else:
            Bootstrap(node, execute_fn=key_value_state_machine, peers=peers).start()
        print(node)
    print(network)

    # for key in 'ab':
    #     do_sequence(network, node, key)

    # def req_done(output):
    #     return output

    # input = ('set', 'a', 10)
    # Requester(node, input, req_done).start()


    # print(network.timers)
    network.run()

if __name__ == "__main__":
    main()


"""
Network nodes: {}, timers: []

N0 - T=1000.000 starting
Seed initial_state: {}, seen_peers: set([]), exit_timer: None
Node address: N0, roles: [<cluster.Seed object at 0x10c70bc90>]

N1 - T=1000.000 starting
N1 - T=1000.000 sending Join() to ['N0']
Node address: N1, roles: [<cluster.Bootstrap object at 0x10c70be50>]

N2 - T=1000.000 starting
N2 - T=1000.000 sending Join() to ['N0']
Node address: N2, roles: [<cluster.Bootstrap object at 0x10c70e150>]

Network
nodes: {
    'N0': <cluster.Node object at 0x10c70bbd0>,
    'N1': <cluster.Node object at 0x10c70bd90>,
    'N2': <cluster.Node object at 0x10c70bfd0>
    },
timers: [
    (expires: 1000.01824393, address: N0),
    (expires: 1000.7, address: N1),
    (expires: 1000.02715556, address: N0),
    (expires: 1000.7, address: N2)
    ]

##################################################################################################



Network nodes: {}, timers: []
N0 - T=1000.000 starting
Seed initial_state: {}, seen_peers: set([]), exit_timer: None
Node address: N0, roles: [<cluster.Seed object at 0x104758dd0>]
N1 - T=1000.000 starting
N1 - T=1000.000 sending Join() to ['N0']
N0
Join()
[(expires: 1000.02715556, address: N0), (expires: 1000.7, address: N1)]
[<cluster.Bootstrap object at 0x104758f90>]
Node address: N1, roles: [<cluster.Bootstrap object at 0x104758f90>]
N2 - T=1000.000 starting
N2 - T=1000.000 sending Join() to ['N0']
N0
Join()
[(expires: 1000.01824393, address: N0), (expires: 1000.7, address: N1), (expires: 1000.02715556, address: N0), (expires: 1000.7, address: N2)]
[<cluster.Bootstrap object at 0x104778290>]
Node address: N2, roles: [<cluster.Bootstrap object at 0x104778290>]
Network nodes: {'N0': <cluster.Node object at 0x104758d10>, 'N1': <cluster.Node object at 0x104758ed0>, 'N2': <cluster.Node object at 0x104778150>}, timers: [(expires: 1000.01824393, address: N0), (expires: 1000.7, address: N1), (expires: 1000.02715556, address: N0), (expires: 1000.7, address: N2)]
************** network run [(expires: 1000.01824393, address: N0), (expires: 1000.7, address: N1), (expires: 1000.02715556, address: N0), (expires: 1000.7, address: N2)]**************
(expires: 1000.01824393, address: N0)
执行回调
<functools.partial object at 0x104772260>
Node address: N0, roles: [<cluster.Seed object at 0x104758dd0>]
N2
do_Join
N0.Seed - T=1000.018 received Join() from N2
Seed initial_state: {}, seen_peers: set(['N2']), exit_timer: None
None
************** network run [(expires: 1000.02715556, address: N0), (expires: 1000.7, address: N1), (expires: 1000.7, address: N2)]**************
(expires: 1000.02715556, address: N0)
执行回调
<functools.partial object at 0x1047721b0>
Node address: N0, roles: [<cluster.Seed object at 0x104758dd0>]
N1
do_Join
N0.Seed - T=1000.027 received Join() from N1
Seed initial_state: {}, seen_peers: set(['N1', 'N2']), exit_timer: None
N0 - T=1000.027 sending Welcome(state={}, slot=1, decisions={}) to ['N1', 'N2']
N1
Welcome(state={}, slot=1, decisions={})
N2
Welcome(state={}, slot=1, decisions={})
[(expires: 1000.04356474, address: N2), (expires: 1000.07009912, address: N1), (expires: 1000.7, address: N1), (expires: 1000.7, address: N2)]
Seed initial_state: {}, seen_peers: set(['N1', 'N2']), exit_timer: (expires: 1001.42715556, address: N0)
[(expires: 1000.04356474, address: N2), (expires: 1000.07009912, address: N1), (expires: 1000.7, address: N1), (expires: 1000.7, address: N2), (expires: 1001.42715556, address: N0)]
None
************** network run [(expires: 1000.04356474, address: N2), (expires: 1000.07009912, address: N1), (expires: 1000.7, address: N1), (expires: 1000.7, address: N2), (expires: 1001.42715556, address: N0)]**************
(expires: 1000.04356474, address: N2)
执行回调
<functools.partial object at 0x104772470>
Node address: N2, roles: [<cluster.Bootstrap object at 0x104778290>]
N0
do_Welcome
N2.Bootstrap - T=1000.044 received Welcome(state={}, slot=1, decisions={}) from N0
Replica state: {}, slot: 1, decisions: {}, proposals: {}, next_slot: 1, latest_leader: None, latest_leader_timeout: None, running: True
Leader ballot_num: Ballot(n=0, leader='N2'), active: False, scouting: False, running: True
asd
[(expires: 1000.07009912, address: N1), (expires: 1000.54356474, address: N2), (expires: 1000.7, address: N1), (expires: 1001.42715556, address: N0), (expires: 1000.7, address: N2)]
[<cluster.Bootstrap object at 0x104778290>, <cluster.Acceptor object at 0x1047781d0>, <cluster.Replica object at 0x104778610>, <cluster.Leader object at 0x1047786d0>]
Bootstrap running: False
[<cluster.Acceptor object at 0x1047781d0>, <cluster.Replica object at 0x104778610>, <cluster.Leader object at 0x1047786d0>]
None
************** network run [(expires: 1000.07009912, address: N1), (expires: 1000.54356474, address: N2), (expires: 1000.7, address: N1), (expires: 1001.42715556, address: N0), (expires: 1000.7, address: N2)]**************
(expires: 1000.07009912, address: N1)
执行回调
<functools.partial object at 0x1047723c0>
Node address: N1, roles: [<cluster.Bootstrap object at 0x104758f90>]
N0
do_Welcome
N1.Bootstrap - T=1000.070 received Welcome(state={}, slot=1, decisions={}) from N0
Replica state: {}, slot: 1, decisions: {}, proposals: {}, next_slot: 1, latest_leader: None, latest_leader_timeout: None, running: True
Leader ballot_num: Ballot(n=0, leader='N1'), active: False, scouting: False, running: True
asd
[(expires: 1000.54356474, address: N2), (expires: 1000.57009912, address: N1), (expires: 1000.7, address: N1), (expires: 1001.42715556, address: N0), (expires: 1000.7, address: N2)]
[<cluster.Bootstrap object at 0x104758f90>, <cluster.Acceptor object at 0x104778450>, <cluster.Replica object at 0x104778850>, <cluster.Leader object at 0x104778910>]
Bootstrap running: False
[<cluster.Acceptor object at 0x104778450>, <cluster.Replica object at 0x104778850>, <cluster.Leader object at 0x104778910>]
None
************** network run [(expires: 1000.54356474, address: N2), (expires: 1000.57009912, address: N1), (expires: 1000.7, address: N1), (expires: 1001.42715556, address: N0), (expires: 1000.7, address: N2)]**************
(expires: 1000.54356474, address: N2)
执行回调
<function <lambda> at 0x10476b6e0>
asd
[(expires: 1000.57009912, address: N1), (expires: 1000.7, address: N2), (expires: 1000.7, address: N1), (expires: 1001.42715556, address: N0), (expires: 1001.04356474, address: N2)]
None
************** network run [(expires: 1000.57009912, address: N1), (expires: 1000.7, address: N2), (expires: 1000.7, address: N1), (expires: 1001.42715556, address: N0), (expires: 1001.04356474, address: N2)]**************
(expires: 1000.57009912, address: N1)
执行回调
<function <lambda> at 0x10476b7d0>
asd
[(expires: 1000.7, address: N1), (expires: 1000.7, address: N2), (expires: 1001.04356474, address: N2), (expires: 1001.42715556, address: N0), (expires: 1001.07009912, address: N1)]
None
************** network run [(expires: 1000.7, address: N1), (expires: 1000.7, address: N2), (expires: 1001.04356474, address: N2), (expires: 1001.42715556, address: N0), (expires: 1001.07009912, address: N1)]**************
(expires: 1000.7, address: N1)
执行回调
<function <lambda> at 0x10476b500>
False
************** network run [(expires: 1000.7, address: N2), (expires: 1001.07009912, address: N1), (expires: 1001.04356474, address: N2), (expires: 1001.42715556, address: N0)]**************
(expires: 1000.7, address: N2)
执行回调
<function <lambda> at 0x10476b578>
False
************** network run [(expires: 1001.04356474, address: N2), (expires: 1001.07009912, address: N1), (expires: 1001.42715556, address: N0)]**************
(expires: 1001.04356474, address: N2)
执行回调
<function <lambda> at 0x10476b848>
asd
[(expires: 1001.07009912, address: N1), (expires: 1001.42715556, address: N0), (expires: 1001.54356474, address: N2)]
None
************** network run [(expires: 1001.07009912, address: N1), (expires: 1001.42715556, address: N0), (expires: 1001.54356474, address: N2)]**************
(expires: 1001.07009912, address: N1)
执行回调
<function <lambda> at 0x10476b6e0>
asd
[(expires: 1001.42715556, address: N0), (expires: 1001.54356474, address: N2), (expires: 1001.57009912, address: N1)]
None
************** network run [(expires: 1001.42715556, address: N0), (expires: 1001.54356474, address: N2), (expires: 1001.57009912, address: N1)]**************
(expires: 1001.42715556, address: N0)
执行回调
<function <lambda> at 0x104611230>
[<cluster.Seed object at 0x104758dd0>, <cluster.Bootstrap object at 0x104778790>]
N0 - T=1001.427 sending Join() to ['N0']
N0
Join()
发送地址和接收地址一样
[(expires: 1001.42715556, address: N0), (expires: 1001.57009912, address: N1), (expires: 1001.54356474, address: N2), (expires: 1002.12715556, address: N0)]
[<cluster.Seed object at 0x104758dd0>, <cluster.Bootstrap object at 0x104778790>]
None
************** network run [(expires: 1001.42715556, address: N0), (expires: 1001.57009912, address: N1), (expires: 1001.54356474, address: N2), (expires: 1002.12715556, address: N0)]**************
(expires: 1001.42715556, address: N0)
执行回调
<function <lambda> at 0x10476b500>
Node address: N0, roles: [<cluster.Bootstrap object at 0x104778790>]
N0
do_Join
None
************** network run [(expires: 1001.54356474, address: N2), (expires: 1001.57009912, address: N1), (expires: 1002.12715556, address: N0)]**************
(expires: 1001.54356474, address: N2)
执行回调
<function <lambda> at 0x10476b578>
asd
[(expires: 1001.57009912, address: N1), (expires: 1002.12715556, address: N0), (expires: 1002.04356474, address: N2)]
None
************** network run [(expires: 1001.57009912, address: N1), (expires: 1002.12715556, address: N0), (expires: 1002.04356474, address: N2)]**************
(expires: 1001.57009912, address: N1)
执行回调
<function <lambda> at 0x10476b848>
asd
[(expires: 1002.04356474, address: N2), (expires: 1002.12715556, address: N0), (expires: 1002.07009912, address: N1)]
None
************** network run [(expires: 1002.04356474, address: N2), (expires: 1002.12715556, address: N0), (expires: 1002.07009912, address: N1)]**************
(expires: 1002.04356474, address: N2)
执行回调
<function <lambda> at 0x10476b500>
asd
[(expires: 1002.07009912, address: N1), (expires: 1002.12715556, address: N0), (expires: 1002.54356474, address: N2)]
None
************** network run [(expires: 1002.07009912, address: N1), (expires: 1002.12715556, address: N0), (expires: 1002.54356474, address: N2)]**************
(expires: 1002.07009912, address: N1)
执行回调
<function <lambda> at 0x10476b578>
asd
[(expires: 1002.12715556, address: N0), (expires: 1002.54356474, address: N2), (expires: 1002.57009912, address: N1)]
None
************** network run [(expires: 1002.12715556, address: N0), (expires: 1002.54356474, address: N2), (expires: 1002.57009912, address: N1)]**************
(expires: 1002.12715556, address: N0)
执行回调
<function <lambda> at 0x10476b6e0>
N0 - T=1002.127 sending Join() to ['N1']
N1
Join()
[(expires: 1002.15026647, address: N1), (expires: 1002.57009912, address: N1), (expires: 1002.54356474, address: N2), (expires: 1002.82715556, address: N0)]
[<cluster.Bootstrap object at 0x104778790>]
None
************** network run [(expires: 1002.15026647, address: N1), (expires: 1002.57009912, address: N1), (expires: 1002.54356474, address: N2), (expires: 1002.82715556, address: N0)]**************
(expires: 1002.15026647, address: N1)
执行回调
<functools.partial object at 0x1047723c0>
Node address: N1, roles: [<cluster.Acceptor object at 0x104778450>, <cluster.Replica object at 0x104778850>, <cluster.Leader object at 0x104778910>]
N0
do_Join
N1.Replica - T=1002.150 received Join() from N0
N1 - T=1002.150 sending Welcome(state={}, slot=1, decisions={}) to ['N0']
N0
Welcome(state={}, slot=1, decisions={})
None
************** network run [(expires: 1002.19837915, address: N0), (expires: 1002.54356474, address: N2), (expires: 1002.82715556, address: N0), (expires: 1002.57009912, address: N1)]**************
(expires: 1002.19837915, address: N0)
执行回调
<functools.partial object at 0x104772368>
Node address: N0, roles: [<cluster.Bootstrap object at 0x104778790>]
N1
do_Welcome
N0.Bootstrap - T=1002.198 received Welcome(state={}, slot=1, decisions={}) from N1
Replica state: {}, slot: 1, decisions: {}, proposals: {}, next_slot: 1, latest_leader: None, latest_leader_timeout: None, running: True
Leader ballot_num: Ballot(n=0, leader='N0'), active: False, scouting: False, running: True
asd
[(expires: 1002.54356474, address: N2), (expires: 1002.57009912, address: N1), (expires: 1002.82715556, address: N0), (expires: 1002.69837915, address: N0)]
[<cluster.Bootstrap object at 0x104778790>, <cluster.Acceptor object at 0x104778110>, <cluster.Replica object at 0x104778a10>, <cluster.Leader object at 0x104778ad0>]
Bootstrap running: False
[<cluster.Acceptor object at 0x104778110>, <cluster.Replica object at 0x104778a10>, <cluster.Leader object at 0x104778ad0>]
None
************** network run [(expires: 1002.54356474, address: N2), (expires: 1002.57009912, address: N1), (expires: 1002.82715556, address: N0), (expires: 1002.69837915, address: N0)]**************
(expires: 1002.54356474, address: N2)
执行回调
<function <lambda> at 0x10476b848>
asd
[(expires: 1002.57009912, address: N1), (expires: 1002.69837915, address: N0), (expires: 1002.82715556, address: N0), (expires: 1003.04356474, address: N2)]
None
************** network run [(expires: 1002.57009912, address: N1), (expires: 1002.69837915, address: N0), (expires: 1002.82715556, address: N0), (expires: 1003.04356474, address: N2)]**************
(expires: 1002.57009912, address: N1)
执行回调
<function <lambda> at 0x10476b500>
asd
[(expires: 1002.69837915, address: N0), (expires: 1003.04356474, address: N2), (expires: 1002.82715556, address: N0), (expires: 1003.07009912, address: N1)]
None
************** network run [(expires: 1002.69837915, address: N0), (expires: 1003.04356474, address: N2), (expires: 1002.82715556, address: N0), (expires: 1003.07009912, address: N1)]**************
(expires: 1002.69837915, address: N0)
执行回调
<function <lambda> at 0x10476b7d0>
asd
[(expires: 1002.82715556, address: N0), (expires: 1003.04356474, address: N2), (expires: 1003.07009912, address: N1), (expires: 1003.19837915, address: N0)]
None
************** network run [(expires: 1002.82715556, address: N0), (expires: 1003.04356474, address: N2), (expires: 1003.07009912, address: N1), (expires: 1003.19837915, address: N0)]**************
(expires: 1002.82715556, address: N0)
执行回调
<function <lambda> at 0x10476b578>
False
************** network run [(expires: 1003.04356474, address: N2), (expires: 1003.19837915, address: N0), (expires: 1003.07009912, address: N1)]**************
(expires: 1003.04356474, address: N2)
执行回调
<function <lambda> at 0x10476b8c0>
asd
[(expires: 1003.07009912, address: N1), (expires: 1003.19837915, address: N0), (expires: 1003.54356474, address: N2)]
None
************** network run [(expires: 1003.07009912, address: N1), (expires: 1003.19837915, address: N0), (expires: 1003.54356474, address: N2)]**************
(expires: 1003.07009912, address: N1)
执行回调
<function <lambda> at 0x10476b848>
asd
[(expires: 1003.19837915, address: N0), (expires: 1003.54356474, address: N2), (expires: 1003.57009912, address: N1)]
None
************** network run [(expires: 1003.19837915, address: N0), (expires: 1003.54356474, address: N2), (expires: 1003.57009912, address: N1)]**************
(expires: 1003.19837915, address: N0)
执行回调
<function <lambda> at 0x10476b500>
asd
[(expires: 1003.54356474, address: N2), (expires: 1003.57009912, address: N1), (expires: 1003.69837915, address: N0)]
None
************** network run [(expires: 1003.54356474, address: N2), (expires: 1003.57009912, address: N1), (expires: 1003.69837915, address: N0)]**************
(expires: 1003.54356474, address: N2)
执行回调
<function <lambda> at 0x10476b578>
asd
[(expires: 1003.57009912, address: N1), (expires: 1003.69837915, address: N0), (expires: 1004.04356474, address: N2)]
None
************** network run [(expires: 1003.57009912, address: N1), (expires: 1003.69837915, address: N0), (expires: 1004.04356474, address: N2)]**************
(expires: 1003.57009912, address: N1)
执行回调
<function <lambda> at 0x10476b8c0>
asd
[(expires: 1003.69837915, address: N0), (expires: 1004.04356474, address: N2), (expires: 1004.07009912, address: N1)]
None
************** network run [(expires: 1003.69837915, address: N0), (expires: 1004.04356474, address: N2), (expires: 1004.07009912, address: N1)]**************
(expires: 1003.69837915, address: N0)
执行回调
<function <lambda> at 0x10476b848>
asd
[(expires: 1004.04356474, address: N2), (expires: 1004.07009912, address: N1), (expires: 1004.19837915, address: N0)]
None
************** network run [(expires: 1004.04356474, address: N2), (expires: 1004.07009912, address: N1), (expires: 1004.19837915, address: N0)]**************
(expires: 1004.04356474, address: N2)
执行回调
<function <lambda> at 0x10476b500>
asd
[(expires: 1004.07009912, address: N1), (expires: 1004.19837915, address: N0), (expires: 1004.54356474, address: N2)]
None
************** network run [(expires: 1004.07009912, address: N1), (expires: 1004.19837915, address: N0), (expires: 1004.54356474, address: N2)]**************
(expires: 1004.07009912, address: N1)
执行回调
<function <lambda> at 0x10476b578>
asd
[(expires: 1004.19837915, address: N0), (expires: 1004.54356474, address: N2), (expires: 1004.57009912, address: N1)]
None
************** network run [(expires: 1004.19837915, address: N0), (expires: 1004.54356474, address: N2), (expires: 1004.57009912, address: N1)]**************
(expires: 1004.19837915, address: N0)
执行回调
<function <lambda> at 0x10476b8c0>
asd
[(expires: 1004.54356474, address: N2), (expires: 1004.57009912, address: N1), (expires: 1004.69837915, address: N0)]
None
************** network run [(expires: 1004.54356474, address: N2), (expires: 1004.57009912, address: N1), (expires: 1004.69837915, address: N0)]**************
(expires: 1004.54356474, address: N2)
执行回调
<function <lambda> at 0x10476b848>
asd
[(expires: 1004.57009912, address: N1), (expires: 1004.69837915, address: N0), (expires: 1005.04356474, address: N2)]
None
************** network run [(expires: 1004.57009912, address: N1), (expires: 1004.69837915, address: N0), (expires: 1005.04356474, address: N2)]**************
(expires: 1004.57009912, address: N1)
执行回调
<function <lambda> at 0x10476b500>
asd
[(expires: 1004.69837915, address: N0), (expires: 1005.04356474, address: N2), (expires: 1005.07009912, address: N1)]
None
************** network run [(expires: 1004.69837915, address: N0), (expires: 1005.04356474, address: N2), (expires: 1005.07009912, address: N1)]**************
(expires: 1004.69837915, address: N0)
执行回调
<function <lambda> at 0x10476b578>
asd
[(expires: 1005.04356474, address: N2), (expires: 1005.07009912, address: N1), (expires: 1005.19837915, address: N0)]
None
************** network run [(expires: 1005.04356474, address: N2), (expires: 1005.07009912, address: N1), (expires: 1005.19837915, address: N0)]**************
(expires: 1005.04356474, address: N2)
执行回调
<function <lambda> at 0x10476b8c0>
asd
[(expires: 1005.07009912, address: N1), (expires: 1005.19837915, address: N0), (expires: 1005.54356474, address: N2)]
None
************** network run [(expires: 1005.07009912, address: N1), (expires: 1005.19837915, address: N0), (expires: 1005.54356474, address: N2)]**************
(expires: 1005.07009912, address: N1)
执行回调
<function <lambda> at 0x10476b848>
asd
[(expires: 1005.19837915, address: N0), (expires: 1005.54356474, address: N2), (expires: 1005.57009912, address: N1)]
None
************** network run [(expires: 1005.19837915, address: N0), (expires: 1005.54356474, address: N2), (expires: 1005.57009912, address: N1)]**************
(expires: 1005.19837915, address: N0)
执行回调
<function <lambda> at 0x10476b500>
asd
[(expires: 1005.54356474, address: N2), (expires: 1005.57009912, address: N1), (expires: 1005.69837915, address: N0)]
None
************** network run [(expires: 1005.54356474, address: N2), (expires: 1005.57009912, address: N1), (expires: 1005.69837915, address: N0)]**************
(expires: 1005.54356474, address: N2)
执行回调
<function <lambda> at 0x10476b578>
asd
[(expires: 1005.57009912, address: N1), (expires: 1005.69837915, address: N0), (expires: 1006.04356474, address: N2)]
None

"""
