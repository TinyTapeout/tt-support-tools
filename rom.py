import git

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
    "t": 0b01111000,
}

def segment_char(c):
    return segment_font[c]

class ROMFile:
    def __init__(self, config, projects):
        self.projects = projects
        self.config = config

    def get_git_remote(self):
        return list(git.Repo(".").remotes[0].urls)[0]

    def get_git_commit_hash(self):
        return git.Repo(".").commit().hexsha

    def write_rom(self):
        rom = bytearray(256)
        short_sha = self.get_git_commit_hash()[:8]

        rom_text = f"shuttle={self.config['name']}\n"
        rom_text += f"repo={self.get_git_remote()}\n"
        rom_text += f"commit={short_sha}\n"

        assert len(rom_text) < 96, "ROM text too long"

        rom[0:4] = map(segment_char, "tt04")
        rom[8:16] = map(segment_char, short_sha.upper())
        rom[32 : 32 + len(rom_text)] = rom_text.encode("ascii")

        # build complete list of filenames for sim
        with open("verilog/includes/rom_tile.vmem", "w") as fh:
            for line in range(0, len(rom), 16):
                for byte in range(0, 16):
                    fh.write("{:02x} ".format(rom[line + byte]))
                fh.write("\n")
