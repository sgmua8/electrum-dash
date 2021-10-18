# -*- coding: utf-8 -*-

import time
from enum import IntEnum

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QGridLayout, QDialog, QVBoxLayout, QCheckBox,
                             QTabWidget, QWidget, QLabel, QSpinBox, QLineEdit,
                             QTreeWidget, QTreeWidgetItem, QMenu, QHeaderView)

from electrum_cintamani import constants, util
from electrum_cintamani.cintamani_net import MIN_PEERS_LIMIT, MAX_PEERS_LIMIT
from electrum_cintamani.i18n import _
from electrum_cintamani.logging import get_logger

from .util import Buttons, CloseButton


_logger = get_logger(__name__)


MATCH_STR_CS = Qt.MatchFixedString | Qt.MatchCaseSensitive


class DashPeersWidget(QTreeWidget):
    class Columns(IntEnum):
        PEER = 0
        UAGENT = 1
        PING = 2
        READ = 3
        WRITE = 4

    def __init__(self, parent):
        QTreeWidget.__init__(self)
        self.parent = parent
        self.setHeaderLabels([_('Peer'), _('User Agent'), _('Ping time (ms)'),
                              _('Received KiB'), _('Sent KiB')])
        h = self.header()
        mode = QHeaderView.ResizeToContents
        h.setSectionResizeMode(self.Columns.PEER, mode)
        h.setSectionResizeMode(self.Columns.UAGENT, mode)
        h.setSectionResizeMode(self.Columns.PING, mode)
        h.setSectionResizeMode(self.Columns.READ, mode)
        h.setSectionResizeMode(self.Columns.WRITE, mode)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.create_menu)

    def create_menu(self, position):
        item = self.currentItem()
        if not item:
            return
        cintamani_net = self.parent.network.cintamani_net
        peer = item.text(self.Columns.PEER)
        menu = QMenu()
        menu.addAction(_('Disconnect'), lambda: self.disconnect(peer))
        if not cintamani_net.use_static_peers:
            menu.addAction(_('Ban'),
                           lambda: self.disconnect(peer, 'ban from gui'))
        menu.exec_(self.viewport().mapToGlobal(position))

    def disconnect(self, peer, msg=None):
        cintamani_net = self.parent.network.cintamani_net
        cintamani_peer = cintamani_net.peers.get(peer)
        if cintamani_peer:
            if msg:
                cintamani_peer.ban(msg)
            cintamani_peer.close()

    def update(self, event=None, args=None):
        cintamani_net = self.parent.network.cintamani_net
        peers = cintamani_net.peers
        if event is None:
            self.clear()
            for peer, cintamani_peer in sorted(list(peers.items())):
                self.add_peer(peer, cintamani_peer)
        elif event == 'cintamani-peers-updated':
            action, peer = args
            if action == 'added':
                cintamani_peer = peers.get(peer)
                if cintamani_peer:
                    self.add_peer(peer, cintamani_peer, insert=True)
            elif action == 'removed':
                items = self.findItems(peer, MATCH_STR_CS)
                if items:
                    idx = self.indexOfTopLevelItem(items[0])
                    self.takeTopLevelItem(idx)
        elif event == 'cintamani-net-activity':
            for peer, cintamani_peer in sorted(list(peers.items())):
                items = self.findItems(peer, MATCH_STR_CS)
                if items:
                    ping_time = str(cintamani_peer.ping_time)
                    read_kbytes = str(round(cintamani_peer.read_bytes/1024, 1))
                    write_kbytes = str(round(cintamani_peer.write_bytes/1024, 1))
                    for i in items:
                        i.setText(self.Columns.PING, ping_time)
                        i.setText(self.Columns.READ, read_kbytes)
                        i.setText(self.Columns.WRITE, write_kbytes)
        super().update()

    def add_peer(self, peer, cintamani_peer, insert=False):
        cintamani_net = self.parent.network.cintamani_net
        peers = cintamani_net.peers
        v = cintamani_peer.version
        user_agent = v.user_agent.decode('utf-8')
        ping_time = str(cintamani_peer.ping_time)
        read_kbytes = str(round(cintamani_peer.read_bytes/1024, 1))
        write_kbytes = str(round(cintamani_peer.write_bytes/1024, 1))
        peers_item = QTreeWidgetItem([peer, user_agent, ping_time,
                                      read_kbytes, write_kbytes])
        if peers:
            sorted_peers = sorted(list(peers.keys()))
            if peer in sorted_peers:
                idx = sorted_peers.index(peer)
                self.insertTopLevelItem(idx, peers_item)
            else:
                self.addTopLevelItem(peers_item)
        else:
            self.addTopLevelItem(peers_item)


