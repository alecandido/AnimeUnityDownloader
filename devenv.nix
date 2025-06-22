{ pkgs, ... }:

{
  packages = with pkgs; [
    pre-commit
    poethepoet
  ];

  languages.python = {
    enable = true;
    venv = {
      enable = true;
      requirements = builtins.readFile ./requirements.txt;
    };
  };
}
