#!/usr/bin/env python3

from struct import unpack, iter_unpack, calcsize
from collections import namedtuple
import numpy
from PIL import Image
from itertools import islice

PIX_PER_COLUMN = 64
COLMNS_PER_BUFFER = 16
BYTES_PIXEL = 12
TICK_PER_REVOLUTION = 90112
HEADER_SIZE = 16
FOOTER_SIZE = 4
BYTES_PER_COLUMN = HEADER_SIZE + PIX_PER_COLUMN * BYTES_PIXEL + FOOTER_SIZE

def file_to_buffers(f):
    while True:
        buf = f.read(BYTES_PER_COLUMN * COLMNS_PER_BUFFER)
        if not buf: break
        yield buf

def buffers_to_frames(buffers):
    struct = "Q H H I 768s I"
    Col = namedtuple("Col", "timestamp column_id frame_id ticks pixeldata valid")
    frame = []
    last_frame_id = -1
    for buffer in buffers:
        for chunck in iter_unpack(struct, buffer):
            column = Col._make(chunck)
            if column.frame_id == last_frame_id:
                frame.append(column)
            else:
                if frame:
                    yield frame
                frame = [column]
                last_frame_id = column.frame_id

def split_pixeldata_to_pixels(pixeldata):
    ## last 2 bytes are unspecified?
    struct = "I H H H xx"
    ## remember to mask range with 0xFFFFF
    Pixel = namedtuple("Pixel", "range reflectivity signal noise")
    for chunck in iter_unpack(struct, pixeldata):
        yield Pixel._make(chunck)

def frames_to_images(frames):
    size = (64, 1024)
    for frame in frames:
        data = numpy.zeros(size, dtype=numpy.uint8)
        for column in frame:
            y = column.column_id
            pixels = split_pixeldata_to_pixels(column.pixeldata)
            for x, pixel in enumerate(pixels):
                yy = y-(x%4)*6
                data[x, yy%1024] = 255*(pixel.range & 0xFFFFF)/100000
        img = Image.fromarray(data)
        yield img

with open("lombard_street_OS1.dd", "rb") as f:
    buffers = file_to_buffers(f)
    frames = buffers_to_frames(buffers)
    images = frames_to_images(frames)
    ims = list(islice(images, 1, 1000))
    ims[0].save("out.gif", save_all=True, append_images=ims, duration=20, loop=0)

