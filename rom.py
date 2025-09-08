# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024, Tiny Tapeout LTD
# Author: Uri Shaked

# Generates the ROM file for the shuttle. The ROM layout is documented at:
# https://github.com/TinyTapeout/tt-chip-rom/blob/main/docs/info.md.

import binascii
import os
from urllib.parse import urlparse

from git.repo import Repo

from config import Config

MAX_ROM_TEXT_SIZE = 92

segment_font = {
    " ": 0b00000000,
    "0": 0b00111111,
    "1": 0b00000110,
    "2": 0b01011011,
    "3": 0b01001111,
    "4": 0b01100110,
    "5": 0b01101101,
    "6": 0b01111101,
    "7": 0b00000111,
    "8": 0b01111111,
    "9": 0b01101111,
    "A": 0b01110111,
    "B": 0b01111100,
    "C": 0b00111001,
    "D": 0b01011110,
    "E": 0b01111001,
    "F": 0b01110001,
    "a": 0b01110111,
    "b": 0b01111100,
    "c": 0b01011000,
    "d": 0b01011110,
    "f": 0b01110001,
    "h": 0b01110110,  # Actually uppercase H
    "i": 0b00110000,  # Actually uppercase I
    "k": 0b01110101,
    "o": 0b01011100,
    "p": 0b01110011,
    "s": 0b01101101,
    "t": 0b01111000,
    "y": 0b01101110,
}


def segment_char(c: str):
    return segment_font[c]


class ROMFile:
    def __init__(self, config: Config):
        self.config = config

    def get_git_remote(self) -> str:
        repo_url = list(Repo(".").remotes[0].urls)[0]
        return urlparse(repo_url).path[1:]

    def get_git_commit_hash(self) -> str:
        return Repo(".").commit().hexsha

    def write_rom(self):
        rom = bytearray(256)
        short_sha = self.get_git_commit_hash()[:8]

        rom_text = f"shuttle={self.config['id']}\n"
        rom_text += f"repo={self.get_git_remote()}\n"
        rom_text += f"commit={short_sha}\n"

        print(f"\nROM text: {len(rom_text)} bytes (max={MAX_ROM_TEXT_SIZE})\n")
        print("  " + "\n  ".join(rom_text.split("\n")))

        assert len(rom_text) < MAX_ROM_TEXT_SIZE, "ROM text too long"

        shuttle_id = self.config["id"][:8]
        rom[0 : len(shuttle_id)] = map(segment_char, shuttle_id)
        rom[8:16] = map(segment_char, short_sha.upper())
        rom[32 : 32 + len(rom_text)] = rom_text.encode("ascii")
        rom[248:252] = b"TT\xFA\xBB"
        rom[252:256] = binascii.crc32(rom[0:252]).to_bytes(4, "little")

        with open(os.path.join(os.path.dirname(__file__), "rom/rom.vmem"), "w") as fh:
            for line in rom_text.split("\n"):
                if len(line) == 0:
                    continue
                fh.write(f"// {line}\n")
            fh.write("\n")
            for line_offset in range(0, len(rom), 16):
                for byte in range(0, 16):
                    fh.write("{:02x} ".format(rom[line_offset + byte]))
                fh.write("\n")
