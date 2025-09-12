REM Test Docker Build - Run this directly in Command Prompt
REM Copy and paste this command:

docker build -f Dockerfile.minimal --build-arg VARIANT=cpu -t gameforge-test:cpu .

REM If that works, try the full build:
REM docker build -f Dockerfile.production.enhanced --build-arg VARIANT=cpu --build-arg BUILD_DATE=2024-01-01T00:00:00Z --build-arg VCS_REF=test --build-arg BUILD_VERSION=test --build-arg PYTHON_VERSION=3.10 -t gameforge-full:cpu .

REM Check the built image:
REM docker images gameforge-test

REM Test the container:
REM docker run --rm gameforge-test:cpu echo "Container test successful"
