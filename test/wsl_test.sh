#!/bin/bash

echo "Running WSL-based integration test for Linux setup..."

# Path to the project in WSL
WSL_PATH="/mnt/c/Users/tyler/Documents/devel/github/ollama"

# Run the Linux setup in WSL Ubuntu
wsl -d Ubuntu bash -c "
cd $WSL_PATH/linux
chmod +x setup.sh
echo 'Running setup.sh in WSL...'
./setup.sh
echo 'Setup completed. Checking services...'
docker ps
echo 'Stopping services...'
docker-compose down
echo 'WSL test completed.'
"

echo "WSL test finished."