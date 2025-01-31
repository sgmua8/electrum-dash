import asyncio
from pprint import pprint

from electrum_cintamani import transaction
from electrum_cintamani.cintamani_tx import DashTxError, TxOutPoint, ProTxBase
from electrum_cintamani.cintamani_tx import (SPEC_PRO_REG_TX, SPEC_PRO_UP_SERV_TX,
                                   SPEC_PRO_UP_REG_TX, SPEC_PRO_UP_REV_TX,
                                   SPEC_CB_TX, SPEC_SUB_TX_REGISTER,
                                   SPEC_SUB_TX_TOPUP, SPEC_SUB_TX_RESET_KEY,
                                   SPEC_SUB_TX_CLOSE_ACCOUNT)
from electrum_cintamani.transaction import BCDataStream
from electrum_cintamani.util import bfh, bh2u, create_and_start_event_loop
from electrum_cintamani.commands import Commands

from . import SequentialTestCase


V2_TX = (
    '020000000192809f0b234cb850d71d020e678e93f074648ed0df5affd0c46d3bcb177f'
    '9ccf020000008b483045022100c5403bcf86c3ae7b8fd4ca0d1e4df6729cc1af05ff95'
    'd9726b43a64b41dd5d9902207fab615f41871885aa3062fc7d8f8d9d3dcbc2e4867c5d'
    '96dd7a176b99e927924141040baa4271a82c5f1a09a5ea63d763697ca0545b6049c4dd'
    '8e8d099dd91f2da10eb11e829000a82047ac56969fb582433067a21c3171e569d1832c'
    '34fdd793cfc8ffffffff030000000000000000226a20195ce612d20e5284eb78bb28c9'
    'c50d6139b10b77b2d5b2f94711b13162700472bfc53000000000001976a9144a519c63'
    'f985ba5ab8b71bb42f1ecb82a0a0d80788acf6984315000000001976a9148b80536aa3'
    'c460258cda834b86a46787c9a2b0bf88ac00000000')


CB_TX = (
    '0300050001000000000000000000000000000000000000000000000000000000000000'
    '0000ffffffff1303c407040e2f5032506f6f6c2d74444153482fffffffff0448d6a73d'
    '000000001976a914293859173a34194d445c2962b97383e2a93d7cb288ac22fc433e00'
    '0000001976a914bf09c602c6b8f1db246aba5c37ad1cfdcb16b15e88ace9259c000000'
    '00004341047559d13c3f81b1fadbd8dd03e4b5a1c73b05e2b980e00d467aa9440b29c7'
    'de23664dde6428d75cafed22ae4f0d302e26c5c5a5dd4d3e1b796d7281bdc9430f35ac'
    '00000000000000002a6a28be61411c3c79b7fd45923118ba74d340afb248ae2edafe78'
    'c15e2d1aa337c942000000000000000000000000260100c407040076629a6e42fb5191'
    '88f65889fd3ac0201be87aa227462b5643e8bb2ec1d7a82a')


CB_TX_D = {
    'height': 264132,
    'merkleRootMNList': '76629a6e42fb519188f65889fd3ac020'
                        '1be87aa227462b5643e8bb2ec1d7a82a',
    'merkleRootQuorums': '',
    'version': 1}


CB_TX_V2 = (
    '0300050001000000000000000000000000000000000000000000000000000000000000'
    '0000ffffffff1303c407040e2f5032506f6f6c2d74444153482fffffffff0448d6a73d'
    '000000001976a914293859173a34194d445c2962b97383e2a93d7cb288ac22fc433e00'
    '0000001976a914bf09c602c6b8f1db246aba5c37ad1cfdcb16b15e88ace9259c000000'
    '00004341047559d13c3f81b1fadbd8dd03e4b5a1c73b05e2b980e00d467aa9440b29c7'
    'de23664dde6428d75cafed22ae4f0d302e26c5c5a5dd4d3e1b796d7281bdc9430f35ac'
    '00000000000000002a6a28be61411c3c79b7fd45923118ba74d340afb248ae2edafe78'
    'c15e2d1aa337c942000000000000000000000000460200c407040076629a6e42fb5191'
    '88f65889fd3ac0201be87aa227462b5643e8bb2ec1d7a82a76629a6e42fb519188f658'
    '89fd3ac0201be87aa227462b5643e8bb2ec1d7a82a')


CB_TX_V2_D = {
    'height': 264132,
    'merkleRootMNList': ('76629a6e42fb519188f65889fd3ac0201be87aa2'
                         '27462b5643e8bb2ec1d7a82a'),
    'merkleRootQuorums': ('76629a6e42fb519188f65889fd3ac0201be87aa'
                          '227462b5643e8bb2ec1d7a82a'),
    'version': 2}


