"""
GPU Acceleration Module
Provides automatic GPU detection and fallback to CPU
Optimizes model loading and inference across the application
"""
import torch
import os
from typing import Optional, Tuple


class GPUAccelerator:
    """Singleton class for GPU acceleration management"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPUAccelerator, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._detect_hardware()
            self._configure_environment()
            GPUAccelerator._initialized = True
    
    def _detect_hardware(self):
        """Detect available hardware and capabilities"""
        self.cuda_available = torch.cuda.is_available()
        self.device_name = "cpu"
        self.device_type = "cpu"
        self.gpu_memory = 0
        self.gpu_name = "None"
        
        if self.cuda_available:
            try:
                self.device_name = "cuda"
                self.device_type = "cuda"
                self.gpu_name = torch.cuda.get_device_name(0)
                self.gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                
                print("\n" + "="*60)
                print("🚀 GPU ACCELERATION ENABLED")
                print("="*60)
                print(f"   GPU: {self.gpu_name}")
                print(f"   Memory: {self.gpu_memory:.2f} GB")
                print(f"   CUDA Version: {torch.version.cuda}")
                print(f"   PyTorch Version: {torch.__version__}")
                print("="*60 + "\n")
                
            except Exception as e:
                print(f"⚠️ GPU detected but initialization failed: {e}")
                print("   Falling back to CPU")
                self.cuda_available = False
                self.device_name = "cpu"
                self.device_type = "cpu"
        else:
            print("\n" + "="*60)
            print("💻 CPU MODE")
            print("="*60)
            print("   No GPU detected - using CPU")
            print("   For faster performance, install CUDA-enabled PyTorch:")
            print("   pip install torch --index-url https://download.pytorch.org/whl/cu118")
            print("="*60 + "\n")
    
    def _configure_environment(self):
        """Configure environment variables for optimal performance"""
        if self.cuda_available:
            # Enable TF32 for faster computation on Ampere GPUs
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            
            # Enable cuDNN auto-tuner for optimal performance
            torch.backends.cudnn.benchmark = True
            
            # Set memory allocation strategy
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
        else:
            # CPU optimizations
            # Use all available CPU cores
            torch.set_num_threads(os.cpu_count() or 4)
    
    def get_device(self) -> str:
        """Get the device string for PyTorch ('cuda' or 'cpu')"""
        return self.device_name
    
    def get_device_for_transformers(self) -> int:
        """Get device ID for transformers library (0 for GPU, -1 for CPU)"""
        return 0 if self.cuda_available else -1
    
    def get_torch_dtype(self) -> torch.dtype:
        """Get optimal dtype for the current device"""
        if self.cuda_available:
            # Use float16 on GPU for faster inference
            return torch.float16
        else:
            # Use float32 on CPU for stability
            return torch.float32
    
    def get_device_map(self) -> Optional[str]:
        """Get device map for model loading"""
        if self.cuda_available:
            return "auto"  # Automatically distribute across available GPUs
        return None
    
    def optimize_model(self, model):
        """Apply optimizations to a loaded model"""
        if self.cuda_available:
            try:
                # Move model to GPU
                model = model.to(self.device_name)
                
                # Enable gradient checkpointing if available (saves memory)
                if hasattr(model, 'gradient_checkpointing_enable'):
                    model.gradient_checkpointing_enable()
                
                # Set to eval mode for inference
                model.eval()
                
                print(f"✅ Model optimized for GPU ({self.gpu_name})")
                
            except Exception as e:
                print(f"⚠️ GPU optimization failed: {e}")
                print("   Model will run on CPU")
                model = model.to("cpu")
        else:
            # CPU optimizations
            model.eval()
            print("✅ Model optimized for CPU")
        
        return model
    
    def load_sentence_transformer(self, model_name: str, **kwargs):
        """Load SentenceTransformer with GPU acceleration"""
        try:
            from sentence_transformers import SentenceTransformer
            
            print(f"📦 Loading {model_name}...")
            
            # Load model with device specification
            device = self.get_device()
            model = SentenceTransformer(model_name, device=device, **kwargs)
            
            if self.cuda_available:
                print(f"✅ {model_name} loaded on GPU")
            else:
                print(f"✅ {model_name} loaded on CPU")
            
            return model
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("   Attempting CPU fallback...")
            
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(model_name, device="cpu", **kwargs)
                print(f"✅ {model_name} loaded on CPU (fallback)")
                return model
            except Exception as e2:
                print(f"❌ CPU fallback also failed: {e2}")
                raise
    
    def get_batch_size(self, default_cpu: int = 8, default_gpu: int = 32) -> int:
        """Get optimal batch size based on available hardware"""
        if self.cuda_available:
            # Adjust based on GPU memory
            if self.gpu_memory >= 8:
                return default_gpu * 2  # 64 for high-end GPUs
            elif self.gpu_memory >= 4:
                return default_gpu  # 32 for mid-range GPUs
            else:
                return default_gpu // 2  # 16 for low-end GPUs
        else:
            return default_cpu
    
    def clear_cache(self):
        """Clear GPU cache to free memory"""
        if self.cuda_available:
            torch.cuda.empty_cache()
            print("🗑️ GPU cache cleared")
    
    def get_memory_info(self) -> Tuple[float, float]:
        """Get GPU memory usage (allocated, total) in GB"""
        if self.cuda_available:
            allocated = torch.cuda.memory_allocated(0) / (1024**3)
            total = self.gpu_memory
            return allocated, total
        return 0.0, 0.0
    
    def print_memory_usage(self):
        """Print current GPU memory usage"""
        if self.cuda_available:
            allocated, total = self.get_memory_info()
            percentage = (allocated / total) * 100 if total > 0 else 0
            print(f"📊 GPU Memory: {allocated:.2f}GB / {total:.2f}GB ({percentage:.1f}%)")


# Global singleton instance
_gpu_accelerator = None

def get_gpu_accelerator() -> GPUAccelerator:
    """Get or create the global GPU accelerator instance"""
    global _gpu_accelerator
    if _gpu_accelerator is None:
        _gpu_accelerator = GPUAccelerator()
    return _gpu_accelerator


# Convenience functions
def get_device() -> str:
    """Get the device string ('cuda' or 'cpu')"""
    return get_gpu_accelerator().get_device()


def get_device_for_transformers() -> int:
    """Get device ID for transformers (0 for GPU, -1 for CPU)"""
    return get_gpu_accelerator().get_device_for_transformers()


def get_torch_dtype() -> torch.dtype:
    """Get optimal dtype for current device"""
    return get_gpu_accelerator().get_torch_dtype()


def is_gpu_available() -> bool:
    """Check if GPU is available"""
    return get_gpu_accelerator().cuda_available


def load_sentence_transformer(model_name: str, **kwargs):
    """Load SentenceTransformer with automatic GPU acceleration"""
    return get_gpu_accelerator().load_sentence_transformer(model_name, **kwargs)


def get_optimal_batch_size(default_cpu: int = 8, default_gpu: int = 32) -> int:
    """Get optimal batch size for current hardware"""
    return get_gpu_accelerator().get_batch_size(default_cpu, default_gpu)


if __name__ == "__main__":
    # Test the GPU accelerator
    gpu = get_gpu_accelerator()
    
    print("\nHardware Information:")
    print(f"  Device: {gpu.get_device()}")
    print(f"  GPU Available: {gpu.cuda_available}")
    print(f"  Optimal Batch Size: {gpu.get_batch_size()}")
    
    if gpu.cuda_available:
        gpu.print_memory_usage()
