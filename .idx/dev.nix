# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-23.11"; # or "unstable"
  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.python3
    pkgs.ruff
    pkgs.python311Packages.pip
    pkgs.docker 
  ];
  # Sets environment variables in the workspace
  env = {};
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      "ms-python.python"
      "alefragnani.project-manager"
      "batisteo.vscode-django"
      "charliermarsh.ruff"
      "donjayamanne.git-extension-pack"
      "donjayamanne.githistory"
      "donjayamanne.python-environment-manager"
      "felipecaputo.git-project-manager"
      "GitHub.vscode-pull-request-github"
      "KevinRose.vsc-python-indent"
      "mikestead.dotenv"
      "monokai.theme-monokai-pro-vscode"
      "ms-azuretools.vscode-docker"
      "ms-python.autopep8"
      "ms-python.debugpy"
      "ms-python.isort"
      "ms-python.pylint"
      "PKief.material-icon-theme"
      "qwtel.sqlite-viewer"
      "ziyasal.vscode-open-in-github"
    ];
    workspace = {
      # Runs when a workspace is first created with this `dev.nix` file
      onCreate = {
        create-venv = ''
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
        '';
      };
      # To run something each time the environment is rebuilt, use the `onStart` hook
    };
    # Enable previews and customize configuration
    previews = {
      enable = false;
      previews = {
        web = {
          command = ["./devserver.sh"];
          env = {
            PORT = "$PORT";
          };
          manager = "web";
        };
      };
    };
  };
}
