FROM node:20-slim AS builder

ARG COMMIT=bd86e1f

WORKDIR /app

RUN apt-get update && apt-get install -y git sed && rm -rf /var/lib/apt/lists/*

RUN git clone --recurse-submodules https://github.com/billsonnn/nitro-converter.git .
RUN git switch -c habbo-room-content $COMMIT
RUN sed -i 's/const skip = (bundle || extract || convertSwf || true);/const skip = (bundle || extract || convertSwf);/' ./src/Main.ts
RUN yarn install
RUN yarn build

ENTRYPOINT ["node", "/app/dist/Main.js"]