{
  description = "track-lab: agent plugins and skills for track workflows";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems =
        f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs: rec {
        pdf-engine = pkgs.rustPlatform.buildRustPackage {
          pname = "track-pdf-engine";
          version = "0.1.0";
          src = pkgs.lib.cleanSourceWith {
            src = ./tools/pdf-engine;
            filter = path: _type: baseNameOf path != "target";
          };
          cargoLock.lockFile = ./tools/pdf-engine/Cargo.lock;
          buildInputs = pkgs.lib.optionals pkgs.stdenv.hostPlatform.isDarwin [ pkgs.libiconv ];
          # The PDF contract is exercised against this binary by checks.pdf-extraction.
          doCheck = false;
        };

        extract-pdf = pkgs.writeShellApplication {
          name = "track-extract-pdf";
          runtimeInputs = [ pdf-engine pkgs.python3 ];
          text = ''
            exec python3 ${./plugins/note/skills/track-clip/scripts/extract_pdf.py} "$@"
          '';
        };

        # textlint と ai-writing preset を lock ごと nix store に固定する。
        # npx が版を引き直さないので、誰が実行しても指摘が一致する。
        textlint = pkgs.buildNpmPackage {
          pname = "track-lab-textlint";
          version = "0.1.0";
          src = ./nix/textlint;
          npmDepsHash = "sha256-1Y7sufRi7Mnd5OV0uC7BsdFCufLZLQviwuRrVgFtkGs=";
          dontNpmBuild = true;
          nativeBuildInputs = [ pkgs.makeWrapper ];
          installPhase = ''
            runHook preInstall
            mkdir -p $out/lib
            cp -r node_modules $out/lib/node_modules
            makeWrapper ${pkgs.nodejs}/bin/node $out/bin/textlint \
              --add-flags $out/lib/node_modules/textlint/bin/textlint.js \
              --set NODE_PATH $out/lib/node_modules
            runHook postInstall
          '';
        };

        lint = pkgs.writeShellApplication {
          name = "track-lab-lint";
          runtimeInputs = [
            textlint
            pkgs.git
          ];
          text = ''
            if [ "$#" -gt 0 ]; then
              exec textlint "$@"
            fi
            # The file list is relative, so resolve it against the repo root
            # rather than wherever the caller happens to stand.
            cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
            mapfile -d "" files < <(find plugins README.md -name '*.md' -print0)
            if [ "''${#files[@]}" -eq 0 ]; then
              # textlint exits 0 on an empty argument list, which would read as
              # a clean run.
              echo "track-lab-lint: no Markdown files found under $PWD" >&2
              exit 1
            fi
            exec textlint "''${files[@]}"
          '';
        };

        default = lint;
      });

      apps = forAllSystems (pkgs: rec {
        extract-pdf = {
          type = "app";
          program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.extract-pdf}/bin/track-extract-pdf";
        };
        lint = {
          type = "app";
          program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.lint}/bin/track-lab-lint";
        };
        default = lint;
      });

      # `nix flake check` runs prose lint and the isolated PDF extraction contract.
      checks = forAllSystems (pkgs: {
        pdf-extraction = pkgs.runCommand "track-pdf-extraction-check" {
          nativeBuildInputs = [ pkgs.python3 self.packages.${pkgs.stdenv.hostPlatform.system}.pdf-engine ];
        } ''
          python3 ${./plugins/note/skills/track-clip/tests/test_extract_pdf.py} \
            ${./plugins/note/skills/track-clip/scripts/extract_pdf.py}
          touch "$out"
        '';
        lint = pkgs.runCommand "track-lab-lint-check" { } ''
          export HOME="$TMPDIR"
          cd ${self}
          ${self.packages.${pkgs.stdenv.hostPlatform.system}.lint}/bin/track-lab-lint
          touch "$out"
        '';
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            self.packages.${pkgs.stdenv.hostPlatform.system}.textlint
            self.packages.${pkgs.stdenv.hostPlatform.system}.extract-pdf
            self.packages.${pkgs.stdenv.hostPlatform.system}.pdf-engine
            pkgs.python3
            pkgs.cargo
            pkgs.rustc
          ];
          buildInputs = pkgs.lib.optionals pkgs.stdenv.hostPlatform.isDarwin [ pkgs.libiconv ];
        };
      });
    };
}
