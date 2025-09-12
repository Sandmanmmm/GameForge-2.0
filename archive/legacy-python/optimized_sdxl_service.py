from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch, io, base64, os, uvicorn, logging, gc, asyncio
from diffusers import DiffusionPipeline
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
MODEL_CACHE = {}
MODEL_ID = 'segmind/SSD-1B'

class ImageRequest(BaseModel):
    prompt: str
    width: int = 512  
    height: int = 512
    steps: int = 20
    guidance_scale: float = 7.5

class ImageResponse(BaseModel):
    image: str
    metadata: dict

async def load_model():
    global MODEL_CACHE
    if 'pipeline' in MODEL_CACHE:
        logger.info(' Model already cached!')
        return
    
    logger.info(f' Loading optimized SDXL model: {MODEL_ID}...')
    pipeline = DiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float32,
        safety_checker=None,
        requires_safety_checker=False
    )
    pipeline = pipeline.to('cpu')
    pipeline.enable_attention_slicing()
    
    MODEL_CACHE['pipeline'] = pipeline
    MODEL_CACHE['model_id'] = MODEL_ID
    logger.info(' SDXL model loaded with caching enabled!')

@asynccontextmanager
async def lifespan(app):
    logger.info(' Starting GameForge SDXL Optimized Service...')
    await load_model()
    yield

app = FastAPI(
    title='GameForge SDXL Optimized',
    version='2.1.0',
    lifespan=lifespan
)

@app.get('/health')
async def health():
    return {
        'status': 'healthy' if 'pipeline' in MODEL_CACHE else 'loading',
        'version': '2.1.0',
        'service': 'sdxl-optimized',
        'models_loaded': 'pipeline' in MODEL_CACHE,
        'model': MODEL_CACHE.get('model_id', 'loading...'),
        'optimization_features': ['model_caching', 'attention_slicing', 'cpu_optimized']
    }

@app.get('/model-status')
async def model_status():
    if 'pipeline' not in MODEL_CACHE:
        raise HTTPException(status_code=503, detail='Model still loading...')
    
    return {
        'loaded': True,
        'model_id': MODEL_CACHE['model_id'],
        'device': 'cpu',
        'optimizations': {
            'attention_slicing': True,
            'model_caching': True,
            'memory_efficient': True
        }
    }

@app.post('/generate', response_model=ImageResponse)
async def generate_image(request: ImageRequest):
    if 'pipeline' not in MODEL_CACHE:
        raise HTTPException(status_code=503, detail='Model still loading, please wait...')
    
    try:
        pipeline = MODEL_CACHE['pipeline']
        
        logger.info(f' Generating: "{request.prompt[:50]}..." ({request.width}x{request.height})')
        
        with torch.inference_mode():
            result = pipeline(
                prompt=request.prompt,
                width=request.width,
                height=request.height,
                num_inference_steps=request.steps,
                guidance_scale=request.guidance_scale,
                output_type='pil'
            )
        
        image = result.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        gc.collect()  # Memory cleanup
        
        logger.info(f' Generated successfully! Image size: {len(img_base64)} chars')
        
        return ImageResponse(
            image=img_base64,
            metadata={
                'prompt': request.prompt,
                'width': request.width,
                'height': request.height,
                'steps': request.steps,
                'guidance_scale': request.guidance_scale,
                'model': MODEL_CACHE['model_id'],
                'device': 'cpu',
                'format': 'PNG',
                'service': 'sdxl-optimized',
                'cached_model': True,
                'optimizations': ['attention_slicing', 'model_caching']
            }
        )
    except Exception as e:
        logger.error(f' Generation failed: {e}')
        gc.collect()
        raise HTTPException(status_code=500, detail=f'Generation failed: {str(e)}')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f' Starting optimized SDXL service on port {port}')
    uvicorn.run(app, host='0.0.0.0', port=port)
