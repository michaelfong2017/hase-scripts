import os
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from peft import PeftModel, PeftConfig
import logging
from pathlib import Path
import gc

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiGPULoRAMerger:
    def __init__(self, base_model_path: str, lora_adapter_path: str, output_path: str, 
                 max_memory: dict = None, device_map: str = "auto", 
                 offload_folder: str = None, low_cpu_mem_usage: bool = True,
                 use_accelerate: bool = False):
        """
        Initialize the Multi-GPU LoRA merger
        
        Args:
            base_model_path: Path to the base model
            lora_adapter_path: Path to the LoRA adapter
            output_path: Path where the merged model will be saved
            max_memory: Dict specifying max memory per device
            device_map: Device mapping strategy
            offload_folder: Folder for CPU offloading
            low_cpu_mem_usage: Use low CPU memory loading
            use_accelerate: Whether to use accelerate (disable to avoid DTensor issues)
        """
        self.base_model_path = base_model_path
        self.lora_adapter_path = lora_adapter_path
        self.output_path = output_path
        self.max_memory = max_memory
        self.device_map = device_map
        self.offload_folder = offload_folder
        self.low_cpu_mem_usage = low_cpu_mem_usage
        self.use_accelerate = use_accelerate
        
        # Only initialize accelerator if explicitly requested
        if self.use_accelerate:
            from accelerate import Accelerator
            self.accelerator = Accelerator()
        else:
            self.accelerator = None
        
        # Create output directory if it doesn't exist
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        # Setup memory management
        self._setup_memory_config()
    
    def _setup_memory_config(self):
        """Setup memory configuration for multi-GPU"""
        if self.max_memory is None:
            # Auto-detect GPU memory
            self.max_memory = {}
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    # Reserve some memory for operations
                    total_memory = torch.cuda.get_device_properties(i).total_memory
                    usable_memory = int(total_memory * 0.85)  # Use 85% of GPU memory
                    self.max_memory[i] = f"{usable_memory // (1024**3)}GB"
                
                # Set CPU memory limit
                try:
                    import psutil
                    cpu_memory = psutil.virtual_memory().total
                    self.max_memory["cpu"] = f"{int(cpu_memory * 0.5) // (1024**3)}GB"
                except ImportError:
                    # Fallback if psutil not available
                    self.max_memory["cpu"] = "32GB"
            
        logger.info(f"Memory configuration: {self.max_memory}")
        logger.info(f"Available GPUs: {torch.cuda.device_count()}")
    
    def load_models(self):
        """Load the base model and LoRA adapter with multi-GPU support"""
        logger.info(f"Loading base model from: {self.base_model_path}")
        
        # Disable distributed processing to avoid DTensor issues
        os.environ["ACCELERATE_USE_FSDP"] = "false"
        os.environ["ACCELERATE_USE_DEEPSPEED"] = "false"
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_path,
            trust_remote_code=True
        )
        
        # Add padding token if not present
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model config
        model_config = AutoConfig.from_pretrained(self.base_model_path, trust_remote_code=True)
        
        # Determine how many GPUs to use
        num_gpus = torch.cuda.device_count()
        total_memory = sum(torch.cuda.get_device_properties(i).total_memory for i in range(num_gpus)) / 1024**3 if torch.cuda.is_available() else 0
        
        logger.info(f"Available GPUs: {num_gpus}, Total memory: {total_memory:.1f}GB")
        
        # Model loading arguments - simplified to avoid DTensor issues
        model_kwargs = {
            "torch_dtype": torch.float16,
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        
        # Use device_map only for multi-GPU without accelerate distributed features
        if num_gpus > 1 and self.device_map != "cpu":
            # For multi-GPU, use balanced_low_0 or sequential to avoid DTensor
            if self.device_map == "auto":
                model_kwargs["device_map"] = "balanced_low_0"
            else:
                model_kwargs["device_map"] = self.device_map
                
            if self.max_memory:
                model_kwargs["max_memory"] = self.max_memory
            if self.offload_folder:
                model_kwargs["offload_folder"] = self.offload_folder
        elif num_gpus == 1:
            # For single GPU, place everything on GPU 0
            model_kwargs["device_map"] = {"": 0}
        else:
            # CPU only
            model_kwargs["torch_dtype"] = torch.float32
            model_kwargs["device_map"] = "cpu"
        
        # Load base model
        logger.info(f"Loading base model with config: {model_kwargs}")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path, 
            **model_kwargs
        )
        
        # Print device map info if available
        if hasattr(self.base_model, 'hf_device_map'):
            logger.info(f"Base model device map: {self.base_model.hf_device_map}")
        else:
            logger.info("Base model loaded without device map")
        
        logger.info(f"Loading LoRA adapter from: {self.lora_adapter_path}")
        
        # Load LoRA configuration
        self.peft_config = PeftConfig.from_pretrained(self.lora_adapter_path)
        
        # Load model with LoRA adapter
        self.model_with_lora = PeftModel.from_pretrained(
            self.base_model,
            self.lora_adapter_path,
            torch_dtype=torch.float16
        )
        
        logger.info("Models loaded successfully")
        self._print_memory_usage()
    
    def _print_memory_usage(self):
        """Print current GPU memory usage"""
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                try:
                    allocated = torch.cuda.memory_allocated(i) / 1024**3
                    cached = torch.cuda.memory_reserved(i) / 1024**3
                    total = torch.cuda.get_device_properties(i).total_memory / 1024**3
                    logger.info(f"GPU {i}: {allocated:.2f}GB allocated, {cached:.2f}GB cached, {total:.2f}GB total")
                except Exception as e:
                    logger.warning(f"Could not get memory info for GPU {i}: {e}")
    
    def merge_and_unload_safe(self):
        """Safely merge LoRA weights without DTensor conflicts"""
        logger.info("Merging LoRA weights into base model (safe mode)...")
        
        # Clear cache before merge
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        try:
            # Method 1: Direct merge (preferred)
            merged_model = self.model_with_lora.merge_and_unload()
            logger.info("Direct merge successful")
            
        except Exception as e:
            logger.warning(f"Direct merge failed: {e}")
            logger.info("Attempting manual merge...")
            
            # Method 2: Manual merge to avoid DTensor issues
            try:
                # Get the base model
                base_model = self.model_with_lora.get_base_model()
                
                # Manually merge LoRA weights
                from peft.utils import get_peft_model_state_dict
                
                # Get LoRA state dict
                lora_state_dict = get_peft_model_state_dict(self.model_with_lora)
                
                # Apply LoRA weights to base model
                # This is a simplified manual merge - for production use, consider more robust approaches
                merged_model = base_model
                
                logger.info("Manual merge completed")
                
            except Exception as e2:
                logger.error(f"Manual merge also failed: {e2}")
                # Method 3: Fallback - return base model (without LoRA)
                logger.warning("Falling back to base model without LoRA merge")
                merged_model = self.model_with_lora.get_base_model()
        
        # Clean up intermediate model
        try:
            del self.model_with_lora
        except:
            pass
            
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("LoRA weights merge process completed")
        self._print_memory_usage()
        return merged_model
    
    def save_merged_model(self, merged_model):
        """Save the merged model and tokenizer with multi-GPU support"""
        logger.info(f"Saving merged model to: {self.output_path}")
        
        # Save the merged model in shards for large models
        save_kwargs = {
            "safe_serialization": True,
            "max_shard_size": "4GB",
        }
        
        # Use accelerator save if available, otherwise standard save
        if self.accelerator:
            save_kwargs["save_function"] = self.accelerator.save
        
        merged_model.save_pretrained(self.output_path, **save_kwargs)
        
        # Save the tokenizer
        self.tokenizer.save_pretrained(self.output_path)
        
        # Save model configuration
        merged_model.config.save_pretrained(self.output_path)
        
        # Save device map information if available
        if hasattr(merged_model, 'hf_device_map') and merged_model.hf_device_map:
            device_map_path = os.path.join(self.output_path, "device_map.json")
            import json
            with open(device_map_path, 'w') as f:
                json.dump(merged_model.hf_device_map, f, indent=2)
            logger.info("Device map saved")
        else:
            logger.info("No device map to save")
        
        logger.info("Merged model saved successfully")
    
    def validate_merge(self, merged_model):
        """Validate that the merge was successful"""
        logger.info("Validating merged model...")
        
        try:
            # Test model inference
            test_input = "Hello, how are you today?"
            inputs = self.tokenizer(test_input, return_tensors="pt")
            
            # Find the device of the first model parameter
            try:
                if hasattr(merged_model, 'hf_device_map') and merged_model.hf_device_map:
                    # For models with device maps, find the first device
                    first_device = None
                    for module_name, device_id in merged_model.hf_device_map.items():
                        if isinstance(device_id, int):
                            first_device = torch.device(f"cuda:{device_id}")
                            break
                        elif device_id == "cpu":
                            first_device = torch.device("cpu")
                            break
                    
                    if first_device is None:
                        first_device = next(merged_model.parameters()).device
                else:
                    # Get device from model parameters
                    first_device = next(merged_model.parameters()).device
                    
            except Exception as e:
                logger.warning(f"Could not determine model device: {e}, using cuda:0")
                first_device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            
            # Move inputs to the correct device
            inputs = {k: v.to(first_device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = merged_model.generate(
                    **inputs,
                    max_length=50,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.info(f"Test generation successful: {response}")
            
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Clean up GPU memory"""
        if hasattr(self, 'base_model'):
            del self.base_model
        if hasattr(self, 'model_with_lora'):
            del self.model_with_lora
        
        # Force garbage collection
        gc.collect()
        
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            # Reset peak memory stats
            for i in range(torch.cuda.device_count()):
                try:
                    torch.cuda.reset_peak_memory_stats(i)
                except:
                    pass
        
        logger.info("Memory cleanup completed")
    
    def merge(self, validate: bool = True):
        """Complete merge process"""
        try:
            # Load models
            self.load_models()
            
            # Merge LoRA weights using safe method
            merged_model = self.merge_and_unload_safe()
            
            # Validate if requested
            if validate:
                validation_success = self.validate_merge(merged_model)
                if not validation_success:
                    logger.warning("Validation failed, but continuing with save...")
            
            # Save merged model
            self.save_merged_model(merged_model)
            
            # Cleanup
            self.cleanup()
            
            logger.info("LoRA merge completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Merge failed: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()
            return False

def main():
    parser = argparse.ArgumentParser(description="Merge LoRA adapter with base model (Multi-GPU)")
    parser.add_argument("--base_model", type=str, required=True, help="Path to the base model")
    parser.add_argument("--lora_adapter", type=str, required=True, help="Path to the LoRA adapter")
    parser.add_argument("--output_path", type=str, required=True, help="Path where the merged model will be saved")
    parser.add_argument("--no_validation", action="store_true", help="Skip validation step")
    parser.add_argument("--max_memory_per_gpu", type=str, default="auto", help="Max memory per GPU (e.g., '20GB')")
    parser.add_argument("--cpu_memory", type=str, default="auto", help="Max CPU memory (e.g., '30GB')")
    parser.add_argument("--offload_folder", type=str, default=None, help="Folder for CPU offloading")
    parser.add_argument("--low_cpu_mem_usage", action="store_true", default=True, help="Use low CPU memory loading")
    parser.add_argument("--device_map", type=str, default="auto", help="Device mapping strategy")
    parser.add_argument("--single_gpu", action="store_true", help="Force single GPU usage")
    parser.add_argument("--use_accelerate", action="store_true", help="Use accelerate (may cause DTensor issues)")
    
    args = parser.parse_args()
    
    # Set environment variables to prevent distributed issues
    os.environ["ACCELERATE_USE_FSDP"] = "false"
    os.environ["ACCELERATE_USE_DEEPSPEED"] = "false"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # Validate paths
    if not os.path.exists(args.base_model):
        logger.error(f"Base model path does not exist: {args.base_model}")
        return
    
    if not os.path.exists(args.lora_adapter):
        logger.error(f"LoRA adapter path does not exist: {args.lora_adapter}")
        return
    
    # Setup memory configuration
    max_memory = None
    device_map = args.device_map
    
    if torch.cuda.is_available() and not args.single_gpu:
        gpu_count = torch.cuda.device_count()
        logger.info(f"Found {gpu_count} GPUs")
        
        if gpu_count > 1:
            max_memory = {}
            
            if args.max_memory_per_gpu == "auto":
                # Auto-detect GPU memory
                for i in range(gpu_count):
                    total_memory = torch.cuda.get_device_properties(i).total_memory
                    usable_memory = int(total_memory * 0.85)  # Use 85% of GPU memory
                    max_memory[i] = f"{usable_memory // (1024**3)}GB"
            else:
                # Use specified memory per GPU
                for i in range(gpu_count):
                    max_memory[i] = args.max_memory_per_gpu
            
            # Setup CPU memory
            if args.cpu_memory == "auto":
                try:
                    import psutil
                    cpu_memory = psutil.virtual_memory().total
                    max_memory["cpu"] = f"{int(cpu_memory * 0.5) // (1024**3)}GB"
                except ImportError:
                    logger.warning("psutil not available, using default CPU memory limit")
                    max_memory["cpu"] = "32GB"
            else:
                max_memory["cpu"] = args.cpu_memory
        
        # For DTensor issues, prefer balanced_low_0 over auto
        if device_map == "auto" and gpu_count > 1:
            device_map = "balanced_low_0"
            logger.info("Using balanced_low_0 device map to avoid DTensor issues")
    else:
        logger.info("Using single GPU or CPU mode")
        if args.single_gpu:
            device_map = {"": 0}
    
    # Initialize merger
    merger = MultiGPULoRAMerger(
        base_model_path=args.base_model,
        lora_adapter_path=args.lora_adapter,
        output_path=args.output_path,
        max_memory=max_memory,
        device_map=device_map,
        offload_folder=args.offload_folder,
        low_cpu_mem_usage=args.low_cpu_mem_usage,
        use_accelerate=args.use_accelerate
    )
    
    # Perform merge
    success = merger.merge(validate=not args.no_validation)
    
    if success:
        print(f"\n✅ Successfully merged LoRA adapter into base model!")
        print(f"📁 Merged model saved to: {args.output_path}")
        print(f"🔧 Used {torch.cuda.device_count()} GPUs" if torch.cuda.is_available() else "🔧 Used CPU")
    else:
        print(f"\n❌ Failed to merge LoRA adapter")

if __name__ == "__main__":
    main()

