{ pkgs }: {
  deps = [
    pkgs.yarn
    pkgs.nodePackages.prettier
    pkgs.libopus
    pkgs.ffmpeg-full
  ];
  env = {
  };
}