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
          runtimeInputs = [ textlint ];
          text = ''
            if [ "$#" -gt 0 ]; then
              exec textlint "$@"
            fi
            mapfile -d "" files < <(find plugins README.md -name '*.md' -print0)
            exec textlint "''${files[@]}"
          '';
        };

        default = lint;
      });

      apps = forAllSystems (pkgs: rec {
        lint = {
          type = "app";
          program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.lint}/bin/track-lab-lint";
        };
        default = lint;
      });

      # `nix flake check` runs the linter, so CI needs no separate step.
      checks = forAllSystems (pkgs: {
        lint = pkgs.runCommand "track-lab-lint-check" { } ''
          export HOME="$TMPDIR"
          cd ${self}
          ${self.packages.${pkgs.stdenv.hostPlatform.system}.lint}/bin/track-lab-lint
          touch "$out"
        '';
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [ self.packages.${pkgs.stdenv.hostPlatform.system}.textlint ];
        };
      });
    };
}
