This is a script I use for backing up SAI files as I work on them, because SAI file recovery doesn't work on Linux.

### Installation from source
- Install python: https://www.python.org/downloads/
- Install project: `pip install -e .`
- See arguments with: `auto-backup --help`
- If exporting doesn't work, you may also need to install ffmpeg: https://www.gyan.dev/ffmpeg/builds/#release-builds
  - You can add the bin directory to your path, or copy ffmpeg.exe to the script folder.

### Building/installing with Nix
- This project is a Nix flake, so you can run flake commands to interact with the package `nix run`, `nix build`, etc.

### Nix systemd task example for your configuration.nix
```nix
{ pkgs, ... }:
let
  flakepkg = (builtins.getFlake path).packages.${pkgs.system}.default;
  sai-auto-backup = flakepkg "github:cromachina/auto-backup";
in
{
  systemd.services.sai-auto-backup = {
    enable = true;
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "simple";
      User = "cro";
      ExecStart = "${sai-auto-backup}/bin/auto-backup --no-recursive --backup-limit 10 --scan-dir /home/cro/aux/art --backup-dir /home/cro/aux/backups --file-match '.*\.(sai2|psd)$'";
    };
  };
}
```