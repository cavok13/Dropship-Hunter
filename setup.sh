#!/bin/bash
echo "🔧 Setting up Dropship Hunter..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p data
echo "✓ Setup complete. Edit config.yaml then run: python main.py --test"