PRO_REG_TX = (
    '030001000335f1c2ca44a1eb72e59f589df2852caacba39b7c0a5e61967f6b71d7a763'
    '3153000000006b483045022100b2d457bbe855abc365a7db9c8014ea106fdb6dae6327'
    '927fe81dfbdecf032b260220262e7e6c28899cd741db55c2e2ec35ed849cf99e78e36a'
    '70c2ec3dac3c2ef60a012102500859b69a4cad6cfe4cf6b606be25b367c562b3be9a24'
    'b06d60c7047ee18fa2feffffff473ac70b52b2260aa0e4bec818c5a8c71d37a1b17430'
    '75823c8e572ad71938b0000000006b483045022100fa4d57cdeb61f8ff1298fdc40256'
    'c68dfce320d44f584494c0a53233ddbe30a702206a50aaa245a6097d06c790fb1d7a37'
    'ced1622299c0aa93ebc018f1590d0eb15c012103f273126b24f755ab7e41311d03d545'
    '590c162ea179421c5e18271c57de1a1635feffffff4de1afa0a321bc88c34978d4eeba'
    '739256b86f8d8cdf47651b6f60e451f0a3de000000006a47304402202c4c5c48ac1d37'
    '9f6da8143664072d6545d64691ce4738e026adf80c9afab24f022053804b4166a342da'
    '38c538757680bebdc7785ce8c18a817fb3014fdaeec6d3bb0121028e99f6bc86489a43'
    'f953b2f0b046666efd7f7ad44da30f62ed5d32921556f8c5feffffff01c7430f000000'
    '00001976a914c1de5f0587dc39112a28644904b0f3ed3298a6ed88ac00000000fd1201'
    '0100000000004de1afa0a321bc88c34978d4eeba739256b86f8d8cdf47651b6f60e451'
    'f0a3de0100000000000000000000000000ffff12ca34aa752f2b3edeed6842db1f59cf'
    '35de1ab5721094f049d000ab986c589053b3f3bd720724e75e18581afdca54bce80d14'
    '750b1bcf9202158fe6c596ce8391815265747bd4a2009e2b3edeed6842db1f59cf35de'
    '1ab5721094f049d000001976a9149bf5948b901a1e3e54e42c6e10496a17cd4067e088'
    'ac54d046585434668b4ee664c597864248b8a6aac33a7b2f4fcd1cc1b5da474a8a411f'
    'c1617ae83406c92a9132f14f9fff1487f2890f401e776fdddd639bc5055c456268cf74'
    '97400d3196109c8cd31b94732caf6937d63de81d9a5be4db5beb83f9aa')


PRO_REG_TX_D = {
    'KeyIdOwner': '2b3edeed6842db1f59cf35de1ab5721094f049d0',
    'KeyIdVoting': '2b3edeed6842db1f59cf35de1ab5721094f049d0',
    'PubKeyOperator': '00ab986c589053b3f3bd720724e75e18'
                      '581afdca54bce80d14750b1bcf920215'
                      '8fe6c596ce8391815265747bd4a2009e',
    'collateralOutpoint': {
        'hash': 'dea3f051e4606f1b6547df8c8d6fb856'
                '9273baeed47849c388bc21a3a0afe14d',
        'index': 1},
    'inputsHash': '54d046585434668b4ee664c597864248'
                  'b8a6aac33a7b2f4fcd1cc1b5da474a8a',
    'ipAddress': '18.202.52.170',
    'mode': 0,
    'operatorReward': 0,
    'payloadSig': '1fc1617ae83406c92a9132f14f9fff1487f2890f401e776f'
                  'dddd639bc5055c456268cf7497400d3196109c8cd31b9473'
                  '2caf6937d63de81d9a5be4db5beb83f9aa',
    'port': 29999,
    'scriptPayout': '76a9149bf5948b901a1e3e54e42c6e10496a17cd4067e088ac',
    'type': 0,
    'version': 1}


PRO_UP_SERV_TX = (
    '03000200010931c6b0ad7ce07f3c8aefeeb78e246a4fe6872bbf08ab6e4eb6a7b69acd'
    '64a6010000006b483045022100a2feb698c43c752738fabea281b7e9e5a3aa648a4c54'
    '1171e06d7c372db92c65022061c1ec3c92f2e76bb7fb1b548d854f19a41e6421267231'
    '74150412caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b'
    '3d0103f761cc69a211feffffff0189fa433e000000001976a914551ab8ca96a9142217'
    '4d22769c3a4f90b2dcd0de88ac00000000ce01003c6dca244f49f19d3f09889753ffff'
    '1fec5bb8f9f5bd5bc09dabd999da21198f00000000000000000000ffff5fb735802711'
    '1976a91421851058431a7d722e8e8dd9509e7f2b8e7042ec88acefcfe3d578914bb48c'
    '6bd71b3459d384e4237446d521c9e2c6b6fcf019b5aafc99443fe14f644cfa47086e88'
    '97cf7b546a67723d4a8ec5353a82f962a96ec3cea328343b647aace2897d6eddd0b8c8'
    'ee0f2e56f6733aed2e9f0006caafa6fc21c18a013c619d6e37af8d2f0985e3b769abc3'
    '8ffa60e46c365a38d9fa0d44fd62')


PRO_UP_SERV_TX_D = {
    'inputsHash': 'efcfe3d578914bb48c6bd71b3459d384'
                  'e4237446d521c9e2c6b6fcf019b5aafc',
    'ipAddress': '95.183.53.128',
    'payloadSig': '99443fe14f644cfa47086e8897cf7b546a67723d4a8ec5353a'
                  '82f962a96ec3cea328343b647aace2897d6eddd0b8c8ee0f2e'
                  '56f6733aed2e9f0006caafa6fc21c18a013c619d6e37af8d2f'
                  '0985e3b769abc38ffa60e46c365a38d9fa0d44fd62',
    'port': 10001,
    'proTxHash': '3c6dca244f49f19d3f09889753ffff1f'
                 'ec5bb8f9f5bd5bc09dabd999da21198f',
    'scriptOperatorPayout': '76a91421851058431a7d722e8'
                            'e8dd9509e7f2b8e7042ec88ac',
    'version': 1}


