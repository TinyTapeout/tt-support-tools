{ pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/8f7a6554c058bfdae00f4fb36f5cd52838f410e7.tar.gz")
    { }
,
}:

pkgs.mkShell {
  buildInputs = [
    pkgs.klayout
    pkgs.magic-vlsi
  ];
}
