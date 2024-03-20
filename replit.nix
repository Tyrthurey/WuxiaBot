{ pkgs }: {
  deps = [
    pkgs.git-lfs
    pkgs.yarn
    pkgs.nodePackages.prettier
    pkgs.libopus
    pkgs.ffmpeg-full
  ];
  env = {
  };
}