class SporksWidget(QTreeWidget):
    class Columns(IntEnum):
        NAME = 0
        ACTIVE = 1
        VALUE = 2
        DEFAULT = 3

    def __init__(self, parent):
        QTreeWidget.__init__(self)
        self.parent = parent
        self.setHeaderLabels([_('Spork'), _('Active'), _('Value'), ''])
        h = self.header()
        mode = QHeaderView.ResizeToContents
        h.setSectionResizeMode(self.Columns.NAME, mode)
        h.setSectionResizeMode(self.Columns.ACTIVE, mode)
        h.setSectionResizeMode(self.Columns.VALUE, mode)
        h.setSectionResizeMode(self.Columns.DEFAULT, mode)

    def update(self):
        cintamani_net = self.parent.network.cintamani_net
        sporks_dict = cintamani_net.sporks.as_dict()
        self.clear()
        for k in sorted(list(sporks_dict.keys())):
            name = sporks_dict[k]['name']
            active = str(sporks_dict[k]['active'])
            value = str(sporks_dict[k]['value'])
            default = _('Default') if sporks_dict[k]['default'] else ''
            spork_item = QTreeWidgetItem([name, active, value, default])
            self.addTopLevelItem(spork_item)
        super().update()


class BanlistWidget(QTreeWidget):
    class Columns(IntEnum):
        PEER = 0
        UA = 1
        MSG = 2
        AT = 3

    def __init__(self, parent):
        QTreeWidget.__init__(self)
        self.parent = parent
        self.setHeaderLabels([_('Peer'), _('User Agent'),
                              _('Message'), _('Ban time')])
        h = self.header()
        mode = QHeaderView.ResizeToContents
        h.setSectionResizeMode(self.Columns.PEER, mode)
        h.setSectionResizeMode(self.Columns.UA, mode)
        h.setSectionResizeMode(self.Columns.MSG, mode)
        h.setSectionResizeMode(self.Columns.AT, mode)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.create_menu)

    def create_menu(self, position):
        item = self.currentItem()
        if not item:
            return
        peer = item.text(self.Columns.PEER)
        menu = QMenu()
        menu.addAction(_('Remove'), lambda: self.unban(peer))
        menu.exec_(self.viewport().mapToGlobal(position))

    def unban(self, peer):
        cintamani_net = self.parent.network.cintamani_net
        if peer:
            cintamani_net._remove_banned_peer(peer)

    def update(self, event=None, args=None):
        cintamani_net = self.parent.network.cintamani_net
        banlist = cintamani_net.banlist
        if event is None:
            self.clear()
            for peer in sorted(list(banlist.keys())):
                self.add_peer(peer)
        else:
            action, peer = args
            if action == 'added':
                self.add_peer(peer, insert=True)
            elif action == 'removed':
                items = self.findItems(peer, MATCH_STR_CS)
                if items:
                    idx = self.indexOfTopLevelItem(items[0])
                    self.takeTopLevelItem(idx)
        super().update()

    def add_peer(self, peer, insert=False):
        cintamani_net = self.parent.network.cintamani_net
        banlist = cintamani_net.banlist
        ua = banlist[peer]['ua']
        at = str(time.ctime(banlist[peer]['at']))
        msg = str(banlist[peer]['msg'])
        banlist_item = QTreeWidgetItem([peer, ua, msg, at])
        if banlist:
            sorted_banlist = sorted(list(banlist.keys()))
            if peer in sorted_banlist:
                idx = sorted_banlist.index(peer)
                self.insertTopLevelItem(idx, banlist_item)
            else:
                self.addTopLevelItem(banlist_item)
        else:
            self.addTopLevelItem(banlist_item)


