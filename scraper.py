#!/usr/bin/env python3

from struct import unpack, iter_unpack, calcsize
from collections import namedtuple

PIX_PER_COLUMN = 64
COLMNS_PER_BUFFER = 16
BYTES_PIXEL = 12
TICK_PER_REVOLUTION = 90112
HEADER_SIZE = 16
FOOTER_SIZE = 4
BYTES_PER_COLUMN = HEADER_SIZE + PIX_PER_COLUMN * BYTES_PIXEL + FOOTER_SIZE

def split_buffer_to_columns(buffer):
    struct = "Q H H I 768s I"
    Col = namedtuple("Col", "timestamp column_id frame_id ticks pixeldata valid")
    for chunck in iter_unpack(struct, buffer):
        yield Col._make(chunck)

def split_pixeldata_to_pixels(pixeldata):
    ## last 2 bytes are unspecified?
    struct = "I H H H xx"
    ## remember to mask range with 0xFFFFF
    Pixel = namedtuple("Pixel", "range reflectivity signal noise")
    for chunck in iter_unpack(struct, pixeldata):
        yield Pixel._make(chunck)

with open("lombard_street_OS1.dd", "rb") as f:
    c = 0
    while f:
        buflen = BYTES_PER_COLUMN * COLMNS_PER_BUFFER
        buf = f.read(buflen)

        rlen = len(buf)
        if rlen <= 0:
            break
        c += rlen
        columns = split_buffer_to_columns(buf)
        for col in columns:
            if col.valid != 4294967295:
                print(col.valid)
            #pixels = split_pixeldata_to_pixels(col.pixeldata)
            #for pixel in pixels:
                #print(col.column_id, col.ticks, pixel)
                #print(pixel.range)

