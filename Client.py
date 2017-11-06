import asyncio
import playground
import random, zlib, logging
from playground import getConnector
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING, UINT64, UINT16, UINT8, BUFFER, LIST
from playground.network.packet.fieldtypes.attributes import Optional
from playground.network.common.Protocol import StackingProtocol, StackingProtocolFactory, StackingTransport
from clientcertfactory import getCertsForAddr, getPrivateKeyForAddr, getIDCertsForAddr, getRootCertsForAddr
import sys
import os
from cryptography import x509
from cryptography.hazmat.backends import default_backend


class BasePacketType(PacketType):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.basepacket"
    DEFINITION_VERSION = "1.0"


class PlsHello(BasePacketType):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.hello"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("Nonce", UINT64),
        ("Certs", LIST(BUFFER))
    ]


class PlsKeyExchange(BasePacketType):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.keyexchange"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("PreKey", BUFFER),
        ("NoncePlusOne", UINT64),
    ]


class PlsHandshakeDone(BasePacketType):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.handshakedone"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("ValidationHash", BUFFER)
    ]


class PlsData(BasePacketType):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.data"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("Ciphertext", BUFFER),
        ("Mac", BUFFER)
    ]


'''class PlsClose(BasePacketType):
    DEFINITION_IDENTIFIER = "netsecfall2017.pls.close"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("Error", STRING(Optional))
    ]'''


class PLSStackingTransport(StackingTransport):
    pass


class PLSClient(StackingProtocol):
    def __init__(self, loop):
        print("###PLSClient init###")
        self.deserializer = BasePacketType.Deserializer()
        self.transport = None
        self.loop = loop

    def connection_made(self, transport):
        print("###PLSClient connection made###")
        self.transport = transport
        clienthello = PlsHello()
        clienthello.Nonce = 12345678
        idcert = getIDCertsForAddr()
        pubkey = getCertsForAddr()
        root = getRootCertsForAddr()
        clienthello.Certs.append(idcert)
        clienthello.Certs.append(pubkey)
        clienthello.Certs.append(root)
        packs = clienthello.__serialize__()
        print("Sent the Client hello.")
        self.transport.write(packs)

    def validate(self, certificate):
        cert = x509.load_pem_x509_certificate(certificate[0], default_backend())
        if cert.Issuer == "C = US, ST = MD, L = Baltimore, O = JHUNetworkSecurityFall2017, OU = PETF, CN = 20174.1.666, emailAddress = vbollap1@jhu.edu":
            pass

    def data_received(self, data):
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():

            if isinstance(packet, PlsHello):
                result = self.validate(packet.Certs)
                clientkey = PlsKeyExchange()
                clientkey.PreKey = os.urandom(16)
                clientkey.NoncePlusOne = packet.Nonce + 1



    def connection_lost(self,exc):
        self.transport.close()
        self.loop.stop()
        self.transport = None

if __name__ == "__main__":

    loop = asyncio.get_event_loop()

    Clientfactory = StackingProtocolFactory(lambda: PLSClient(loop))

    coro = playground.getConnector().create_playground_connection(Clientfactory, '20174.1.1.1', 8888)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    loop.close()
