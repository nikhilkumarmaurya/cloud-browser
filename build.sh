#!/bin/bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright Chromium browser (lightweight)
playwright install chromium
playwright install-deps chromium
