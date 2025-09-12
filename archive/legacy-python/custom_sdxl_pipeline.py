# Custom SDXL Pipeline - Production Ready Implementation
# RTX 4090 Optimized Modular SDXL Pipeline
# Version: 2.0.0

"""
Production-ready custom SDXL pipeline implementation.
Modular design optimized for RTX 4090 with advanced features.
"""

import torch
import logging
from typing import Dict, Optional, Union
from PIL import Image
import sys
import os

# Add the sdxl_pipeline module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'sdxl_pipeline'))

try:
    from sdxl_pipeline import (
        PipelineConfig, GPUMode, PrecisionMode,
        get_optimal_rtx4090_config, log_system_info,
        performance_monitor
    )
    from sdxl_pipeline.pipeline import SDXLPipeline, GenerationParams, GenerationResult
    from sdxl_pipeline.text_encoder import SDXLTextEncoder
    from sdxl_pipeline.unet import SDXLUNet
    from sdxl_pipeline.vae import SDXLVAE
except ImportError as e:
    # Fallback to basic implementation if modules not available
    print(f"Warning: Could not import modular SDXL pipeline: {e}")
    print("Using fallback implementation...")
    
    class PipelineConfig:
        def __init__(self):
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.precision = "fp16"
            self.num_inference_steps = 25
            self.guidance_scale = 7.5
            self.width = 1024
            self.height = 1024
    
    class GenerationParams:
        def __init__(self, prompt, **kwargs):
            self.prompt = prompt
            for k, v in kwargs.items():
                setattr(self, k, v)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomSDXLPipeline:
    """
    Production-ready custom SDXL pipeline for RTX 4090.
    
    Features:
    - Modular design with separate text encoder, UNet, and VAE
    - RTX 4090 specific optimizations
    - Memory management and caching
    - Performance monitoring
    - Fallback CPU support
    - Advanced prompt processing
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None, fallback_mode: bool = False):
        """Initialize the custom SDXL pipeline"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fallback_mode = fallback_mode
        
        # Use provided config or create optimal RTX 4090 config
        if config is None:
            try:
                self.config = get_optimal_rtx4090_config()
            except NameError:
                self.config = PipelineConfig()
        else:
            self.config = config
        
        # Initialize pipeline components
        self.pipeline = None
        self.is_loaded = False
        
        # Performance tracking
        self.generation_count = 0
        self.total_generation_time = 0.0
        
        self.logger.info("Custom SDXL Pipeline initialized")
    
    def load(self) -> bool:
        """Load the SDXL pipeline with error handling"""
        try:
            self.logger.info("Loading Custom SDXL Pipeline...")
            
            # Log system information
            self._log_system_info()
            
            if not self.fallback_mode:
                # Try to load full modular pipeline
                self.pipeline = SDXLPipeline(self.config)
                self.pipeline.load()
                self.logger.info("Modular SDXL pipeline loaded successfully")
            else:
                # Load fallback implementation
                self._load_fallback_pipeline()
                self.logger.info("Fallback SDXL pipeline loaded")
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load SDXL pipeline: {e}")
            
            # Try fallback if not already in fallback mode
            if not self.fallback_mode:
                self.logger.info("Attempting fallback pipeline...")
                self.fallback_mode = True
                return self._load_fallback_pipeline()
            
            return False
    
    def _load_fallback_pipeline(self) -> bool:
        """Load a simple fallback pipeline"""
        try:
            # This is a placeholder for a basic diffusers pipeline
            from diffusers import StableDiffusionXLPipeline
            
            self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                use_safetensors=True
            )
            
            if torch.cuda.is_available():
                self.pipeline = self.pipeline.to("cuda")
                
            self.logger.info("Fallback pipeline loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Fallback pipeline failed to load: {e}")
            return False
    
    def _log_system_info(self):
        """Log system information for debugging"""
        try:
            log_system_info()
        except NameError:
            # Basic system info if modular function not available
            self.logger.info("=== System Information ===")
            self.logger.info(f"PyTorch version: {torch.__version__}")
            self.logger.info(f"CUDA available: {torch.cuda.is_available()}")
            
            if torch.cuda.is_available():
                self.logger.info(f"GPU: {torch.cuda.get_device_name()}")
                memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
                self.logger.info(f"GPU Memory: {memory_gb:.1f}GB")
    
    def generate(self, prompt: str, **kwargs) -> Union[Image.Image, None]:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            **kwargs: Additional generation parameters
            
        Returns:
            PIL Image or None if generation failed
        """
        if not self.is_loaded:
            self.logger.error("Pipeline not loaded. Call load() first.")
            return None
        
        try:
            start_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            end_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            
            self.logger.info(f"Generating image: '{prompt[:50]}...'")
            
            if start_time:
                start_time.record()
            
            # Use modular pipeline if available
            if hasattr(self.pipeline, 'generate') and not self.fallback_mode:
                # Create generation parameters
                params = GenerationParams(prompt=prompt, **kwargs)
                result = self.pipeline.generate(params)
                image = result.image
                generation_time = result.generation_time
            else:
                # Use fallback pipeline
                generation_kwargs = {
                    'prompt': prompt,
                    'num_inference_steps': kwargs.get('num_inference_steps', 25),
                    'guidance_scale': kwargs.get('guidance_scale', 7.5),
                    'width': kwargs.get('width', 1024),
                    'height': kwargs.get('height', 1024)
                }
                
                if 'seed' in kwargs:
                    generator = torch.Generator(device=self.pipeline.device)
                    generator.manual_seed(kwargs['seed'])
                    generation_kwargs['generator'] = generator
                
                result = self.pipeline(**generation_kwargs)
                image = result.images[0]
                generation_time = 0.0  # Not tracked in fallback mode
            
            if end_time:
                end_time.record()
                torch.cuda.synchronize()
                if generation_time == 0.0:
                    generation_time = start_time.elapsed_time(end_time) / 1000.0
            
            # Update statistics
            self.generation_count += 1
            self.total_generation_time += generation_time
            
            self.logger.info(f"Image generated successfully in {generation_time:.2f}s")
            return image
            
        except Exception as e:
            self.logger.error(f"Image generation failed: {e}")
            return None
    
    def generate_batch(self, prompts: list, **kwargs) -> list:
        """Generate multiple images from a list of prompts"""
        results = []
        
        self.logger.info(f"Generating {len(prompts)} images...")
        
        for i, prompt in enumerate(prompts):
            self.logger.info(f"Generating image {i+1}/{len(prompts)}")
            
            image = self.generate(prompt, **kwargs)
            results.append(image)
        
        return results
    
    def benchmark(self, num_runs: int = 3) -> Dict[str, float]:
        """Run performance benchmark"""
        if not self.is_loaded:
            self.logger.error("Pipeline not loaded. Call load() first.")
            return {}
        
        self.logger.info(f"Running benchmark with {num_runs} generations...")
        
        test_prompts = [
            "a fantasy sword with magical runes",
            "futuristic robot warrior",
            "medieval castle on a hill"
        ]
        
        times = []
        
        for i in range(num_runs):
            prompt = test_prompts[i % len(test_prompts)]
            
            start_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            end_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            
            if start_time:
                start_time.record()
            
            image = self.generate(prompt, num_inference_steps=20)
            
            if end_time:
                end_time.record()
                torch.cuda.synchronize()
                elapsed = start_time.elapsed_time(end_time) / 1000.0
                times.append(elapsed)
            
            if image:
                self.logger.info(f"Benchmark run {i+1}: Success")
            else:
                self.logger.warning(f"Benchmark run {i+1}: Failed")
        
        if times:
            avg_time = sum(times) / len(times)
            results = {
                "average_time": avg_time,
                "min_time": min(times),
                "max_time": max(times),
                "images_per_minute": 60.0 / avg_time if avg_time > 0 else 0.0,
                "total_generations": self.generation_count,
                "total_time": self.total_generation_time
            }
        else:
            results = {"error": "No successful generations"}
        
        self.logger.info(f"Benchmark results: {results}")
        return results
    
    def get_pipeline_info(self) -> Dict:
        """Get information about the loaded pipeline"""
        info = {
            "loaded": self.is_loaded,
            "fallback_mode": self.fallback_mode,
            "generation_count": self.generation_count,
            "total_time": self.total_generation_time,
            "average_time": self.total_generation_time / max(1, self.generation_count)
        }
        
        if self.is_loaded and hasattr(self.pipeline, 'get_system_info'):
            try:
                info.update(self.pipeline.get_system_info())
            except Exception as e:
                self.logger.warning(f"Could not get system info: {e}")
        
        return info
    
    def cleanup(self):
        """Clean up GPU memory and resources"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        if hasattr(self.pipeline, 'cleanup'):
            self.pipeline.cleanup()
        
        self.logger.info("Pipeline cleanup completed")


