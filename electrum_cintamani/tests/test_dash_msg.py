from ipaddress import IPv6Address

from electrum_cintamani.cintamani_msg import (DashVersionMsg, DashDsaMsg, DashDssuMsg,
                                    DashDsqMsg, DashDsiMsg, DashDsfMsg,
                                    DashDssMsg, DashDscMsg)
from electrum_cintamani.cintamani_tx import TxOutPoint, CTxIn, CTxOut
from electrum_cintamani.transaction import Transaction
from electrum_cintamani.util import bfh, bh2u

from . import TestCaseForTestnet


class TestDashMsg(TestCaseForTestnet):

    def test_version_msg(self):
        msg = DashVersionMsg.from_hex(VERSION_MSG)
        assert msg.version == 70215
        assert msg.services == 5
        assert msg.timestamp == 1567673683
        assert msg.recv_services == 0
        assert msg.recv_ip == IPv6Address('::')
        assert msg.recv_port == 0
        assert msg.trans_services == 5
        assert msg.trans_ip == IPv6Address('::')
        assert msg.trans_port == 0
        assert msg.nonce == 12615609395080869973
        assert msg.user_agent == b'/Dash Core:0.14.0.3/'
        assert msg.start_height == 169118
        assert msg.relay == 1
        assert msg.mnauth_challenge == bfh('9404092b784754ae2757c614d3e76ae1'
                                           '80dc66305055ee6e6c62b409c1d57b30')
        assert msg.fMasternode == 0
        assert bh2u(msg.serialize()) == VERSION_MSG

    def test_dsa_msg(self):
        msg = DashDsaMsg.from_hex(DSA_MSG)
        assert msg.nDenom == 2
        assert type(msg.txCollateral) == str
        tx = Transaction(msg.txCollateral)
        assert type(tx) == Transaction
        assert bh2u(msg.serialize()) == DSA_MSG

    def test_dssu_msg(self):
        msg = DashDssuMsg.from_hex(DSSU_MSG)
        assert msg.sessionID == 67305985
        assert msg.state == 5
        assert msg.entriesCount == 3
        assert msg.statusUpdate == 1
        assert msg.messageID == 21
        assert bh2u(msg.serialize()) == DSSU_MSG

    def test_dsq_msg(self):
        msg = DashDsqMsg.from_hex(DSQ_MSG)
        assert msg.nDenom == 2
        assert type(msg.masternodeOutPoint) == TxOutPoint
        assert msg.nTime == 1567673683
        assert msg.fReady
        assert len(msg.vchSig) == 96
        assert bh2u(msg.serialize()) == DSQ_MSG

    def test_dsi_msg(self):
        msg = DashDsiMsg.from_hex(DSI_MSG)
        assert len(msg.vecTxDSIn) == 2
        for txin in msg.vecTxDSIn:
            assert type(txin) == CTxIn
        assert type(msg.txCollateral) == str
        tx = Transaction(msg.txCollateral)
        assert type(tx) == Transaction
        assert len(msg.vecTxDSOut) == 2
        for txout in msg.vecTxDSOut:
            assert type(txout) == CTxOut
        assert bh2u(msg.serialize()) == DSI_MSG

    def test_dsf_msg(self):
        msg = DashDsfMsg.from_hex(DSF_MSG)
        assert msg.sessionID == 7
        assert type(msg.txFinal) == Transaction
        assert bh2u(msg.serialize()) == DSF_MSG

    def test_dss_msg(self):
        msg = DashDssMsg.from_hex(DSS_MSG)
        assert len(msg.inputs) == 2
        for txin in msg.inputs:
            assert type(txin) == CTxIn
        assert bh2u(msg.serialize()) == DSS_MSG

    def test_dsc_msg(self):
        msg = DashDscMsg.from_hex(DSC_MSG)
        assert msg.sessionID == 67305985
        assert msg.messageID == 21
        assert bh2u(msg.serialize()) == DSC_MSG


