#!/bin/bash
cat << 'EOF'
    ______                ______                     
   / ____/(_)_______     / ____/___  _________ ___ 
  / /_   / // ___/ _ \  / /_  / __ \/ ___/ __ `__ \
 / __/  / // /  /  __/ / __/ / /_/ / /  / / / / / /
/_/    /_//_/   \___/ /_/    \____/_/  /_/ /_/ /_/ 
EOF

echo "Checking for required dependencies..."

# Check and install 'make'
if ! command -v make &> /dev/null; then
    echo "'make' could not be found. Attempting to install..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y make
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y make
    elif command -v yum &> /dev/null; then
        sudo yum install -y make
    elif command -v pacman &> /dev/null; then
	sudo pacman -S make 
    else
        echo "Error: Package manager not found. Please install 'make' manually."
        exit 1
    fi
    echo "'make' installed successfully."
fi

if ! command -v docker &> /dev/null; then
    echo "'docker' could not be found. Attempting to install..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    
fi

if ! docker compose version &> /dev/null; then
    echo "'docker compose' plugin not found. Attempting to install..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y docker-compose-plugin
    else
        echo "Please ensure docker-compose is installed."
    fi
fi

echo "============================================"
echo "Building containers..."
echo "============================================"
make build
echo "============================================"
echo "Starting containers..."
echo "============================================"
make up
echo "============================================"
echo "Use make down to stop" 
echo -e "Use docker ps to verify, you should see 2 containers:"
echo -e "\t* fireform-app"
echo -e "\t* ollama/ollama:latest"
docker ps
echo "============================================"
echo "Pulling mistral from ollama"
echo "============================================"
make pull-model
echo "============================================"
echo "Done"
