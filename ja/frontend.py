#!/usr/bin/env python

"""Ninja frontend interface.

This module implements a Ninja frontend interface that delegates handling each
message to a handler object
"""

import os
import pkg_resources
import google.protobuf.descriptor_pb2
import google.protobuf.message_factory

def default_reader():
    fd = 3
    return os.fdopen(fd, 'rb', 0)

class Frontend(object):
    """Generator class that parses length-delimited ninja status messages
    through a ninja frontend interface.
    """

    def __init__(self, reader=None):
        self.reader = reader if reader else default_reader()
        self.status_class = self.get_status_proto()

    def get_status_proto(self):
        fd_set = google.protobuf.descriptor_pb2.FileDescriptorSet()
        descriptor = 'frontend.pb'
        fd_set.ParseFromString(pkg_resources.resource_string(__name__, 'frontend.pb'))

        if len(fd_set.file) != 1:
            raise RuntimeError('expected exactly one file descriptor in ' + descriptor)

        messages = google.protobuf.message_factory.GetMessages(fd_set.file)
        return messages['ninja.Status']

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        size = 0
        shift = 0
        while True:
            byte = bytearray(bytes(self.reader.read(1)))
            if not byte:
                raise StopIteration()

            byte = byte[0]
            size += (byte & 0x7f) << (shift * 7)
            if (byte & 0x80) == 0:
                break
            shift += 1
            if shift > 4:
                raise "Expected varint32 length-delimeted message"

        message = bytes(self.reader.read(size))
        while len(message) < size:
            new_bytes = bytes(self.reader.read(size - len(message)))
            if not new_bytes:
                break
            message += new_bytes

        if len(message) != size:
            raise Exception("Unexpected EOF reading {} bytes".format(size))

        try:
            return self.status_class.FromString(message)
        except google.protobuf.message.DecodeError as err:
            print(err)
            return self.next()
