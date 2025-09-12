
"""
GameForge Backend GPU Integration
Updates to gameforge_minimal_server.py for GPU API integration
"""
import asyncio
import aiohttp
import base64
from typing import Optional

class GPUClient:
    """Client for communicating with GPU server"""

    def __init__(self, gpu_endpoint: str):
        self.gpu_endpoint = gpu_endpoint.rstrip('/')
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def health_check(self) -> dict:
        """Check GPU server health"""
        async with self.session.get(f"{self.gpu_endpoint}/health") as response:
            return await response.json()

    async def generate_image(self, prompt: str, **kwargs) -> dict:
        """Generate image via GPU server"""
        payload = {
            "prompt": prompt,
            "negative_prompt": kwargs.get("negative_prompt", ""),
            "width": kwargs.get("width", 1024),
            "height": kwargs.get("height", 1024),
            "num_inference_steps": kwargs.get("steps", 20),
            "guidance_scale": kwargs.get("guidance_scale", 7.5),
            "seed": kwargs.get("seed")
        }

        async with self.session.post(
            f"{self.gpu_endpoint}/generate",
            json=payload
        ) as response:
            return await response.json()

# Add this to your FastAPI app startup
GPU_ENDPOINT = "http://your-vast-gpu-ip:8000"  # Update with actual IP
gpu_client = None

@app.on_event("startup")
async def startup_event():
    global gpu_client
    gpu_client = GPUClient(GPU_ENDPOINT)

# Update your asset generation endpoint
@app.post("/api/assets/generate")
async def generate_asset_endpoint(request: AssetGenerationRequest):
    try:
        async with GPUClient(GPU_ENDPOINT) as client:
            # Generate using GPU server
            result = await client.generate_image(
                prompt=request.prompt,
                width=request.width,
                height=request.height,
                steps=request.num_inference_steps,
                guidance_scale=request.guidance_scale
            )

            if result["success"]:
                # Save image and return asset info
                asset_data = {
                    "id": result["generation_id"],
                    "type": request.asset_type,
                    "prompt": request.prompt,
                    "image_data": result["image_base64"],
                    "processing_time": result["processing_time"],
                    "created_at": datetime.utcnow().isoformat()
                }

                return {"success": True, "asset": asset_data}
            else:
                raise HTTPException(status_code=500, detail=result["error"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
