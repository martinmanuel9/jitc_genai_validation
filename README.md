# JITC Gen AI Validation Tool

This project is to provide a validation suite in which inteoperability of systems is evaluated.

The goal is to receive messages and validate that the messages are in accordance with the standards such as IEEE 802.11 or MIL-STD

# Set Up

There is a make file in which you are able to build up the docker image to run the application.
The chatbot runs on a FastAPI and uvicorn.

## Build & Bringing the Environment Up

Run the following command to build docker images

```
make build
```
1. Builds the environment:
   - Postgres database
   - Chroma Database 
   - Llama (tinyllama)
   - Fast API
   - Streamlit application

```
make compose-up
```

Brings docker images up

The following command puts everything together

```
make all
```


# Migrate openai 
After running environment need to run
```
openai migrate 
```