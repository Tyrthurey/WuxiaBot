{ pkgs }: {
  deps = [
    pkgs.nodePackages.prettier
    pkgs.libopus
    pkgs.ffmpeg-full
  ];
  env = {
  };
}