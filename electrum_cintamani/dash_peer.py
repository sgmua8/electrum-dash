#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Dash-Electrum - lightweight Dash client
# Copyright (C) 2019 Dash Developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import asyncio
import ipaddress
import logging
import random
import time
from struct import pack, unpack
from typing import Optional, Tuple

from .bitcoin import public_key_to_p2pkh
from .crypto import sha256d
from .cintamani_msg import (SporkID, DashType, DashCmd, DashVersionMsg,
                       DashPingMsg, DashPongMsg, DashGetDataMsg,
                       DashGetMNListDMsg, DashSendDsqMsg)
from .ecc import ECPubkey
from .interface import GracefulDisconnect
from .logging import Logger
from .util import (log_exceptions, ignore_exceptions, SilentTaskGroup,
                   MySocksProxy)
from .version import ELECTRUM_VERSION


EMPTY_PAYLOAD_CHECKSUM = b'\x5D\xF6\xE0\xE2'
DASH_PROTO_VERSION = 70216
LOCAL_IP_ADDR = ipaddress.ip_address('127.0.0.1')
PAYLOAD_LIMIT = 32*2**20  # 32MiB
READ_LIMIT = 64*2**10     # 64KiB


def deserialize_peer(peer_str: str) -> Tuple[str, str]:
    # host might be IPv6 address, hence do rsplit:
    host, port = str(peer_str).rsplit(':', 1)
    if not host:
        raise ValueError('host must not be empty')
    int_port = int(port)  # Throw if cannot be converted to int
    if not (0 < int_port < 2**16):
        raise ValueError(f'port {port} is out of valid range')
    return host, int_port


