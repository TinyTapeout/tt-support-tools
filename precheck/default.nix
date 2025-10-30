{ pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/cee01fe2c16da2d972b56c595d96b53fdd8ecc3f.tar.gz")
    { }
,
}:

pkgs.mkShell {
  buildInputs = [
    pkgs.klayout
    pkgs.magic-vlsi
  ];
}
