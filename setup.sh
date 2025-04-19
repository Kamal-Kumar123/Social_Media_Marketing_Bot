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

echo "Setup complete! To start the app, run:"
echo "python -m streamlit run streamlit_app.py" 