PRO_UP_REG_TX = (
    '0300030001f8f9a27ca1c727fb971d45983c9a08a0bbd76753f8eb7913130c72d94218'
    '8d32000000006a47304402205d530dc4e9e34b44fdf58f06fff0c225d80490be2861ad'
    '7fe5fed7e62b48053b022052a78b5beaccc468b7fdb80e47090cb54c351aa9aa82fa7e'
    '9b15b82d53b5f15a0121028106cde1660d2bfcc11231dfb1a05b60ded262d59e5e021a'
    'a3a814234013f4e9feffffff01c60c0000000000001976a91452a23d803da188cca952'
    'f9b7bc94c47c6fd1468a88ac00000000e40100aeb817f94b8e699b58130a53d2fbe98d'
    '5519c2abe3b15e6f36c9abeb32e4dcce00001061eb559a64427ad239830742ef59591c'
    'dbbdffda7d3f5e7a2d95b9607ad80e389191e44c59ea5987b85e6d0e3eb527b9e198fa'
    '7a745913c9278ec993d4472a95dac4251976a914eebbacffff3a55437803e0efb68a7d'
    '591e0409d188ac0eb0067e6ccdd2acb96e7279113702218f3f0ab6f2287e14c11c5be6'
    'f2051d5a4120cb00124d838b02207097048cb668244cd79df825eb2d4d211fd2c4604c'
    '18b30e1ae9bb654787144d16856676efff180889f05b5c9121a483b4ae3f0ea0ff3faf')


PRO_UP_REG_TX_D = {
    'KeyIdVoting': 'b9e198fa7a745913c9278ec993d4472a95dac425',
    'PubKeyOperator': '1061eb559a64427ad239830742ef59591cdbbdffda7d3f'
                      '5e7a2d95b9607ad80e389191e44c59ea5987b85e6d0e3eb527',
    'inputsHash': '0eb0067e6ccdd2acb96e727911370221'
                  '8f3f0ab6f2287e14c11c5be6f2051d5a',
    'mode': 0,
    'payloadSig': '20cb00124d838b02207097048cb668244cd79df825eb2d4d21'
                  '1fd2c4604c18b30e1ae9bb654787144d16856676efff180889'
                  'f05b5c9121a483b4ae3f0ea0ff3faf',
    'proTxHash': 'aeb817f94b8e699b58130a53d2fbe98d'
                 '5519c2abe3b15e6f36c9abeb32e4dcce',
    'scriptPayout': '76a914eebbacffff3a55437803e0efb68a7d591e0409d188ac',
    'version': 1}


PRO_UP_REV_TX = (
    '030004000100366cd80169116da28e387413e8e3660a7aedd65002b320d0bd165eea8e'
    'ba52000000006a4730440220043a639f4554842f38253c75d066e70098ef02b141d5ff'
    'dea9fc408d307fce1202205d5d779f416fbc431847d19d83ae90c4036cf9925d3c4852'
    'cdd5df25d5843a48012102688d37c6d08a236d7952cdbc310dcb344ddae8b02e028720'
    '1e79fd774509e8abfeffffff01570b0000000000001976a91490c5ce9d8bfefe3526d8'
    '538cd0ed5e5d472c992a88ac00000000a40100b67ffbbd095de31ea38446754b6bf251'
    '287936d2881d58b7c4efae0b54c75e9f0000eb073521b60306717f1d4feb3e9022f886'
    'b97bf981137684716a7d3d7e45b7fe83f4bb5530f7c5954e8b1ad50a74a9e1d65dcdcb'
    'e4acb8cbe3671abc7911e8c3954856c4da7e5fd242f2e4f5546f08d90849245bc593d1'
    '605654e1a99cd0a79e9729799742c48d4920044666ad25a85fd093559c43e4900e634c'
    '371b9b8d89ba')


PRO_UP_REV_TX_D = {
    'inputsHash': 'eb073521b60306717f1d4feb3e9022f8'
                  '86b97bf981137684716a7d3d7e45b7fe',
    'payloadSig': '83f4bb5530f7c5954e8b1ad50a74a9e1d65dcdcbe4acb8cbe3'
                  '671abc7911e8c3954856c4da7e5fd242f2e4f5546f08d90849'
                  '245bc593d1605654e1a99cd0a79e9729799742c48d49200446'
                  '66ad25a85fd093559c43e4900e634c371b9b8d89ba',
    'proTxHash': 'b67ffbbd095de31ea38446754b6bf251'
                 '287936d2881d58b7c4efae0b54c75e9f',
    'reason': 0,
    'version': 1}


SUB_TX_REGISTER = (
    '03000800010931c6b0ad7ce07f3c8aefeeb78e246a4fe6872bbf08ab6e4eb6a7b69acd'
    '64a6010000006b483045022100a2feb698c43c752738fabea281b7e9e5a3aa648a4c54'
    '1171e06d7c372db92c65022061c1ec3c92f2e76bb7fb1b548d854f19a41e6421267231'
    '74150412caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b'
    '3d0103f761cc69a211feffffff0189fa433e000000001976a914551ab8ca96a9142217'
    '4d22769c3a4f90b2dcd0de88ac00000000960100036162638e7042ec88acefcfe3d578'
    '914bb48c6bd71b3459d384e42374e8abfeffffff01570b0000000000001976a91490c5'
    'ce9d8bc992a88ac00000000a40100b67ffbbd095de31ea38446754e8abfeffffff0157'
    '0b0000000000001976a91490c5ce9d8bc992a88ac00000000a40100b67ffbbd095de31'
    'ea38446754e8abfeffffff01570b0000000000001976a91490c5ce9d')


