.PHONY: build run clean

# Build the Docker image
build:
	docker build -t jitc-genai-validation .

# Run the Docker container
run:
	docker run -p 8000:8000 jitc-genai-validation

# Clean up Docker images
clean:
	docker rmi jitc-genai-validation

# Build and run in one command
all: build run

# Remove Docker container and image
remove:
	docker ps -q -f ancestor=jitc-genai-validation | xargs -r docker stop
	docker ps -a -q -f ancestor=jitc-genai-validation | xargs -r docker rm
	docker rmi jitc-genai-validation