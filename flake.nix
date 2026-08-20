{
  description = "TT support tools development environment for TTSKY26a hardening";

  inputs = {
    librelane.url = "github:librelane/librelane";
  };

  outputs = { self, librelane, ... }: let
    forAllSystems = librelane.inputs.nix-eda.forAllSystems;
  in {
    devShells = forAllSystems (system: let
      nixpkgs = librelane.inputs.nix-eda.inputs.nixpkgs;
      devshell = librelane.inputs.devshell;
      pkgs = import nixpkgs {
        inherit system;
        overlays = [
          devshell.overlays.default
          librelane.inputs.nix-eda.overlays.default
          librelane.overlays.default
          (final: prev: prev.lib.optionalAttrs prev.stdenv.isDarwin {
            # ghdl-mcode is Linux-only; stub it out on macOS so cocotb can be built
            # without VHDL simulation support (which we don't need).
            ghdl-mcode = prev.runCommand "ghdl-mcode-stub" {} "mkdir $out";
            python3 = prev.python3.override {
              packageOverrides = pyFinal: pyPrev: {
                # nixpkgs pins cocotb 1.8.1 which uses MODULE= env var.
                # tt-support-tools test Makefile uses COCOTB_TEST_MODULES= (cocotb 2.x API).
                # Override with cocotb 2.0.1 from PyPI.
                find-libpython = pyPrev.find-libpython.overridePythonAttrs (_: rec {
                  version = "0.5.1";
                  src = prev.fetchurl {
                    url = "https://files.pythonhosted.org/packages/source/f/find_libpython/find_libpython-${version}.tar.gz";
                    sha256 = "1zjranrffz2l782acpcfq72ai91f2jyv2m6m1ynn9k4dzwwzp80j";
                  };
                  doCheck = false;
                });
                cocotb = pyPrev.cocotb.overridePythonAttrs (_: rec {
                  version = "2.0.1";
                  src = prev.fetchurl {
                    url = "https://files.pythonhosted.org/packages/source/c/cocotb/cocotb-${version}.tar.gz";
                    sha256 = "10jfg238wba7vbbb9hyhjjdg2vqzvb0dd6jpz2c3xx1g8547g239";
                  };
                  patches = [];
                  doCheck = false;
                });
              };
            };
          })
        ];
      };
    in {
      default = pkgs.callPackage (librelane.createOpenLaneShell {

        extra-packages = with pkgs;
          pkgs.lib.optionals stdenv.isDarwin [
            cairo
          ];

        extra-env = pkgs.lib.optionals pkgs.stdenv.isDarwin [
          {
            name = "DYLD_LIBRARY_PATH";
            value = "${pkgs.gfortran.cc.lib}/lib:${pkgs.cairo}/lib";
          }
        ];

        extra-python-packages = with pkgs.python3.pkgs; [
          # tt-support-tools direct dependencies
          cairosvg
          chevron
          cocotb
          configupdater
          find-libpython
          gitpython
          mistune
          pillow
          pytest
          python-frontmatter

          # transitive dependencies
          cffi
          cssselect2
          defusedxml
          smmap
          tinycss2
          webencodings
        ];

      }) {};
    });
  };
}
