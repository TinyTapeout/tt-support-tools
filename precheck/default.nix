{ pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/f2bd8adf7b78d7616b52d0ef08865c7c2fcf189d.tar.gz")
    { }
, magic ? import ./nix/magic.nix { inherit pkgs; }
,
}:

pkgs.mkShell {
  buildInputs = [
    pkgs.klayout
    magic
  ];
}
