#!/bin/bash

if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo ".env file not found. Please copy .env.example to .env and configure it."
  exit 1
fi

echo "Starting vLLM container..."
echo "Model: $LLM_MODEL"
echo "Port: 8000"

# Check for GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "Warning: nvidia-smi not found. This script requires an NVIDIA GPU and proper drivers."
    # Continue anyway in case they are set up differently
fi

docker run --rm -it \
  --runtime nvidia \
  --gpus all \
  --network host \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --env HUGGING_FACE_HUB_TOKEN=$HUGGING_FACE_HUB_TOKEN \
  --ipc=host \
  nvcr.io/nvidia/vllm:25.12.post1-py3 \
  vllm serve \
  --model $LLM_MODEL \
  --dtype auto \
  --api-key $LLM_API_KEY \
  --max-model-len $MAX_MODEL_LEN \
  --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
  --port 8000