class DashNetDialogLayout(object):

    def __init__(self, network, config, parent):
        self.parent = parent
        self.network = network
        self.config = config

        self.tabs = tabs = QTabWidget()
        cintamani_net_tab = QWidget()
        sporks_tab = QWidget()
        banlist_tab = QWidget()
        bls_speed_tab = QWidget()
        tabs.addTab(cintamani_net_tab, _('Dash Network'))
        tabs.addTab(sporks_tab, _('Sporks'))
        tabs.addTab(banlist_tab, _('Banlist'))

        if parent.is_testnet:
            tabs.addTab(bls_speed_tab, _('BLS Speed'))
            self.min_t = 1000
            self.max_t = 0
            self.n_measures = -1

            def min_str():
                return _('Min time') + f': {self.min_t}'

            def max_str():
                return _('Max time') + f': {self.max_t}'

            self.min_label = QLabel(min_str())
            self.max_label = QLabel(max_str())
            vbox = QVBoxLayout(bls_speed_tab)
            vbox.addWidget(self.min_label)
            vbox.addWidget(self.max_label)
            self.timer = QTimer()
            self.timer.setInterval(500)

            def update_bls_speed():
                if self.parent.isVisible() and bls_speed_tab.isVisible():
                    start_t = time.time()
                    res = self.network.cintamani_net.test_bls_speed()
                    res_t = time.time() - start_t
                    _logger.info(f'Test BLS Speed: res={res}, time={res_t}')
                    self.min_t = min(self.min_t, res_t)
                    self.max_t = max(self.max_t, res_t)
                    self.min_label.setText(min_str())
                    self.max_label.setText(max_str())
                    self.n_measures += 1
                    if self.n_measures >= 100:
                        self.timer.stop()
            self.timer.timeout.connect(update_bls_speed)

            def on_tabs_current_changed(*args):
                cur_widget = self.tabs.currentWidget()
                if cur_widget == bls_speed_tab and self.n_measures < 0:
                    self.n_measures = 0
                    self.timer.start()
            tabs.currentChanged.connect(on_tabs_current_changed)

        # Dash Network tab
        grid = QGridLayout(cintamani_net_tab)
        grid.setSpacing(8)
        cintamani_net = self.network.cintamani_net
        net = self.network

        # row 0
        self.both_kb = QLabel()
        self.read_kb = QLabel()
        self.write_kb = QLabel()
        grid.addWidget(self.both_kb, 0, 0, 1, 2)
        grid.addWidget(self.read_kb, 0, 2, 1, 2)
        grid.addWidget(self.write_kb, 0, 4, 1, 2)

        self.run_cintamani_net_cb = QCheckBox(_('Enable Dash Network'))
        self.run_cintamani_net_cb.setChecked(self.config.get('run_cintamani_net', True))
        run_cintamani_net_modifiable = self.config.is_modifiable('run_cintamani_net')
        self.run_cintamani_net_cb.setEnabled(run_cintamani_net_modifiable)

        def on_run_cintamani_net_cb_clicked(run_cintamani_net):
            self.config.set_key('run_cintamani_net', run_cintamani_net, True)
            net.run_from_another_thread(net.cintamani_net.set_parameters())
        self.run_cintamani_net_cb.clicked.connect(on_run_cintamani_net_cb_clicked)

        grid.addWidget(self.run_cintamani_net_cb, 0, 6, 1, 2)

        # row 1
        is_cmd_cintamani_peers = cintamani_net.is_cmd_cintamani_peers
        use_static_peers = cintamani_net.use_static_peers

        static_peers_label = QLabel(_('Static Peers:'))
        grid.addWidget(static_peers_label, 1, 0, 1, 1)

        self.cintamani_peers_e = QLineEdit()
        self.cintamani_peers_e.setText(cintamani_net.cintamani_peers_as_str())
        self.cintamani_peers_e.setReadOnly(is_cmd_cintamani_peers)

        def on_cintamani_peers_editing_end():
            if is_cmd_cintamani_peers:
                return
            res = cintamani_net.cintamani_peers_from_str(self.cintamani_peers_e.text())
            if type(res) == str:
                self.err_label.setText(f'Error: {res}')
            else:
                self.config.set_key('cintamani_peers', res, True)
                if cintamani_net.use_static_peers:
                    net.run_from_another_thread(net.cintamani_net.set_parameters())
        self.cintamani_peers_e.editingFinished.connect(on_cintamani_peers_editing_end)

        def on_cintamani_peers_changed():
            self.err_label.setText('')
        self.cintamani_peers_e.textChanged.connect(on_cintamani_peers_changed)

        grid.addWidget(self.cintamani_peers_e, 1, 1, 1, 5)

        self.use_static_cb = QCheckBox(_('Use Static Peers'))
        self.use_static_cb.setChecked(use_static_peers)
        self.use_static_cb.setEnabled(not is_cmd_cintamani_peers)

        def on_use_static_cb_clicked(use_static):
            self.config.set_key('cintamani_use_static_peers', use_static, True)
            net.run_from_another_thread(net.cintamani_net.set_parameters())
        self.use_static_cb.clicked.connect(on_use_static_cb_clicked)

        grid.addWidget(self.use_static_cb, 1, 6, 1, 2)
        # row 2 with error msg
        self.err_label = QLabel('')
        self.err_label.setObjectName('err-label')
        grid.addWidget(self.err_label, 2, 0, 1, -1)

        # row 3
        self.status_label = QLabel('')
        grid.addWidget(self.status_label, 3, 0, 1, 6)

        max_peers_label = _('Max Peers:')
        grid.addWidget(QLabel(max_peers_label), 3, 6, 1, 1)
        self.max_peers = QSpinBox()
        self.max_peers.setValue(cintamani_net.max_peers)
        self.max_peers.setRange(MIN_PEERS_LIMIT, MAX_PEERS_LIMIT)
        grid.addWidget(self.max_peers, 3, 7, 1, 1)

        def on_change_max_peers(max_peers):
            cintamani_net.max_peers = max_peers
        self.max_peers.valueChanged.connect(on_change_max_peers)

        # row 4
        self.cintamani_peers_list = DashPeersWidget(self)
        grid.addWidget(self.cintamani_peers_list, 4, 0, 1, -1)

        # Dash Sporks tab
        vbox = QVBoxLayout(sporks_tab)
        sporks_label = QLabel(_('Dash Sporks Values'))
        self.sporks_list = SporksWidget(self)
        vbox.addWidget(sporks_label)
        vbox.addWidget(self.sporks_list)

        # Dash Banlist tab
        vbox = QVBoxLayout(banlist_tab)
        banlist_label = QLabel(_('Banned Dash Peers'))
        self.banlist_list = BanlistWidget(self)
        vbox.addWidget(banlist_label)
        vbox.addWidget(self.banlist_list)

        # init layout
        vbox = QVBoxLayout()
        vbox.addWidget(tabs)
        self.layout_ = vbox
        self.update()

    def update(self, event=None, args=None):
        is_visible = self.parent.isVisible()
        if event is not None and not is_visible:
            return

        if event is None:
            self.update_cintamani_net_tab()
            self.sporks_list.update()
            self.banlist_list.update()
        elif event in ['cintamani-peers-updated', 'cintamani-net-activity']:
            self.update_cintamani_net_tab(event, args)
        elif event == 'sporks-activity':
            self.sporks_list.update()
        elif event == 'cintamani-banlist-updated':
            self.banlist_list.update(event, args)

    def update_cintamani_net_tab(self, event=None, args=None):
        cintamani_net = self.network.cintamani_net
        self.cintamani_peers_list.update(event, args)
        if event in [None, 'cintamani-net-activity']:
            read_bytes = cintamani_net.read_bytes
            write_bytes = cintamani_net.write_bytes
            both_kb = round((write_bytes + read_bytes)/1024, 1)
            read_kb = round(read_bytes/1024, 1)
            write_kb = round(write_bytes/1024, 1)
            self.both_kb.setText(_('Total') + f': {both_kb} KiB')
            self.read_kb.setText(_('Received') + f': {read_kb} KiB')
            self.write_kb.setText(_('Sent') + f': {write_kb} KiB')
        if event in [None, 'cintamani-peers-updated']:
            status = _('Connected Peers') + f': {len(cintamani_net.peers)}'
            self.status_label.setText(status)

    def layout(self):
        return self.layout_


