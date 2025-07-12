{ pkgs }: {
  deps = [
    pkgs.python311Full
    pkgs.git
    pkgs.openssl
    pkgs.sqlite
    pkgs.curl
    pkgs.unzip
  ];
}