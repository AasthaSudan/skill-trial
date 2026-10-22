$ErrorActionPreference = 'Stop'
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop before setting up the runner.' }
foreach ($image in @('python:3.12-alpine', 'node:22-alpine', 'eclipse-temurin:21-jdk-alpine')) {
    docker pull $image
    if ($LASTEXITCODE -ne 0) { throw "Could not pull $image" }
}
