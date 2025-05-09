#!/bin/bash

echo "Setting up AdBot environment..."

# Create virtual environment
echo "Creating virtual environment..."
python -m venv env

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source env/Scripts/activate
else
    source env/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directories
echo "Creating data directories..."
mkdir -p data/images
mkdir -p data/analytics

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.template .env
    echo "Please edit the .env file to add your API credentials."
fi

# Always enable test account mode for proper functionality
echo "TEST_ACCOUNT=true" >> .env
echo "Enabled test account mode - real posting will be attempted without charges."

# Ask if mock mode should be used (no real API calls)
read -p "Use mock mode for social media posts? This will simulate posting without making real API calls (y/n): " enable_mock
if [[ $enable_mock == "y" || $enable_mock == "Y" ]]; then
    echo "MOCK_SOCIAL=true" >> .env
    echo "Enabled mock mode - no real API calls will be made."
else
    echo "MOCK_SOCIAL=false" >> .env
    echo "Real API calls will be made if credentials are configured."
fi

echo "Setup complete! To start the app, run:"
echo "python -m streamlit run streamlit_app.py" 