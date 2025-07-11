{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.sqlite
    pkgs.git
  ];
}

{ pkgs }: {
  deps = [
    pkgs.python311Full
    pkgs.python311Packages.flask
    pkgs.python311Packages.flask_sqlalchemy
    pkgs.python311Packages.flask_mail
    pkgs.python311Packages.python_dotenv
    pkgs.python311Packages.itsdangerous
    pkgs.python311Packages.werkzeug
    pkgs.python311Packages.requests
  ];
}