class DashPeer(Logger):

    LOGGING_SHORTCUT = 'P'

    def __init__(self, cintamani_net, peer: str, proxy: Optional[dict],
                 debug=False, sml_entry=None, mix_session=None):
        self.default_port = cintamani_net.default_port
        self.start_str = cintamani_net.start_str

        self._is_open = False
        self.ready = asyncio.Future()
        self.peer = peer
        self.host, self.port = deserialize_peer(self.peer)
        Logger.__init__(self)
        assert cintamani_net.network.config.path
        self.cintamani_net = cintamani_net
        self.loop = cintamani_net.loop
        self.proxy = MySocksProxy.from_proxy_dict(proxy)
        self.sml_entry = sml_entry
        self.mix_session = mix_session

        self.sw = None  # StreamWriter
        self.sr = None  # StreamReader

        # Dump net msgs (only for this peer). Set at runtime from the console.
        self.debug = debug

        # Ping data
        self.ping_start = None
        self.ping_time = None
        self.ping_nonce = None

        # Sporks data
        self.sporks_done = False

        # getaddr flag
        self.getaddr_done = False

        # mnlistdiff data
        self.mnlistdiffs = asyncio.Queue(1)

        # Activity data
        self.read_bytes = 0
        self.read_time = 0
        self.write_bytes = 0
        self.write_time = 0

        self.ban_msg = None
        self.ban_till = None

        main_group_coro = self.cintamani_net.main_taskgroup.spawn(self.run())
        asyncio.run_coroutine_threadsafe(main_group_coro, self.loop)
        self.group = SilentTaskGroup()

    def diagnostic_name(self):
        return f'{self.host}:{self.port}'

    def handle_disconnect(func):
        async def wrapper_func(self: 'DashPeer', *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except GracefulDisconnect as e:
                self.logger.log(e.log_level, f'disconnecting due to {repr(e)}')
            finally:
                await self.cintamani_net.connection_down(self)
                # if was not 'ready' yet, schedule waiting coroutines:
                self.ready.cancel()
        return wrapper_func

    @ignore_exceptions  # do not kill main_taskgroup
    @log_exceptions
    @handle_disconnect
    async def run(self):
        try:
            self.ip_addr = ipaddress.ip_address(self.host)
        except Exception:
            addr = await self.cintamani_net.resolve_dns_over_https(self.host)
            if addr:
                self.ip_addr = ipaddress.ip_address(addr[0])
            else:
                self.ip_addr = ipaddress.ip_address('::')
        try:
            await self.open()
        except (asyncio.CancelledError, OSError) as e:
            self.logger.info(f'disconnecting due to: {repr(e)}')
            return

    def mark_ready(self):
        if self.ready.cancelled():
            raise GracefulDisconnect('conn establishment was too slow; '
                                     '*ready* future was cancelled')
        if self.ready.done():
            return
        self.ready.set_result(1)

    async def open(self):
        self.logger.info('open connection')
        if self.proxy is None:
            self.sr, self.sw = await asyncio.open_connection(host=self.host,
                                                             port=self.port,
                                                             limit=READ_LIMIT)
        else:
            self.sr, self.sw = \
                await self.proxy.open_connection(host=self.host,
                                                 port=self.port)

        self._is_open = True
        verack_received = False
        version_received = False
        await self.send_version()
        for res in [await self.read_next_msg() for i in range(2)]:
            if not res:
                continue
            if res.cmd == 'version':
                self.version = res.payload
                version_received = True
                await self.send_msg('verack')
            elif res.cmd == 'verack':
                verack_received = True
        if not version_received or not verack_received:
            raise GracefulDisconnect('Peer version handshake failed')
        await self.send_msg('senddsq', DashSendDsqMsg(True).serialize())

        self.mark_ready()
        self.logger.info(f'connection established')
        try:
            async with self.group as group:
                await group.spawn(self.process_msgs)
                await group.spawn(self.process_ping)
                await group.spawn(self.monitor_connection)
        except GracefulDisconnect:
            raise
        except (asyncio.CancelledError, OSError) as e:
            raise GracefulDisconnect(e) from e
        except Exception as e:
            raise GracefulDisconnect(e, log_level=logging.ERROR) from e

    async def process_msgs(self):
        while True:
            res = await self.read_next_msg()
            if res:
                cintamani_net = self.cintamani_net
                cmd = res.cmd
                payload = res.payload
                if cmd == 'ping':
                    msg = DashPongMsg(payload.nonce)
                    await self.send_msg('pong', msg.serialize())
                elif cmd == 'pong':
                    now = time.time()
                    if payload.nonce == self.ping_nonce:
                        self.ping_time = round((now - self.ping_start) * 1000)
                        self.ping_nonce = None
                        self.ping_start = None
                    else:
                        self.logger.info(f'pong with unknonw nonce')
                elif cmd == 'spork':
                    spork_msg = payload
                    spork_id = spork_msg.nSporkID
                    if not SporkID.has_value(spork_id):
                        self.logger.info(f'unknown spork id: {spork_id}')
                        continue

                    def verify_spork():
                        return self.verify_spork(spork_msg)
                    verify_ok = await self.loop.run_in_executor(None,
                                                                verify_spork)
                    if not verify_ok:
                        raise GracefulDisconnect('verify_spork failed')
                    sporks = cintamani_net.sporks
                    sporks.set_spork(spork_id, spork_msg.nValue, self.peer)
                    cintamani_net.set_spork_time = time.time()
                elif cmd == 'inv':
                    out_inventory = []
                    for di in payload.inventory:
                        inv_hash = di.hash
                        if self.mix_session:
                            if di.type == DashType.MSG_DSTX:
                                out_inventory.append(di)
                        elif di.type == DashType.MSG_ISLOCK:
                            recent_invs = cintamani_net.recent_islock_invs
                            if inv_hash not in recent_invs:
                                recent_invs.append(inv_hash)
                                out_inventory.append(di)
                    if out_inventory:
                        msg = DashGetDataMsg(out_inventory)
                        await self.send_msg('getdata', msg.serialize())
                elif cmd == 'addr':
                    addresses = [f'{a.ip}:{a.port}'
                                 for a in payload.addresses]
                    found_peers = self.cintamani_net.found_peers
                    found_peers = found_peers.union(addresses)
                elif cmd == 'mnlistdiff':
                    try:
                        self.mnlistdiffs.put_nowait(payload)
                    except asyncio.QueueFull:
                        self.logger.info('excess mnlistdiff msg')
                elif cmd == 'islock':
                    cintamani_net.append_to_recent_islocks(payload)
                elif cmd == 'dsq':
                    if self.mix_session:
                        if payload.fReady:  # session must ignore other dsq
                            if self.mix_session.verify_ds_msg_sig(payload):
                                await self.mix_session.msg_queue.put(res)
                            else:
                                exc = Exception(f'dsq vchSig verification'
                                                f' failed {res}')
                                await self.mix_session.msg_queue.put(exc)
                    else:
                        cintamani_net.add_recent_dsq(payload)
                elif cmd == 'dssu' and self.mix_session:
                    await self.mix_session.msg_queue.put(res)
                elif cmd == 'dsf' and self.mix_session:
                    await self.mix_session.msg_queue.put(res)
                elif cmd == 'dsc' and self.mix_session:
                    await self.mix_session.msg_queue.put(res)
            await asyncio.sleep(0.1)

    async def monitor_connection(self):
        net_timeout = self.cintamani_net.network.get_network_timeout_seconds()
        while True:
            await asyncio.sleep(1)
            if not self._is_open:
                raise GracefulDisconnect('peer session was closed')
            read_timeout = self.write_time - self.read_time
            if read_timeout > net_timeout:
                raise GracefulDisconnect('read timeout')

    def is_active(self, num_seconds=1):
        '''Peer is sending/receiving data last num_seconds'''
        now = time.time()
        return (now - self.read_time < num_seconds
                or now - self.write_time < num_seconds)

    async def process_ping(self):
        while True:
            while self.is_active():
                await asyncio.sleep(0.5)
            self.ping_nonce = random.getrandbits(64)
            msg = DashPingMsg(self.ping_nonce)
            msg_serialized = msg.serialize()
            self.ping_start = time.time()
            await self.send_msg('ping', msg_serialized)
            await asyncio.sleep(300)

    def close(self):
        if self._is_open:
            if self.sw:
                self.sw.close()
            if self.mix_session:
                self.mix_session.msg_queue.put_nowait(None)
            self._is_open = False
            # monitor_connection will cancel tasks

    def ban(self, ban_msg, ban_seconds=None):
        self.ban_msg = ban_msg
        ban_till = time.time() + ban_seconds if ban_seconds else None
        self.ban_till = ban_till
        till = '' if ban_till is None else ' (till %s)' % time.ctime(ban_till)
        self.logger.info(f'banned{till}: {ban_msg}')

    async def send_msg(self, cmd: str, payload: bytes=b''):
        cintamani_net = self.cintamani_net
        if self.debug or cintamani_net.debug:
            cintamani_cmd = DashCmd(cmd, payload)
            if payload:
                self.logger.info(f'--> {cintamani_cmd}')
            else:
                self.logger.info(f'--> {cintamani_cmd} (no payload)')
        cmd_len = len(cmd)
        if cmd_len > 12:
            raise Exception('command str to long')
        cmd_padding = b'\x00' * (12 - cmd_len)
        cmd = cmd.encode('ascii') + cmd_padding

        len_payload = len(payload)
        payload_size = pack('<I', len_payload)

        if len_payload > 0:
            checksum = sha256d(payload)[:4]
            msg = self.start_str + cmd + payload_size + checksum + payload
        else:
            msg = self.start_str + cmd + payload_size + EMPTY_PAYLOAD_CHECKSUM
        self.sw.write(msg)
        self.write_bytes += len(msg)
        cintamani_net.write_bytes += len(msg)
        self.write_time = cintamani_net.write_time = time.time()
        await self.sw.drain()

    async def send_version(self):
        version = DASH_PROTO_VERSION
        services = 0
        timestamp = int(time.time())
        recv_services = 1
        recv_ip = self.ip_addr
        recv_port = self.port
        trans_services = services
        trans_ip = LOCAL_IP_ADDR
        trans_port = self.default_port
        nonce = random.getrandbits(64)
        user_agent = '/Dash Electrum:%s/' % ELECTRUM_VERSION
        start_height = self.cintamani_net.network.get_local_height()
        relay = 0
        msg = DashVersionMsg(version, services, timestamp,
                             recv_services, recv_ip, recv_port,
                             trans_services, trans_ip, trans_port,
                             nonce, user_agent, start_height, relay,
                             None, None)
        await self.send_msg('version', msg.serialize())

    async def read_next_msg(self):
        start_str = None
        start_bytes_read = 0
        cintamani_net = self.cintamani_net
        while not start_str:
            try:
                start_str = await self.sr.readuntil(self.start_str)
                self.read_time = cintamani_net.read_time = time.time()
                len_start_str = len(start_str)
                self.read_bytes += len_start_str
                cintamani_net.read_bytes += len_start_str
                if len_start_str > 4:
                    self.logger.info(f'extra data before start'
                                     f' str: {len_start_str}')
            except asyncio.LimitOverrunError:
                self.logger.info('start str not found, read ahead')
                await self.sr.readexactly(READ_LIMIT)
                self.read_time = cintamani_net.read_time = time.time()
                self.read_bytes += READ_LIMIT
                cintamani_net.read_bytes += READ_LIMIT
                start_bytes_read += READ_LIMIT
                if start_bytes_read > PAYLOAD_LIMIT:
                    raise GracefulDisconnect(f'start str not found in '
                                             f'{start_bytes_read} bytes read')
            except asyncio.IncompleteReadError:
                if not self._is_open:
                    return
                raise GracefulDisconnect('start str not found '
                                         'in buffer, EOF found')

        try:
            res = None
            cmd = await self.sr.readexactly(12)
            cmd = cmd.strip(b'\x00').decode('ascii')
            payload_size = await self.sr.readexactly(4)
            payload_size = unpack('<I', payload_size)[0]
            if payload_size > PAYLOAD_LIMIT:
                raise GracefulDisconnect('incoming msg payload to large')
            checksum = await self.sr.readexactly(4)
            self.read_time = cintamani_net.read_time = time.time()
            self.read_bytes += 20
            cintamani_net.read_bytes += 20
            if payload_size == 0:
                if checksum != EMPTY_PAYLOAD_CHECKSUM:
                    self.logger.info(f'error reading msg {cmd}, '
                                     f'checksum mismatch')
                    return
                res = DashCmd(cmd)
                if self.debug or cintamani_net.debug:
                    self.logger.info(f'<-- {res} (no payload)')
                return res

            payload = await self.sr.readexactly(payload_size)
            self.read_time = cintamani_net.read_time = time.time()
            self.read_bytes += payload_size
            cintamani_net.read_bytes += payload_size
            calc_checksum = sha256d(payload)[:4]
            if checksum != calc_checksum:
                self.logger.info(f'error reading msg {cmd}, '
                                 f'checksum mismatch')
                return
            res = DashCmd(cmd, payload)
        except asyncio.IncompleteReadError:
            if not self._is_open:
                return
            raise GracefulDisconnect('error reading msg, EOF reached')
        except Exception as e:
            raise GracefulDisconnect(e) from e
        if self.debug or cintamani_net.debug:
            self.logger.info(f'<-- {res}')
        return res

    def verify_spork(self, spork_msg):
        if spork_msg.nTimeSigned > time.time() + 2 * 3600:
            self.logger.info('Spork signed to far in the future')
            return False

        new_sigs = self.cintamani_net.sporks.is_new_sigs()

        try:
            if self.verify_spork_sig(spork_msg, new_sigs):
                return True
        except Exception as e:
            self.logger.info(f'Spork verification error: {repr(e)}')

        try:  # Try another sig type
            if self.verify_spork_sig(spork_msg, not new_sigs):
                return True
        except Exception as e:
            self.logger.info(f'Spork verification error: {repr(e)}')

        self.logger.info('Spork address differs from hardcoded')
        return False

    def verify_spork_sig(self, spork_msg, new_sigs):
        sig = spork_msg.vchSig
        msg_hash = spork_msg.msg_hash(new_sigs)
        public_key, compressed = ECPubkey.from_signature65(sig, msg_hash)
        public_key.verify_message_hash(sig[1:], msg_hash)
        pubkey_bytes = public_key.get_public_key_bytes(compressed)
        spork_address = public_key_to_p2pkh(pubkey_bytes)
        if self.cintamani_net.spork_address == spork_address:
            return True
        else:
            return False

    async def getmnlistd(self, base_height, height):
        base_block_hash = await self.cintamani_net.get_hash(base_height)
        block_hash = await self.cintamani_net.get_hash(height)
        msg = DashGetMNListDMsg(base_block_hash, block_hash)
        if not self.mnlistdiffs.empty():
            self.logger.info('unasked mnlistdiff msg')
            self.mnlistdiffs.get_nowait()
        await self.send_msg('getmnlistd', msg.serialize())
        return await asyncio.wait_for(self.mnlistdiffs.get(), timeout=30)
