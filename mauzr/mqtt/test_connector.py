""" Test connector module. """

from pathlib import Path
import unittest
from unittest.mock import Mock, call
from mauzr.mqtt.connector import QoSShelf, Connector

__author__ = "Alexander Sowitzki"


class QoSShelfTest(unittest.TestCase):
    """ Test Agent class. """

    def test_all(self):  # pylint: disable=too-many-statements
        """ Test all. """

        shell = Mock()
        low = Mock()
        low.__len__ = Mock(return_value=1)
        low.__getitem__ = Mock()
        low.__setitem__ = Mock()
        low.__delitem__ = Mock()
        default_id = 65535
        shell.args.data_path = Path("/tmp")
        shelf = QoSShelf(log=Mock(), shell=shell, default_id=default_id,
                         factory=Mock(return_value=low))
        every = shell.sched.every
        every.assert_called_once_with(shell.args.sync_interval, shelf.sync)
        every().enable.assert_not_called()
        every.reset_mock()
        shelf.__enter__()
        low.setdefault.assert_called_once_with("pkg_id", default_id)
        shelf.factory.assert_called_once_with(str(shell.args.data_path/"qos"))
        every.assert_not_called()
        every().enable.assert_called_once_with()

        low.__setitem__.assert_not_called()
        pkg_id = 60
        data = bytes([1, 2, 3])
        shelf[pkg_id] = data
        low.__setitem__.assert_called_once_with(str(pkg_id), data)
        low.__setitem__.reset_mock()
        self.assertIsInstance(shelf[pkg_id], Mock)
        low.__getitem__.assert_called_once_with(str(pkg_id))
        low.__getitem__.reset_mock()
        low.__delitem__.assert_not_called()
        del shelf[pkg_id]
        low.__delitem__.assert_called_once_with(str(pkg_id))

        low.sync.assert_not_called()
        shelf.sync()
        low.sync.assert_called_once_with()
        low.sync.reset_mock()
        low.__setitem__.assert_not_called()
        shelf.clear()
        low.__getitem__.assert_called_once_with("pkg_id")
        low.clear.assert_called_once_with()
        low.__setitem__.assert_called_once_with("pkg_id",
                                                low.__getitem__("pkg_id"))

        low.items = Mock(return_value=(("pkg_id", 1),
                                       (3, bytes((0, 0, 0, 0)))))
        self.assertEqual(((3, bytes([8, 0, 0, 0]),),), tuple(shelf.replay()))

        low.__setitem__.reset_mock()
        low.__getitem__.side_effect = [default_id, default_id, default_id+1]
        self.assertEqual(default_id+1, shelf.new_pkg_id())
        low.__setitem__.assert_called_once_with("pkg_id", default_id + 1)

        low.__setitem__.reset_mock()
        low.__getitem__.side_effect = [default_id+1, default_id+1, default_id]
        self.assertEqual(default_id, shelf.new_pkg_id())
        low.__setitem__.assert_has_calls([call("pkg_id", default_id+2),
                                          call("pkg_id", default_id)])

        every().disable.assert_not_called()
        low.close.assert_not_called()
        every().disable.assert_not_called()
        shelf.__exit__(None, None, None)
        every().disable.assert_called_once_with()
        low.close.assert_called_once_with()


class ConnectorTest(unittest.TestCase):
    """ Test Agent class. """

    @staticmethod
    def connector_mock():
        """ Test all. """

        socket_factory = Mock(return_value=Mock())
        shelf_factory = Mock()
        shell = Mock()
        shell.args.keepalive = 3
        shell.args.name = "testagent"
        shell.sched.every.side_effect = [Mock(), Mock()]
        return Connector(shell=shell, socket_factory=socket_factory,
                         shelf_factory=shelf_factory)
