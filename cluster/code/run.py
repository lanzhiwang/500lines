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

    peers = ['N%d' % i for i in range(7)]  # ['N0', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6']
    for p in peers:
        node = network.new_node(address=p)
        if p == 'N0':
            Seed(node, initial_state={}, peers=peers, execute_fn=key_value_state_machine)
        else:
            Bootstrap(node, execute_fn=key_value_state_machine, peers=peers).start()

    for key in 'ab':
        do_sequence(network, node, key)

    # def req_done(output):
    #     return output

    # input = ('set', 'a', 10)
    # Requester(node, input, req_done).start()


    # print(network.timers)
    network.run()

if __name__ == "__main__":
    main()
