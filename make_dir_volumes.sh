#!/bin/bash

# Define the base directory
BASE_DIR="/jitc_genai_validation"
makdir -p $BASE_DIR/volumes
mkdir -p $BASE_DIR/volumes/postgres

echo "Directories created and permissions set."