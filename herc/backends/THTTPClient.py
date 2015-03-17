from thriftpy.transport import TTransportBase, TTransportException
import requests
import requests.exceptions
import logging
from io import BytesIO


log = logging.getLogger('thrift.THTTPClient')


class THTTPClient(TTransportBase):
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = str(port)
        self.timeout = timeout
        self.session = None
        self._rbuf = BytesIO()
        self._wbuf = BytesIO()
        log.info("New THTTPClient: " + self.host + ":" + self.port )

    def open(self):
        log.info("Session opened")
        self.session = requests.Session()
        self.session.headers['Content-Type'] = 'application/x-thrift'
        self.session.headers['Host'] = self.host

    def close(self):
        log.info("Session closed")
        self.session.close()

    def read(self, size):
        log.info("Reading " + str(size) + " bytes")
        self._rbuf.read(size)

    def write(self, buff):
        log.info("Writing: " + str(buff))
        self._rbuf.write(buff)

    def flush(self):
        data = self._wbuf.getvalue()
        log.debug("Sending " + str(data) + " to " + str(self.host) + ":" + self.port)
        self._wbuf = BytesIO()

        self.session.headers['Content-Length'] = str(len(data))

        response = None
        try:
            response = self.session.post(
                self.host + ":" + self.port,
                data=data,
                timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise TTransportException(
                type=TTransportException.TIMED_OUT,
                message='Timed out talking to %s' % self.host + ":" + self.port )
        except requests.exceptions.RequestException as e:
            if response:
                log.debug('Error connecting, logging response headers:.')
                for field_name, field_value in response.headers.items():
                    log.debug('  %s: %s' % (field_name, field_value))
            raise TTransportException(
                type=TTransportException.UNKNOWN,
                message='Unknown error talking to %s: %s' % (self.host + ":" + self.port, e) )

        self._rbuf = BytesIO(response.content)

class THTTPClientFactory(object):
    def get_transport(self, socket):
        return THTTPClient(socket.host, socket.port, socket._timeout)
