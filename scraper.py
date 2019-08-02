#!/usr/bin/env python3

import argparse, progressbar, numpy, json
import logging as log

from struct import unpack, iter_unpack, calcsize
from collections import namedtuple
from PIL import Image
from itertools import islice

PIX_PER_COLUMN = 64
COLMNS_PER_BUFFER = 16
BYTES_PIXEL = 12
TICK_PER_REVOLUTION = 90112
HEADER_SIZE = 16
FOOTER_SIZE = 4
BYTES_PER_COLUMN = HEADER_SIZE + PIX_PER_COLUMN * BYTES_PIXEL + FOOTER_SIZE
ROWS_PER_FRAME = 1024

PCAP_HEADER_SIZE = 24
UDP_OVERHEAD = 42

def is_pcap(f):
    f.seek(0)
    magic = unpack("I", f.read(4))[0]
    f.seek(0)
    is_capture    = magic in [0xa1b2c3d4, 0xd4c3b2a1, 0xa1b23c4d, 0x4d3cb2a1]
    is_revsersed  = magic in [0xd4c3b2a1, 0x4d3cb2a1]
    is_nanosecond = magic in [0xa1b23c4d, 0x4d3cb2a1]
    return is_capture

def raw_to_buffers(f):
    while True:
        buf = f.read(BYTES_PER_COLUMN * COLMNS_PER_BUFFER)
        if not buf: break
        yield buf

def pcap_to_buffers(f):
    head = f.read(PCAP_HEADER_SIZE)
    pkt_meta_fmt = "IIII"
    PktMeta = namedtuple("PktMeta", "ts_sec ts_usec incl_len orig_len")
    while True:
        chunk = f.read(calcsize(pkt_meta_fmt))
        if not chunk: break
        pktmeta = PktMeta._make(unpack(pkt_meta_fmt, chunk))
        assert(pktmeta.incl_len == pktmeta.orig_len)
        f.seek(UDP_OVERHEAD, 1)
        pkt = f.read(pktmeta.incl_len - UDP_OVERHEAD)
        yield pkt

def file_to_buffers(f):
    if is_pcap(f):
        return pcap_to_buffers(f)
    else:
        return raw_to_buffers(f)

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

def frames_to_images(frames, start, stop, azimuth_correction):
    def fix_azimuth(x, y):
        return int(y + azimuth_correction[x])

    size = (PIX_PER_COLUMN, ROWS_PER_FRAME)
    if stop: bar = progressbar.ProgressBar(maxval=stop-start).start()
    for i, frame in enumerate(islice(frames, start, stop)):
        data = numpy.zeros(size, dtype=numpy.uint8)
        for column in frame:
            y = column.column_id
            pixels = split_pixeldata_to_pixels(column.pixeldata)
            for x, pixel in enumerate(pixels):
                yy = fix_azimuth(x, y)
                data[x, yy%ROWS_PER_FRAME] = 255*(pixel.range & 0xFFFFF)/100000
                #data[x, yy%ROWS_PER_FRAME] = 255*(pixel.reflectivity & 0xFFFFF)/35500
                #data[x, yy%ROWS_PER_FRAME] = 255*(pixel.signal & 0xFFFFF)/1500
                #data[x, yy%ROWS_PER_FRAME] = 255*(pixel.noise & 0xFFFFF)/1500
        img = Image.fromarray(data)
        log.debug(f"writing img {i}")
        yield img
        if stop: bar.update(i)
    if stop: bar.finish()

def parse_arguments():
    parser = argparse.ArgumentParser(description="TODO description",
        epilog="2019 - KapiteinLabs - yuri@kapiteinlabs.com")
    parser.add_argument("-l", "--log-level", help="Set loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        type=str.upper, action="store", default="INFO")
    parser.add_argument("-c", "--calibration_file", help="JSON file containing calibration info",
        action="store", type=str, default=None)
    parser.add_argument("-r", "--read-file", help="PCAP/RAW file containing OS1 data",
        action="store", type=str, required=True)
    parser.add_argument("-o", "--outfile", help="GIF to write",
        action="store", type=str, required=True)
    parser.add_argument("-n", "--framecount", help="Number of frames",
        action="store", type=int)
    parser.add_argument("-f", "--fps", help="Frame rate of output gif",
        action="store", type=float, default=62.5)
    return parser.parse_args()

def main(args):
    FRAMETIME_MS = 1000//args.fps

    if args.calibration_file:
        with open(args.calibration_file, "r") as f:
            calib = json.load(f)
            azimuths = [a for a in calib['beam_azimuth_angles']]
    else:
        log.warning("No calibration file given. Estimating azimuth errors.")
        azimuths = [a*360/1024 for a in [9,3,-3,-9]*16]
    azimuth_pixel_corrections = [a*1024/360 for a in azimuths]

    with open(args.read_file, "rb") as f:
        buffers = file_to_buffers(f)
        frames = buffers_to_frames(buffers)
        images = frames_to_images(frames, start=1, stop=args.framecount,
            azimuth_correction=azimuth_pixel_corrections)
        first_img = next(images)
        first_img.save(args.outfile, save_all=True, append_images=images,
            duration=FRAMETIME_MS, loop=0)

if __name__ == '__main__':
    args = parse_arguments()
    log.basicConfig(level=args.log_level)
    main(args)
