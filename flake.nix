{
  description = "Tiny Tapeout tools packaged using poetry2nix";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        pkgs = nixpkgs.legacyPackages.${system};
        p2n = poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
        commit = if self ? "rev" then builtins.substring 0 7 self.rev else "dirty";
        version = "6.0.0+${commit}";
      in
      {
        packages = {
          tt-tools = (p2n.mkPoetryApplication {
            projectDir = self;

            overrides = p2n.overrides.withDefaults (self: super: {

              gdstk = super.gdstk.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [ self.setuptools pkgs.zlib pkgs.qhull ];
                nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.cmake ];
                dontUseCmakeConfigure = true;
                # gdstk ships with its own FindQhull.cmake, but that isn't
                # included in the python release -- fix
                postPatch = ''
                  if [ ! -e cmake_modules/FindQhull.cmake ]; then
                    mkdir -p cmake_modules
                    cp ${pkgs.fetchurl {
                      url = "https://github.com/heitzmann/gdstk/raw/57c9ecec1f7bc2345182bcf383602a792026a28b/cmake_modules/FindQhull.cmake";
                      hash = "sha256-lJNWAfSItbg7jsHfe7gZryqJruHjjMM0GXudXa/SJu4=";
                    }} cmake_modules/FindQhull.cmake
                  fi
                '';
              });

              defusedxml = super.defusedxml.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [ self.setuptools ];
              });

              pillow = super.pillow.overridePythonAttrs (old: {
                # Use preConfigure from nixpkgs to fix library detection issues and
                # impurities which can break the build process; this also requires
                # adding propagatedBuildInputs and buildInputs from the same source.
                propagatedBuildInputs = (old.buildInputs or [ ]) ++ [ self.olefile self.defusedxml ];
                buildInputs = (old.buildInputs or [ ]) ++ pkgs.python3.pkgs.pillow.buildInputs;
                preConfigure = (old.preConfigure or "") + pkgs.python3.pkgs.pillow.preConfigure;

                # https://github.com/nix-community/poetry2nix/issues/1139
                patches = (old.patches or [ ]) ++ pkgs.lib.optionals (old.version == "9.5.0") [
                  (pkgs.fetchpatch {
                    url = "https://github.com/python-pillow/Pillow/commit/0ec0a89ead648793812e11739e2a5d70738c6be5.diff";
                    sha256 = "sha256-rZfk+OXZU6xBpoumIW30E80gRsox/Goa3hMDxBUkTY0=";
                  })
                ];
              });

            });
          }).overridePythonAttrs (old:
            {
              inherit version;
              patchPhase = ''
                sed \
                  -e 's/tt_version\s*=.*/tt_version = "${version}"/' \
                  -e 's|yowasp-yosys|${pkgs.yosys}/bin/yosys|' \
                  -i tt_support_tools/project.py \

              '';
            });
          default = self.packages.${system}.tt-tools;
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.tt-tools ];
          packages = [ pkgs.poetry ];
        };
      });
}
