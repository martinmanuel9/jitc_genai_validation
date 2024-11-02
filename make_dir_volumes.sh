#!/bin/bash

# Define the base directory
BASE_DIR="/jitc_genai_validation"
makdir -p $BASE_DIR/volumes
mkdir -p $BASE_DIR/volumes/milvus
mkdir -p $BASE_DIR/volumes/milvus/conf
mkdir -p $BASE_DIR/volumes/milvus/db
mkdir -p $BASE_DIR/volumes/milvus/logs
mkdir -p $BASE_DIR/volumes/milvus/wal
mkdir -p $BASE_DIR/volumes/postgres

echo "Directories created and permissions set."