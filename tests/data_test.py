""" Tests regarding mauzr.data. """

import mauzr.data

__author__ = "Alexander Sowitzki"


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

    mauzr.data.aggregate(core, lambda vs, t, v: vs.copy(), c.dflt,
                         ((c.in_tpcs[0], c.deser, c.qos),
                          (c.in_tpcs[1], c.deser, c.qos),
                          (c.in_tpcs[2], c.deser, c.qos)),
                         (c.out_tpc, c.ser, c.qos))

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
                     (c.in_tpc, c.deser, c.qos), (c.out_tpc, c.ser, c.qos))
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
    core.mqtt.inj(c.in_tpc, 3)
    core.mqtt.exp(c.out_tpc, 7, c.ret)
    core.mqtt.inj(c.in_tpc, 2)

    mauzr.data.convert(core, lambda v: 7 if v == 3 else None, c.ret, c.dflt,
                       (c.in_tpc, c.deser, c.qos), (c.out_tpc, c.ser, c.qos))

    with core:
        core.mqtt(0.1, 1)