SUB_TX_REGISTER_D = {
    'payloadSig': '8bc992a88ac00000000a40100b67ffbbd095de31ea38446754'
                  'e8abfeffffff01570b0000000000001976a91490c5ce9d8bc9'
                  '92a88ac00000000a40100b67ffbbd095de31ea38446754e8ab'
                  'feffffff01570b0000000000001976a91490c5ce9d',
    'pubKey': '8e7042ec88acefcfe3d578914bb48c6bd71b3459d384e42374'
              'e8abfeffffff01570b0000000000001976a91490c5ce9d',
    'userName': 'abc',
    'version': 1}


SUB_TX_TOPUP = (
    '03000900010931c6b0ad7ce07f3c8aefeeb78e246a4fe6872bbf08ab6e4eb6a7b69acd'
    '64a6010000006b483045022100a2feb698c43c752738fabea281b7e9e5a3aa648a4c54'
    '1171e06d7c372db92c65022061c1ec3c92f2e76bb7fb1b548d854f19a41e6421267231'
    '74150412caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b'
    '3d0103f761cc69a211feffffff0189fa433e000000001976a914551ab8ca96a9142217'
    '4d22769c3a4f90b2dcd0de88ac00000000220100d384e42374e8abfeffffff01570b00'
    '0000a40100b67ffbbd095de31ea3844675')


SUB_TX_TOPUP_D = {
    'regTxHash': 'd384e42374e8abfeffffff01570b0000'
                 '00a40100b67ffbbd095de31ea3844675',
    'version': 1}


SUB_TX_RESET_KEY = (
    '03000a00010931c6b0ad7ce07f3c8aefeeb78e246a4fe6872bbf08ab6e4eb6a7b69acd'
    '64a6010000006b483045022100a2feb698c43c752738fabea281b7e9e5a3aa648a4c54'
    '1171e06d7c372db92c65022061c1ec3c92f2e76bb7fb1b548d854f19a41e6421267231'
    '74150412caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b'
    '3d0103f761cc69a211feffffff0189fa433e000000001976a914551ab8ca96a9142217'
    '4d22769c3a4f90b2dcd0de88ac00000000da0100d384e42374e8abfeffffff01570b00'
    '0000a40100b67ffbbd095de31ea3844675af3e98e9601210293360bf2a2e810673412b'
    'c6e8e0e358f3fb7bdbe9a667b3d0e803000000000000601210293360bf2a2e81067341'
    '2bc6e8e0e358f3fb7bdbe9a667b3d0103f761caf3e98e9601210293360bf2a2e810673'
    '412bc6e8e0e358f3fb7bdbe9a667b3d0103f761caf3e98e9601210293360bf2a2e8106'
    '73412bc6e8e0e358f3fb7bdbe9a667b3d0103f761caf3e98e9601210293360bf2a2e81'
    '0673412bc6e8e0e358f3fb7bdbe9a667b3d0103f761cabcdefab')


SUB_TX_RESET_KEY_D = {
    'creditFee': 1000,
    'hashPrevSubTx': 'af3e98e9601210293360bf2a2e810673'
                     '412bc6e8e0e358f3fb7bdbe9a667b3d0',
    'newPubKey': '601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9'
                 'a667b3d0103f761caf3e98e9601210293360bf2a2e810673',
    'payloadSig': '412bc6e8e0e358f3fb7bdbe9a667b3d0103f761caf3e98e96012102'
                  '93360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b3d0103f76'
                  '1caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bd'
                  'be9a667b3d0103f761cabcdefab',
    'regTxHash': 'd384e42374e8abfeffffff01570b0000'
                 '00a40100b67ffbbd095de31ea3844675',
    'version': 1}


SUB_TX_CLOSE_ACCOUNT = (
    '03000b00010931c6b0ad7ce07f3c8aefeeb78e246a4fe6872bbf08ab6e4eb6a7b69acd'
    '64a6010000006b483045022100a2feb698c43c752738fabea281b7e9e5a3aa648a4c54'
    '1171e06d7c372db92c65022061c1ec3c92f2e76bb7fb1b548d854f19a41e6421267231'
    '74150412caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b'
    '3d0103f761cc69a211feffffff0189fa433e000000001976a914551ab8ca96a9142217'
    '4d22769c3a4f90b2dcd0de88ac00000000aa0100d384e42374e8abfeffffff01570b00'
    '0000a40100b67ffbbd095de31ea3844675af3e98e9601210293360bf2a2e810673412b'
    'c6e8e0e358f3fb7bdbe9a12bc6e8e803000000000000a62bc6e8e0e358f3fb7bdbe9a6'
    '67b3d0103f761caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9'
    'a667b3d0103f761caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdb'
    'e9a667b3d0103f761cabcdefab')


