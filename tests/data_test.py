"""
.. module:: tests.data_test
   :platform: posix
   :synopsis: Tests regarding mauzr.data

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import mauzr.data

def test_aggregate_run(core, merge):
    """ Test :func:`mauzr.data.aggregate` run under normal conditions. """

    c = merge
    assert len(c.in_tpcs) == 3

    core.mqtt.set(c.out_tpc, c.ser, c.qos, c.dflt)
    [core.mqtt.sub(topic, c.deser, c.qos)
     for topic in c.in_tpcs]

    core.mqtt.inj(c.in_tpcs[0], 1)
    core.mqtt.exp(c.out_tpc, {c.in_tpcs[0]: 1, c.in_tpcs[1]: None,
                              c.in_tpcs[2]: None}, True)
    core.mqtt.inj(c.in_tpcs[1], 2)
    core.mqtt.exp(c.out_tpc, {c.in_tpcs[0]: 1, c.in_tpcs[1]: 2,
                              c.in_tpcs[2]: None}, True)
    core.mqtt.inj(c.in_tpcs[2], 4)
    core.mqtt.exp(c.out_tpc, {c.in_tpcs[0]: 1, c.in_tpcs[1]: 2,
                              c.in_tpcs[2]: 4}, True)

    mauzr.data.aggregate(core, zip(c.in_tpcs, [c.deser] * 3),
                         lambda vs, t, v: vs.copy(), c.dflt, c.out_tpc,
                         c.ser, c.qos)

    with core:
        core.mqtt(0.1, 1)

def test_split_run(core, split):
    """ Test :func:`mauzr.data.split` run under normal conditions. """

    c = split
    assert len(c.out_tpcs) == 3

    [core.mqtt.set(topic, c.ser, c.qos, c.dflt) for topic in c.out_tpcs]
    #[core.mqtt.exp(topic, c.dflt, True) for topic in c.out_tpcs]
    core.mqtt.sub(c.in_tpc, c.deser, c.qos)

    core.mqtt.inj(c.in_tpc, [1, 2, 4])
    core.mqtt.exp(c.out_tpcs[0], 1, True)
    core.mqtt.exp(c.out_tpcs[1], 2, True)
    core.mqtt.exp(c.out_tpcs[2], 4, True)

    mauzr.data.split(core, c.in_tpc, c.out_tpcs, c.deser, c.ser, c.dflt, c.qos)

    with core:
        core.mqtt(0.1, 1)


def test_merge_run(core, merge):
    """ Test :func:`mauzr.data.merge` run under normal conditions. """

    c = merge
    assert len(c.in_tpcs) == 3

    core.mqtt.set(c.out_tpc, c.ser, c.qos, c.dflt)
    core.mqtt.exp(c.out_tpc, c.dflt, True)
    [core.mqtt.sub(topic, c.deser, c.qos) for topic in c.in_tpcs]


    core.mqtt.inj(c.in_tpcs[0], 1)
    core.mqtt.exp(c.out_tpc, [1, c.dflt[1], c.dflt[2]], True)
    core.mqtt.inj(c.in_tpcs[1], 2)
    core.mqtt.exp(c.out_tpc, [1, 2, c.dflt[2]], True)
    core.mqtt.inj(c.in_tpcs[2], 4)
    core.mqtt.exp(c.out_tpc, [1, 2, 4], True)

    mauzr.data.merge(core, c.in_tpcs, c.out_tpc, c.deser, c.ser, c.dflt, c.qos)

    with core:
        core.mqtt(0.1, 1)

def test_delay_run(core, delay):
    """ Test :func:`mauzr.data.delay` run under normal conditions. """

    import time

    c = delay

    core.mqtt.set(c.out_tpc, c.ser, c.qos, None)
    core.mqtt.sub(c.in_tpc, c.deser, c.qos)
    core.mqtt.inj(c.in_tpc, 3)
    core.mqtt.exp(c.out_tpc, c.pay, c.ret)
    core.mqtt.inj(c.in_tpc, 2)

    mqtt_delay = 0.1
    delay = 1000
    start_time = time.time()
    mauzr.data.delay(core, lambda v: v == 3, delay, c.pay, c.ret,
                     c.in_tpc, c.out_tpc, c.deser, c.ser, c.qos)
    with core:
        core.mqtt(mqtt_delay, 1)

    run_time = time.time() - start_time
    expected_time = mqtt_delay + delay / 1000
    assert run_time > expected_time

def test_convert_run(core, conversion):
    """ Test :func:`mauzr.data.map` run under normal conditions. """

    c = conversion

    core.mqtt.set(c.out_tpc, c.ser, c.qos, c.dflt)
    core.mqtt.sub(c.in_tpc, c.deser, c.qos)
    #core.mqtt.exp(c.out_tpc, c.dflt, c.ret)
    core.mqtt.inj(c.in_tpc, 3)
    core.mqtt.exp(c.out_tpc, 7, c.ret)
    core.mqtt.inj(c.in_tpc, 2)

    mauzr.data.convert(core, lambda v: 7 if v == 3 else None, c.ret, c.dflt,
                       c.in_tpc, c.out_tpc, c.deser, c.ser, c.qos)

    with core:
        core.mqtt(0.1, 1)
