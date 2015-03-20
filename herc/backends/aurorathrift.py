from thrift.transport.THttpClient import THttpClient
from thrift.protocol.TJSONProtocol import TJSONProtocol
from gen.apache.aurora.api import AuroraAdmin

class AuroraThrift(object):
    """Talk to the Aurora scheduler using its Thrift API."""

    def __init__(self):
        self.transport = THttpClient("http://localhost:8081/api")
        self.protocol = TJSONProtocol(self.transport)
        self.transport.open()
        self.client = AuroraAdmin.Client(self.protocol)