SUB_TX_CLOSE_ACCOUNT_D = {
    'creditFee': 1000,
    'hashPrevSubTx': 'af3e98e9601210293360bf2a2e810673'
                     '412bc6e8e0e358f3fb7bdbe9a12bc6e8',
    'payloadSig': 'a62bc6e8e0e358f3fb7bdbe9a667b3d0103f761caf3e98e9601210293'
                  '360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b3d0103f761caf'
                  '3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a66'
                  '7b3d0103f761cabcdefab',
    'regTxHash': 'd384e42374e8abfeffffff01570b0000'
                 '00a40100b67ffbbd095de31ea3844675',
    'version': 1}


UNKNOWN_SPEC_TX = (
    '0300bb00010931c6b0ad7ce07f3c8aefeeb78e246a4fe6872bbf08ab6e4eb6a7b69acd'
    '64a6010000006b483045022100a2feb698c43c752738fabea281b7e9e5a3aa648a4c54'
    '1171e06d7c372db92c65022061c1ec3c92f2e76bb7fb1b548d854f19a41e6421267231'
    '74150412caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b'
    '3d0103f761cc69a211feffffff0189fa433e000000001976a914551ab8ca96a9142217'
    '4d22769c3a4f90b2dcd0de88ac00000000aa0100d384e42374e8abfeffffff01570b00'
    '0000a40100b67ffbbd095de31ea3844675af3e98e9601210293360bf2a2e810673412b'
    'c6e8e0e358f3fb7bdbe9a12bc6e8e0e358f3fb7bdbe9a62bc6e8e0e358f3fb7bdbe9a6'
    '67b3d0103f761caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9'
    'a667b3d0103f761caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdb'
    'e9a667b3d0103f761cabcdefab')


WRONG_SPEC_TX = (  # Tx version < 3
    '0200bb00010931c6b0ad7ce07f3c8aefeeb78e246a4fe6872bbf08ab6e4eb6a7b69acd'
    '64a6010000006b483045022100a2feb698c43c752738fabea281b7e9e5a3aa648a4c54'
    '1171e06d7c372db92c65022061c1ec3c92f2e76bb7fb1b548d854f19a41e6421267231'
    '74150412caf3e98e9601210293360bf2a2e810673412bc6e8e0e358f3fb7bdbe9a667b'
    '3d0103f761cc69a211feffffff0189fa433e000000001976a914551ab8ca96a9142217'
    '4d22769c3a4f90b2dcd0de88ac00000000')


TEST_HASH = 'a7b64e6eab08bf2b87e64f6a248eb7eeef8a3c7fe07cadb0c631090100bb0002'


class TestDashTx(SequentialTestCase):

    def test_tx_outpoint(self):
        # test normal outpoint
        o = TxOutPoint(bfh(TEST_HASH)[::-1], 1)
        assert o.is_null == False
        assert o.hash_is_null == False
        assert str(o) == TEST_HASH + ':1'
        ser = o.serialize()
        assert bh2u(ser) == bh2u(bfh(TEST_HASH)[::-1]) + '01000000'
        s = BCDataStream()
        s.write(ser)
        o2 = TxOutPoint.read_vds(s)
        assert str(o2) == str(o)

        # test null outpoint
        o = TxOutPoint(b'\x00'*32, -1)
        assert o.is_null == True
        assert o.hash_is_null == True
        assert str(o) == '0'*64 + ':-1'
        ser = o.serialize()
        assert bh2u(ser) == '0'*64 + 'f'*8
        s = BCDataStream()
        s.write(ser)
        o2 = TxOutPoint.read_vds(s)
        assert str(o2) == str(o)

        # test null hash
        o = TxOutPoint(b'\x00'*32, 0)
        assert o.is_null == False
        assert o.hash_is_null == True
        assert str(o) == '0'*64 + ':0'
        ser = o.serialize()
        assert bh2u(ser) == '0'*64 + '00000000'
        s = BCDataStream()
        s.write(ser)
        o2 = TxOutPoint.read_vds(s)
        assert str(o2) == str(o)