VERSION_MSG = ('47120100050000000000000053cd705d0000000000000000'
               '000000000000000000000000000000000000000000000500'
               '000000000000000000000000000000000000000000000000'
               '5538e08ae7a513af142f4461736820436f72653a302e3134'
               '2e302e332f9e940200019404092b784754ae2757c614d3e7'
               '6ae180dc66305055ee6e6c62b409c1d57b3000')


DSA_MSG = ('020000000200000001df2149d4b1805f1842aace662956f8'
           '5d442d0aab9acf68fe13e2f93f9be9b259000000006b4830'
           '450221009a24e58366f1c7a4cbb170f6dc813d44023f176f'
           '5fa87809ee9cc561ebd6f29802204b05f289613e86727025'
           'd71d8f58315d30ec3e4d8a7aef7b12a7425ff4fe345a0121'
           '034963cceab57f14094933a8272e6dd3d76a30c6f1d22fd9'
           '7c2f7e5dff0d6efe94feffffff019b3bd971020000001976'
           'a914ec785ad145df029f48e51e305483fda47f7834a588ac'
           'f06d0200')


DSSU_MSG = ('0102030405000000030000000100000015000000')


DSQ_MSG = ('020000005d442d0aab9acf68fe13e2f93f9be9b25d442d0a'
           'ab9acf68fe13e2f93f9be9b20100000053cd705d00000000'
           '01605d442d0aab9acf68fe13e2f93f9be9b25d442d0aab9a'
           'cf68fe13e2f93f9be9b25d442d0aab9acf68fe13e2f93f9b'
           'e9b25d442d0aab9acf68fe13e2f93f9be9b25d442d0aab9a'
           'cf68fe13e2f93f9be9b25d442d0aab9acf68fe13e2f93f9b'
           'e9b2')


DSI_MSG = ('02ab9acf68fe13e2f93f9be9b201000000ab9acf68fe13e2'
           'f93f9be9b20100000001000000080102030405060708ffff'
           'ffffab9acf68fe13e2f93f9be9b201000000ab9acf68fe13'
           'e2f93f9be9b20100000002000000081112131415161718ff'
           'ffffff0200000001df2149d4b1805f1842aace662956f85d'
           '442d0aab9acf68fe13e2f93f9be9b259000000006b483045'
           '0221009a24e58366f1c7a4cbb170f6dc813d44023f176f5f'
           'a87809ee9cc561ebd6f29802204b05f289613e86727025d7'
           '1d8f58315d30ec3e4d8a7aef7b12a7425ff4fe345a012103'
           '4963cceab57f14094933a8272e6dd3d76a30c6f1d22fd97c'
           '2f7e5dff0d6efe94feffffff019b3bd971020000001976a9'
           '14ec785ad145df029f48e51e305483fda47f7834a588acf0'
           '6d0200020100000000000000080102030405060708020000'
           '0000000000081112131415161718')


DSF_MSG = ('070000000200000001df2149d4b1805f1842aace662956f8'
           '5d442d0aab9acf68fe13e2f93f9be9b259000000006b4830'
           '450221009a24e58366f1c7a4cbb170f6dc813d44023f176f'
           '5fa87809ee9cc561ebd6f29802204b05f289613e86727025'
           'd71d8f58315d30ec3e4d8a7aef7b12a7425ff4fe345a0121'
           '034963cceab57f14094933a8272e6dd3d76a30c6f1d22fd9'
           '7c2f7e5dff0d6efe94feffffff019b3bd971020000001976'
           'a914ec785ad145df029f48e51e305483fda47f7834a588ac'
           'f06d0200')


DSS_MSG = ('02ab9acf68fe13e2f93f9be9b201000000ab9acf68fe13e2'
           'f93f9be9b20100000001000000080102030405060708ffff'
           'ffffab9acf68fe13e2f93f9be9b201000000ab9acf68fe13'
           'e2f93f9be9b20100000002000000081112131415161718ff'
           'ffffff')


DSC_MSG = ('0102030415000000')
