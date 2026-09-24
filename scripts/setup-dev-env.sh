#!/usr/bin/env bash
set -euo pipefail
log() { echo -e "\033[0;32m[SETUP]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"
log "Detected OS: $OS"

if [[ "$OS" == "Darwin" ]]; then
    if ! has_cmd brew; then
        log "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew_install() { brew install "$1" 2>/dev/null || true; }
    
    brew_install direnv
    brew_install just
    brew_install pnpm
    brew_install docker
    brew_install kubectl
    brew_install helm
    brew_install cosign
    brew_install dvc
    brew_install jq
    brew_install yq
    brew_install tree
    brew_install fzf
    brew_install ripgrep
    brew_install gh
    
elif [[ "$OS" == "Linux" ]]; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
        curl wget jq git tree direnv ca-certificates gnupg lsb-release \
        fzf ripgrep

    # Just
    if ! has_cmd just; then
        curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
    fi

    # pnpm
    if ! has_cmd pnpm; then
        curl -fsSL https://get.pnpm.io/install.sh | sh -
    fi

    # cosign
    if ! has_cmd cosign; then
        COSIGN_VERSION="v2.2.4"
        curl -L -o /usr/local/bin/cosign \
            "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64"
        chmod +x /usr/local/bin/cosign
    fi

    # kubectl
    if ! has_cmd kubectl; then
        curl -fsSL https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl \
            -o /usr/local/bin/kubectl
        chmod +x /usr/local/bin/kubectl
    fi

    # helm
    if ! has_cmd helm; then
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    fi

    # yq
    if ! has_cmd yq; then
        curl -L https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 \
            -o /usr/local/bin/yq
        chmod +x /usr/local/bin/yq
    fi

    # GitHub CLI
    if ! has_cmd gh; then
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
            sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        sudo apt-get update -qq && sudo apt-get install -y gh
    fi
fi

# Node.js (via nvm if not present)
if ! has_cmd node; then
    log "Installing Node.js via nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    source "$NVM_DIR/nvm.sh"
    nvm install 20
    nvm use 20
fi

# Python 3.12
if ! has_cmd python3.12 && ! python3 --version 2>&1 | grep -q "3.12"; then
    warn "Python 3.12 not found. Install via: pyenv install 3.12"
fi

# Rust
if ! has_cmd rustc; then
    log "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Note: pnpm workspace deps are installed by postCreateCommand
# (avoid duplicate install here)

# Direnv allow
if has_cmd direnv && [[ -f ".envrc" ]]; then
    direnv allow . 2>/dev/null || warn "Run 'direnv allow' manually"
fi

log "✅ Dev environment setup complete!"
log "Next: just up"