# Factory function for easy initialization
def create_custom_sdxl_pipeline(config: Optional[PipelineConfig] = None) -> CustomSDXLPipeline:
    """
    Create and load a custom SDXL pipeline.
    
    Args:
        config: Optional pipeline configuration
        
    Returns:
        Loaded CustomSDXLPipeline instance
    """
    pipeline = CustomSDXLPipeline(config)
    success = pipeline.load()
    
    if not success:
        logger.error("Failed to load pipeline")
        return None
    
    return pipeline


# Test function
def test_pipeline():
    """Test the custom SDXL pipeline"""
    logger.info("Testing Custom SDXL Pipeline...")
    
    # Create pipeline
    pipeline = create_custom_sdxl_pipeline()
    
    if pipeline is None:
        logger.error("Failed to create pipeline")
        return False
    
    # Test generation
    test_prompt = "a magical sword glowing with blue energy, fantasy art, detailed"
    image = pipeline.generate(test_prompt)
    
    if image:
        logger.info(f"Test generation successful! Image size: {image.size}")
        
        # Run benchmark
        benchmark_results = pipeline.benchmark(2)
        logger.info(f"Benchmark: {benchmark_results}")
        
        # Get pipeline info
        info = pipeline.get_pipeline_info()
        logger.info(f"Pipeline info: {info}")
        
        return True
    else:
        logger.error("Test generation failed")
        return False


if __name__ == "__main__":
    # Run test
    success = test_pipeline()
    
    if success:
        print("✅ Custom SDXL Pipeline test completed successfully!")
    else:
        print("❌ Custom SDXL Pipeline test failed!")