class TestDashSpecTxSerialization(SequentialTestCase):

    def setUp(self):
        super().setUp()
        self.asyncio_loop, self._stop_loop, self._loop_thread = create_and_start_event_loop()

    def tearDown(self):
        super().tearDown()
        self.asyncio_loop.call_soon_threadsafe(self._stop_loop.set_result, 1)
        self._loop_thread.join(timeout=1)

    def test_cintamani_tx_v2(self):
        tx = transaction.Transaction(V2_TX)
        deser = tx.to_json()
        assert deser['version'] == 2
        assert deser['tx_type'] == 0
        assert deser['extra_payload'] == ''
        assert tx.extra_payload == b''
        ser = tx.serialize()
        assert ser == V2_TX

    def test_cintamani_tx_cb_tx(self):
        tx = transaction.Transaction(CB_TX)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 5
        extra_dict = deser['extra_payload']
        assert extra_dict == CB_TX_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == CB_TX_D['version']
        assert extra.height == CB_TX_D['height']
        assert len(extra.merkleRootMNList) == 32
        assert extra.merkleRootMNList == bfh(CB_TX_D['merkleRootMNList'])
        ser = tx.serialize()
        assert ser == CB_TX

        assert extra.to_hex_str() == CB_TX[532:]
        extra2 = ProTxBase.from_hex_str(SPEC_CB_TX, CB_TX[532:])
        assert extra2.version == extra.version
        assert extra2.height == extra.height
        assert extra2.merkleRootMNList == extra.merkleRootMNList

    def test_cintamani_tx_cb_tx_v2(self):
        tx = transaction.Transaction(CB_TX_V2)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 5
        extra_dict = deser['extra_payload']
        assert extra_dict == CB_TX_V2_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == CB_TX_V2_D['version']
        assert extra.height == CB_TX_V2_D['height']
        assert len(extra.merkleRootMNList) == 32
        assert extra.merkleRootMNList == bfh(CB_TX_V2_D['merkleRootMNList'])
        assert len(extra.merkleRootQuorums) == 32
        assert extra.merkleRootQuorums == bfh(CB_TX_V2_D['merkleRootQuorums'])
        ser = tx.serialize()
        assert ser == CB_TX_V2

        assert extra.to_hex_str() == CB_TX_V2[532:]
        extra2 = ProTxBase.from_hex_str(SPEC_CB_TX, CB_TX_V2[532:])
        assert extra2.version == extra.version
        assert extra2.height == extra.height
        assert extra2.merkleRootMNList == extra.merkleRootMNList

    def test_cintamani_tx_pro_reg_tx(self):
        tx = transaction.Transaction(PRO_REG_TX)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 1
        extra_dict = deser['extra_payload']
        assert extra_dict == PRO_REG_TX_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == PRO_REG_TX_D['version']
        assert extra.type == PRO_REG_TX_D['type']
        assert extra.mode == PRO_REG_TX_D['mode']
        assert len(extra.collateralOutpoint.hash) == 32
        assert extra.collateralOutpoint.hash == \
            bfh(PRO_REG_TX_D['collateralOutpoint']['hash'])[::-1]
        assert extra.collateralOutpoint.index == \
            PRO_REG_TX_D['collateralOutpoint']['index']
        assert extra.ipAddress == PRO_REG_TX_D['ipAddress']
        assert extra.port == PRO_REG_TX_D['port']
        assert len(extra.KeyIdOwner) == 20
        assert extra.KeyIdOwner == bfh(PRO_REG_TX_D['KeyIdOwner'])
        assert len(extra.PubKeyOperator) == 48
        assert extra.PubKeyOperator == bfh(PRO_REG_TX_D['PubKeyOperator'])
        assert len(extra.KeyIdVoting) == 20
        assert extra.KeyIdVoting == bfh(PRO_REG_TX_D['KeyIdVoting'])
        assert extra.operatorReward == PRO_REG_TX_D['operatorReward']
        assert extra.scriptPayout == bfh(PRO_REG_TX_D['scriptPayout'])
        assert len(extra.inputsHash) == 32
        assert extra.inputsHash == bfh(PRO_REG_TX_D['inputsHash'])
        assert extra.payloadSig == bfh(PRO_REG_TX_D['payloadSig'])
        ser = tx.serialize()
        assert ser == PRO_REG_TX

        assert extra.to_hex_str() == PRO_REG_TX[980:]
        extra2 = ProTxBase.from_hex_str(SPEC_PRO_REG_TX, PRO_REG_TX[980:])
        assert extra2.version == extra.version
        assert extra2.type == extra.type
        assert extra2.mode == extra.mode
        assert extra2.collateralOutpoint.hash == extra.collateralOutpoint.hash
        assert extra2.collateralOutpoint.index == \
            extra.collateralOutpoint.index
        assert extra2.ipAddress == extra.ipAddress
        assert extra2.port == extra.port
        assert extra2.KeyIdOwner == extra.KeyIdOwner
        assert extra2.PubKeyOperator == extra.PubKeyOperator
        assert extra2.KeyIdVoting == extra.KeyIdVoting
        assert extra2.operatorReward == extra.operatorReward
        assert extra2.scriptPayout == extra.scriptPayout
        assert extra2.inputsHash == extra.inputsHash
        assert extra2.payloadSig == extra.payloadSig

    def test_cintamani_tx_pro_up_serv_tx(self):
        tx = transaction.Transaction(PRO_UP_SERV_TX)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 2
        extra_dict = deser['extra_payload']
        assert extra_dict == PRO_UP_SERV_TX_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == PRO_UP_SERV_TX_D['version']
        assert len(extra.proTxHash) == 32
        assert extra.proTxHash == bfh(PRO_UP_SERV_TX_D['proTxHash'])
        assert extra.ipAddress == PRO_UP_SERV_TX_D['ipAddress']
        assert extra.port == PRO_UP_SERV_TX_D['port']
        assert extra.scriptOperatorPayout == \
            bfh(PRO_UP_SERV_TX_D['scriptOperatorPayout'])
        assert len(extra.inputsHash) == 32
        assert extra.inputsHash == bfh(PRO_UP_SERV_TX_D['inputsHash'])
        assert len(extra.payloadSig) == 96
        assert extra.payloadSig == bfh(PRO_UP_SERV_TX_D['payloadSig'])
        ser = tx.serialize()
        assert ser == PRO_UP_SERV_TX

        assert extra.to_hex_str() == PRO_UP_SERV_TX[386:]
        extra2 = ProTxBase.from_hex_str(SPEC_PRO_UP_SERV_TX,
                                        PRO_UP_SERV_TX[386:])
        assert extra2.version == extra.version
        assert extra2.proTxHash == extra.proTxHash
        assert extra2.ipAddress == extra.ipAddress
        assert extra2.port == extra.port
        assert extra2.scriptOperatorPayout == extra.scriptOperatorPayout
        assert extra2.inputsHash == extra.inputsHash
        assert extra2.payloadSig == extra.payloadSig

    def test_cintamani_tx_pro_up_reg_tx(self):
        tx = transaction.Transaction(PRO_UP_REG_TX)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 3
        extra_dict = deser['extra_payload']
        assert extra_dict == PRO_UP_REG_TX_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == PRO_UP_REG_TX_D['version']
        assert extra.proTxHash == bfh(PRO_UP_REG_TX_D['proTxHash'])
        assert extra.mode == PRO_UP_REG_TX_D['mode']
        assert len(extra.PubKeyOperator) == 48
        assert extra.PubKeyOperator == bfh(PRO_UP_REG_TX_D['PubKeyOperator'])
        assert len(extra.KeyIdVoting) == 20
        assert extra.KeyIdVoting == bfh(PRO_UP_REG_TX_D['KeyIdVoting'])
        assert extra.scriptPayout == bfh(PRO_UP_REG_TX_D['scriptPayout'])
        assert len(extra.inputsHash) == 32
        assert extra.inputsHash == bfh(PRO_UP_REG_TX_D['inputsHash'])
        assert extra.payloadSig == bfh(PRO_UP_REG_TX_D['payloadSig'])
        ser = tx.serialize()
        assert ser == PRO_UP_REG_TX

        assert extra.to_hex_str() == PRO_UP_REG_TX[384:]
        extra2 = ProTxBase.from_hex_str(SPEC_PRO_UP_REG_TX,
                                        PRO_UP_REG_TX[384:])
        assert extra2.version == extra.version
        assert extra2.proTxHash == extra.proTxHash
        assert extra2.mode == extra.mode
        assert extra2.PubKeyOperator == extra.PubKeyOperator
        assert extra2.KeyIdVoting == extra.KeyIdVoting
        assert extra2.scriptPayout == extra.scriptPayout
        assert extra2.inputsHash == extra.inputsHash
        assert extra2.payloadSig == extra.payloadSig

    def test_cintamani_tx_pro_up_rev_tx(self):
        tx = transaction.Transaction(PRO_UP_REV_TX)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 4
        extra_dict = deser['extra_payload']
        assert extra_dict == PRO_UP_REV_TX_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == PRO_UP_REV_TX_D['version']
        assert len(extra.proTxHash) == 32
        assert extra.proTxHash == bfh(PRO_UP_REV_TX_D['proTxHash'])
        assert extra.reason == PRO_UP_REV_TX_D['reason']
        assert len(extra.inputsHash) == 32
        assert extra.inputsHash == bfh(PRO_UP_REV_TX_D['inputsHash'])
        assert len(extra.payloadSig) == 96
        assert extra.payloadSig == bfh(PRO_UP_REV_TX_D['payloadSig'])
        ser = tx.serialize()
        assert ser == PRO_UP_REV_TX

        assert extra.to_hex_str() == PRO_UP_REV_TX[384:]
        extra2 = ProTxBase.from_hex_str(SPEC_PRO_UP_REV_TX,
                                        PRO_UP_REV_TX[384:])
        assert extra2.version == extra.version
        assert extra2.proTxHash == extra.proTxHash
        assert extra2.reason == extra.reason
        assert extra2.inputsHash == extra.inputsHash
        assert extra2.payloadSig == extra.payloadSig

    def test_cintamani_tx_sub_tx_register(self):
        tx = transaction.Transaction(SUB_TX_REGISTER)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 8
        extra_dict = deser['extra_payload']
        assert extra_dict == SUB_TX_REGISTER_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == SUB_TX_REGISTER_D['version']
        assert extra.userName == SUB_TX_REGISTER_D['userName']
        assert len(extra.pubKey) == 48
        assert extra.pubKey == bfh(SUB_TX_REGISTER_D['pubKey'])
        assert len(extra.payloadSig) == 96
        assert extra.payloadSig == bfh(SUB_TX_REGISTER_D['payloadSig'])
        ser = tx.serialize()
        assert ser == SUB_TX_REGISTER

        assert extra.to_hex_str() == SUB_TX_REGISTER[386:]
        extra2 = ProTxBase.from_hex_str(SPEC_SUB_TX_REGISTER,
                                        SUB_TX_REGISTER[386:])
        assert extra2.version == extra.version
        assert extra2.userName == extra.userName
        assert extra2.pubKey == extra.pubKey
        assert extra2.payloadSig == extra.payloadSig

    def test_cintamani_tx_sub_tx_topup(self):
        tx = transaction.Transaction(SUB_TX_TOPUP)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 9
        extra_dict = deser['extra_payload']
        assert extra_dict == SUB_TX_TOPUP_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == SUB_TX_TOPUP_D['version']
        assert len(extra.regTxHash) == 32
        assert extra.regTxHash == bfh(SUB_TX_TOPUP_D['regTxHash'])
        ser = tx.serialize()
        assert ser == SUB_TX_TOPUP

        assert extra.to_hex_str() == SUB_TX_TOPUP[386:]
        extra2 = ProTxBase.from_hex_str(SPEC_SUB_TX_TOPUP,
                                        SUB_TX_TOPUP[386:])
        assert extra2.version == extra.version
        assert extra2.regTxHash == extra.regTxHash

    def test_cintamani_tx_sub_tx_reset_key(self):
        tx = transaction.Transaction(SUB_TX_RESET_KEY)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 10
        extra_dict = deser['extra_payload']
        assert extra_dict == SUB_TX_RESET_KEY_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == SUB_TX_RESET_KEY_D['version']
        assert len(extra.regTxHash) == 32
        assert extra.regTxHash == bfh(SUB_TX_RESET_KEY_D['regTxHash'])
        assert len(extra.hashPrevSubTx) == 32
        assert extra.hashPrevSubTx == bfh(SUB_TX_RESET_KEY_D['hashPrevSubTx'])
        assert extra.creditFee == SUB_TX_RESET_KEY_D['creditFee']
        assert len(extra.newPubKey) == 48
        assert extra.newPubKey == bfh(SUB_TX_RESET_KEY_D['newPubKey'])
        assert len(extra.payloadSig) == 96
        assert extra.payloadSig == bfh(SUB_TX_RESET_KEY_D['payloadSig'])
        ser = tx.serialize()
        assert ser == SUB_TX_RESET_KEY

        assert extra.to_hex_str() == SUB_TX_RESET_KEY[386:]
        extra2 = ProTxBase.from_hex_str(SPEC_SUB_TX_RESET_KEY,
                                        SUB_TX_RESET_KEY[386:])
        assert extra2.version == extra.version
        assert extra2.regTxHash == extra.regTxHash
        assert extra2.hashPrevSubTx == extra.hashPrevSubTx
        assert extra2.creditFee == extra.creditFee
        assert extra2.newPubKey == extra.newPubKey
        assert extra2.payloadSig == extra.payloadSig

    def test_cintamani_tx_sub_tx_close_account(self):
        tx = transaction.Transaction(SUB_TX_CLOSE_ACCOUNT)
        deser = tx.to_json()
        assert deser['version'] == 3
        assert deser['tx_type'] == 11
        extra_dict = deser['extra_payload']
        assert extra_dict == SUB_TX_CLOSE_ACCOUNT_D
        extra = tx.extra_payload
        assert(str(extra))
        assert extra.version == SUB_TX_CLOSE_ACCOUNT_D['version']
        assert len(extra.regTxHash) == 32
        assert extra.regTxHash == bfh(SUB_TX_CLOSE_ACCOUNT_D['regTxHash'])
        assert len(extra.hashPrevSubTx) == 32
        assert extra.hashPrevSubTx == \
            bfh(SUB_TX_CLOSE_ACCOUNT_D['hashPrevSubTx'])
        assert extra.creditFee == SUB_TX_CLOSE_ACCOUNT_D['creditFee']
        assert len(extra.payloadSig) == 96
        assert extra.payloadSig == bfh(SUB_TX_CLOSE_ACCOUNT_D['payloadSig'])
        ser = tx.serialize()
        assert ser == SUB_TX_CLOSE_ACCOUNT

        assert extra.to_hex_str() == SUB_TX_CLOSE_ACCOUNT[386:]
        extra2 = ProTxBase.from_hex_str(SPEC_SUB_TX_CLOSE_ACCOUNT,
                                        SUB_TX_CLOSE_ACCOUNT[386:])
        assert extra2.version == extra.version
        assert extra2.regTxHash == extra.regTxHash
        assert extra2.hashPrevSubTx == extra.hashPrevSubTx
        assert extra2.creditFee == extra.creditFee
        assert extra2.payloadSig == extra.payloadSig

    def test_cintamani_tx_unknown_spec_tx(self):
        tx = transaction.Transaction(UNKNOWN_SPEC_TX)
        with self.assertRaises(DashTxError):
            tx.to_json()

    def test_cintamani_tx_wrong_spec_tx(self):
        tx = transaction.Transaction(WRONG_SPEC_TX)
        deser = tx.to_json()
        assert deser['version'] == 12255234
        assert deser['tx_type'] == 0
        extra_dict = deser['extra_payload']
        assert extra_dict == ''
        extra = tx.extra_payload
        assert extra == b''
        ser = tx.serialize()
        assert ser == WRONG_SPEC_TX

    def test_deserialize_transaction_v2(self):
        cmds = Commands(config=None)
        deser = cmds._run('deserialize', (V2_TX, ))
        assert deser['extra_payload'] == ''

    def test_deserialize_transaction_cbtx(self):
        cmds = Commands(config=None)
        deser = cmds._run('deserialize', (CB_TX_V2, ))
        assert deser['extra_payload'] == CB_TX_V2_D

    def test_deserialize_transaction_unknown_spec_tx(self):
        cmds = Commands(config=None)
        with self.assertRaises(DashTxError):
            coro = cmds.deserialize(UNKNOWN_SPEC_TX)
            fut = asyncio.run_coroutine_threadsafe(coro, asyncio.get_event_loop())
            result = fut.result()

    def test_serialize_command_with_extra_payload(self):
        cmds = Commands(config=None)
        test_json_tx = {
            'inputs': [],
            'outputs': [],
        }
        res = cmds._run('serialize', (test_json_tx, ))
        assert res == '02000000000000000000'

        test_json_tx.update({'extra_payload': ''})
        res = cmds._run('serialize', (test_json_tx, ))
        assert res == '02000000000000000000'

        test_json_tx.update({'extra_payload': {'key': 'value'}})
        res = cmds._run('serialize', (test_json_tx, ))
        assert res == {'error': 'Transactions with extra payload can not'
                                ' be created from serialize command'}

        test_json_tx.update({'extra_payload': '0b0a'})
        res = cmds._run('serialize', (test_json_tx, ))
        assert res == {'error': 'Transactions with extra payload can not'
                                ' be created from serialize command'}