class DashNetDialog(QDialog):
    def __init__(self, *, network, config, cintamani_net_sobj):
        QDialog.__init__(self)
        self.setWindowTitle(_('Dash Network'))
        self.setMinimumSize(700, 400)
        self.is_testnet = constants.net.TESTNET
        self.network = network
        self.dnlayout = DashNetDialogLayout(network, config, self)
        self.cintamani_net_sobj = cintamani_net_sobj
        vbox = QVBoxLayout(self)
        vbox.addLayout(self.dnlayout.layout())
        vbox.addLayout(Buttons(CloseButton(self)))
        self.cintamani_net_sobj.dlg.connect(self.on_updated)
        self._cleaned_up = False

    def show(self):
        super(DashNetDialog, self).show()
        if self.network:
            util.register_callback(self.on_cintamani_net,
                                   ['cintamani-peers-updated',
                                    'cintamani-net-activity',
                                    'sporks-activity',
                                    'cintamani-banlist-updated'])

    def closeEvent(self, e):
        if self.dnlayout.err_label.text():
            e.ignore()
        if self.network:
            util.unregister_callback(self.on_cintamani_net)

    def on_cintamani_net(self, event, *args):
        signal_obj = self.cintamani_net_sobj
        if signal_obj:
            signal_obj.dlg.emit(event, args)

    def on_updated(self, event=None, args=None):
        self.dnlayout.update(event, args)

    def clean_up(self):
        if self._cleaned_up:
            return
        self._cleaned_up = True
        self.cintamani_net_sobj.dlg.disconnect()
        self.cintamani_net_sobj = None
