import os
import sys
import signal
import atexit
import psutil
import time
import json
import argparse
from datetime import datetime, timedelta

# CRITICAL: Set these BEFORE importing torch
os.environ["TRION_CACHE_DIR"] = "/tmp"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Fix the memory allocator issue
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512,expandable_segments:False,garbage_collection_threshold:0.8"
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # For debugging

import torch
import pandas as pd
from torch.utils.data import Dataset
import transformers
from transformers import (
    AutoTokenizer,
    AutoConfig,
    TrainingArguments,
    Trainer,
    AutoModelForCausalLM,
    get_linear_schedule_with_warmup,
)
from peft import LoraConfig, TaskType, get_peft_model
from torch.utils.tensorboard import SummaryWriter
from transformers.integrations import TensorBoardCallback
import gc
import traceback

# Global variables for cleanup and metrics
writer = None
trainer = None
model = None
metrics_tracker = None

class MetricsTracker:
    """Comprehensive metrics tracking for training"""
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        """Reset all metrics"""
        self.start_time = time.time()
        self.step_times = {}
        self.gpu_memory_snapshots = {}
        self.cpu_usage_snapshots = {}
        self.training_losses = []  # Only store actual loss values
        self.learning_rates = []
        self.step_durations = []
        self.epoch_metrics = []
        self.resource_usage = {
            'max_gpu_memory': {},
            'avg_cpu_usage': 0,
            'peak_cpu_usage': 0,
            'total_disk_io': {'read': 0, 'write': 0}
        }
        
        # Initialize GPU memory tracking
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                self.resource_usage['max_gpu_memory'][i] = 0
                
        # Get initial system stats
        try:
            self.initial_disk_io = psutil.disk_io_counters()
        except:
            self.initial_disk_io = None
    
    def start_step(self, step_name):
        """Start timing a step"""
        self.step_times[step_name] = {'start': time.time()}
        
    def end_step(self, step_name):
        """End timing a step"""
        if step_name in self.step_times:
            self.step_times[step_name]['end'] = time.time()
            self.step_times[step_name]['duration'] = (
                self.step_times[step_name]['end'] - self.step_times[step_name]['start']
            )
            
    def snapshot_resources(self, label):
        """Take a snapshot of current resource usage"""
        snapshot = {
            'timestamp': time.time(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'gpu_memory': {}
        }
        
        # GPU memory
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / 1024**3
                reserved = torch.cuda.memory_reserved(i) / 1024**3
                snapshot['gpu_memory'][i] = {
                    'allocated_gb': allocated,
                    'reserved_gb': reserved
                }
                
                # Update max GPU memory
                self.resource_usage['max_gpu_memory'][i] = max(
                    self.resource_usage['max_gpu_memory'][i], allocated
                )
        
        self.gpu_memory_snapshots[label] = snapshot
        
        # Update CPU usage tracking
        cpu_usage = psutil.cpu_percent()
        self.resource_usage['peak_cpu_usage'] = max(self.resource_usage['peak_cpu_usage'], cpu_usage)
        
    def log_training_step(self, step, loss, lr, step_duration):
        """Log training step metrics - only call when loss is actually computed"""
        # Ensure loss is a valid number
        if loss is not None and not (isinstance(loss, float) and (loss != loss)):  # Check for NaN
            self.training_losses.append({'step': step, 'loss': float(loss)})
            self.learning_rates.append({'step': step, 'lr': float(lr)})
            self.step_durations.append(float(step_duration))
        
    def log_epoch_metrics(self, epoch, avg_loss, total_steps):
        """Log epoch-level metrics"""
        self.epoch_metrics.append({
            'epoch': epoch,
            'avg_loss': avg_loss,
            'total_steps': total_steps,
            'timestamp': time.time()
        })
        
    def get_training_summary(self):
        """Generate comprehensive training summary with proper NaN handling"""
        total_time = time.time() - self.start_time
        
        # Calculate average metrics with proper handling of empty lists
        avg_step_duration = sum(self.step_durations) / len(self.step_durations) if self.step_durations else 0
        
        # Handle loss calculations properly
        if self.training_losses:
            losses = [l['loss'] for l in self.training_losses]
            min_loss = min(losses)
            final_loss = losses[-1]
            initial_loss = losses[0]
            loss_improvement = initial_loss - final_loss
        else:
            min_loss = final_loss = initial_loss = loss_improvement = 0
        
        # Calculate disk I/O
        try:
            current_disk_io = psutil.disk_io_counters()
            if self.initial_disk_io:
                disk_read = (current_disk_io.read_bytes - self.initial_disk_io.read_bytes) / 1024**3
                disk_write = (current_disk_io.write_bytes - self.initial_disk_io.write_bytes) / 1024**3
            else:
                disk_read = disk_write = 0
        except:
            disk_read = disk_write = 0
            
        # Calculate average CPU usage
        cpu_snapshots = [s['cpu_percent'] for s in self.gpu_memory_snapshots.values()]
        avg_cpu = sum(cpu_snapshots) / len(cpu_snapshots) if cpu_snapshots else 0
        
        summary = {
            'total_training_time_seconds': total_time,
            'total_training_time_formatted': str(timedelta(seconds=int(total_time))),
            'step_timing': dict(self.step_times),
            'training_performance': {
                'total_steps': len(self.training_losses),  # Only count actual optimization steps
                'avg_step_duration_seconds': avg_step_duration,
                'steps_per_second': 1 / avg_step_duration if avg_step_duration > 0 else 0,
                'final_loss': final_loss,
                'min_loss': min_loss,
                'initial_loss': initial_loss,
                'loss_improvement': loss_improvement
            },
            'resource_utilization': {
                'max_gpu_memory_gb': dict(self.resource_usage['max_gpu_memory']),
                'peak_cpu_usage_percent': self.resource_usage['peak_cpu_usage'],
                'avg_cpu_usage_percent': avg_cpu,
                'disk_io_gb': {
                    'read': disk_read,
                    'write': disk_write,
                    'total': disk_read + disk_write
                }
            },
            'epoch_progression': self.epoch_metrics,
            'memory_snapshots': self.gpu_memory_snapshots
        }
        
        return summary

def aggressive_memory_cleanup():
    """Aggressive memory cleanup function"""
    try:
        # Clear Python garbage
        gc.collect()
        gc.collect()
        
        # Clear CUDA cache on all GPUs
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            
            # Synchronize all devices
            torch.cuda.synchronize()
            
        # Force Python garbage collection again
        gc.collect()
        
    except Exception as e:
        print(f"Error in aggressive cleanup: {e}")

def print_detailed_memory_usage():
    """Print detailed memory usage for debugging"""
    if torch.cuda.is_available():
        print("\n🔍 DETAILED GPU MEMORY ANALYSIS:")
        print("-" * 50)
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            reserved = torch.cuda.memory_reserved(i) / 1024**3
            max_reserved = torch.cuda.max_memory_reserved(i) / 1024**3
            
            try:
                memory_summary = torch.cuda.memory_summary(i)
                print(f"\nGPU {i} Memory Summary:")
                print(f"  Allocated: {allocated:.2f}GB")
                print(f"  Reserved: {reserved:.2f}GB") 
                print(f"  Max Reserved: {max_reserved:.2f}GB")
                print(f"  Memory Summary:\n{memory_summary}")
            except:
                print(f"GPU {i}: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")

def print_metrics_report(metrics_summary, config):
    """Print a comprehensive metrics report"""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE TRAINING METRICS REPORT")
    print("="*80)
    
    # Training Overview
    print("\n🎯 TRAINING OVERVIEW")
    print("-" * 40)
    perf = metrics_summary['training_performance']
    print(f"📅 Total Training Time: {metrics_summary['total_training_time_formatted']}")
    print(f"🔢 Total Training Steps: {perf['total_steps']:,}")
    print(f"⚡ Average Step Duration: {perf['avg_step_duration_seconds']:.3f} seconds")
    print(f"🚀 Steps per Second: {perf['steps_per_second']:.2f}")
    
    # Only show loss metrics if we have valid data
    if perf['total_steps'] > 0:
        print(f"📈 Initial Loss: {perf['initial_loss']:.4f}")
        print(f"🏁 Final Loss: {perf['final_loss']:.4f}")
        print(f"🎯 Best Loss: {perf['min_loss']:.4f}")
        print(f"📉 Loss Improvement: {perf['loss_improvement']:.4f}")
        
        # Loss improvement percentage
        if perf['initial_loss'] > 0:
            improvement_pct = (perf['loss_improvement'] / perf['initial_loss']) * 100
            print(f"📊 Loss Improvement: {improvement_pct:.2f}%")
    else:
        print("⚠️ No training steps recorded")
    
    # Step Timing Breakdown
    print("\n⏱️  STEP TIMING BREAKDOWN")
    print("-" * 40)
    step_times = metrics_summary['step_timing']
    for step_name, timing in step_times.items():
        if 'duration' in timing:
            minutes = int(timing['duration'] // 60)
            seconds = timing['duration'] % 60
            print(f"🔧 {step_name}: {minutes}m {seconds:.1f}s")
    
    # Resource Utilization
    print("\n💻 RESOURCE UTILIZATION")
    print("-" * 40)
    resources = metrics_summary['resource_utilization']
    print(f"🖥️  Peak CPU Usage: {resources['peak_cpu_usage_percent']:.1f}%")
    print(f"📊 Average CPU Usage: {resources['avg_cpu_usage_percent']:.1f}%")
    
    print("\n🎮 GPU Memory Usage:")
    for gpu_id, max_memory in resources['max_gpu_memory_gb'].items():
        print(f"  GPU {gpu_id}: {max_memory:.2f} GB (peak)")
    
    print(f"\n💾 Disk I/O:")
    disk_io = resources['disk_io_gb']
    print(f"  📖 Read: {disk_io['read']:.2f} GB")
    print(f"  📝 Write: {disk_io['write']:.2f} GB")
    print(f"  📊 Total: {disk_io['total']:.2f} GB")
    
    print("="*80)

def save_metrics_report(metrics_summary, config, output_dir):
    """Save detailed metrics to files"""
    metrics_dir = os.path.join(output_dir, "training_metrics")
    os.makedirs(metrics_dir, exist_ok=True)
    
    # Save complete metrics as JSON
    with open(os.path.join(metrics_dir, "training_metrics.json"), "w") as f:
        json.dump(metrics_summary, f, indent=2, default=str)
    
    # Save training losses as CSV
    if metrics_summary['training_performance']['total_steps'] > 0:
        losses_df = pd.DataFrame([
            {'step': item['step'], 'loss': item['loss']} 
            for item in metrics_tracker.training_losses
        ])
        losses_df.to_csv(os.path.join(metrics_dir, "training_losses.csv"), index=False)
    
    print(f"📊 Detailed metrics saved to: {metrics_dir}")

# Replace MODEL_FAMILIES with this universal version:
MODEL_FAMILIES = {
    "deepseek": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    },
    "qwen": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    },
    "llama": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    },
    "mistral": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    },
    "yi": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    },
    "baichuan": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    },
    "chatglm": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    },
    "internlm": {
        "prompt_template": lambda instruction, input_text: f"Instruction: {instruction}\nInput: {input_text}\nOutput: ",
        "response_template": lambda output: f"{output}",
        "padding_side": "left"
    }
}

def load_config(config_path="config.json"):
    """Load configuration from JSON file"""
    if not os.path.exists(config_path):
        print(f"Config file {config_path} not found. Creating default config...")
        create_default_config(config_path)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        print(f"Error loading config file: {e}")
        print("Using default configuration...")
        return get_default_config()

def create_default_config(config_path="config.json"):
    """Create a default configuration file"""
    default_config = get_default_config()
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print(f"Default configuration saved to {config_path}")
        print("Please modify the config file and run again.")
    except Exception as e:
        print(f"Error creating default config file: {e}")

def get_default_config():
    """Get default configuration with memory-optimized settings"""
    return {
        "model": {
            "model_path": "/path/to/your/model",
            "model_family": "deepseek"
        },
        "data": {
            "train_csv": "train_set.csv",
            "eval_csv": "test_set.csv"
        },
        "lora": {
            "use_lora": True,
            "lora_r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05
        },
        "training": {
            "batch_size": 1,  # Reduced from 2
            "learning_rate": 3e-5,
            "num_epochs": 3,
            "max_seq_length": 8192,  # increased from 512
            "gradient_accumulation_steps": 16,  # Increased to maintain effective batch size
            "warmup_steps": 500
        },
        "output": {
            "output_dir": None
        }
    }

def parse_args():
    """Parse command line arguments (only for config file path)"""
    parser = argparse.ArgumentParser(description="Fine-tune Large Language Models with Model Parallelism")
    parser.add_argument("--job_id", type=str, default="no_job_id",
                       help="Slurm job ID for tracking purposes")
    parser.add_argument("--config", type=str, default="config.json",
                       help="Path to configuration JSON file")
    return parser.parse_args()

def validate_config(config):
    """Validate configuration values"""
    required_sections = ["model", "data", "lora", "training", "output"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section '{section}' in config")
    
    # Check model family
    model_family = config["model"]["model_family"]
    if model_family not in MODEL_FAMILIES:
        raise ValueError(f"Unsupported model family: {model_family}. "
                        f"Supported families: {list(MODEL_FAMILIES.keys())}")
    
    # Check file paths
    if not os.path.exists(config["data"]["train_csv"]):
        raise FileNotFoundError(f"Training file not found: {config['data']['train_csv']}")
    if not os.path.exists(config["data"]["eval_csv"]):
        raise FileNotFoundError(f"Evaluation file not found: {config['data']['eval_csv']}")
    
    print("✓ Configuration validation passed")

def print_config(config):
    """Print configuration in a readable format"""
    print("="*60)
    print("LOADED CONFIGURATION")
    print("="*60)
    
    print("📁 Model Configuration:")
    print(f"  Model path: {config['model']['model_path']}")
    print(f"  Model family: {config['model']['model_family']}")
    
    print("\n📊 Data Configuration:")
    print(f"  Training data: {config['data']['train_csv']}")
    print(f"  Evaluation data: {config['data']['eval_csv']}")
    
    print("\n🔧 LoRA Configuration:")
    print(f"  Use LoRA: {config['lora']['use_lora']}")
    if config['lora']['use_lora']:
        print(f"  LoRA rank: {config['lora']['lora_r']}")
        print(f"  LoRA alpha: {config['lora']['lora_alpha']}")
        print(f"  LoRA dropout: {config['lora']['lora_dropout']}")
    
    print("\n🚀 Training Configuration:")
    print(f"  Batch size: {config['training']['batch_size']}")
    print(f"  Learning rate: {config['training']['learning_rate']}")
    print(f"  Number of epochs: {config['training']['num_epochs']}")
    print(f"  Max sequence length: {config['training']['max_seq_length']}")
    print(f"  Gradient accumulation steps: {config['training']['gradient_accumulation_steps']}")
    print(f"  Warmup steps: {config['training']['warmup_steps']}")
    
    print("\n💾 Output Configuration:")
    output_dir = config['output']['output_dir'] or "Auto-generated"
    print(f"  Output directory: {output_dir}")
    
    print("="*60)

def cleanup_resources():
    """Comprehensive cleanup of all resources"""
    global writer, trainer, model
    
    print("\n" + "="*50)
    print("STARTING CLEANUP PROCESS")
    print("="*50)
    
    try:
        if writer is not None:
            print("Closing TensorBoard writer...")
            writer.close()
            writer = None
    except Exception as e:
        print(f"Error closing writer: {e}")
    
    try:
        if trainer is not None:
            print("Clearing trainer...")
            del trainer
            trainer = None
    except Exception as e:
        print(f"Error clearing trainer: {e}")
    
    try:
        if model is not None:
            print("Clearing model...")
            del model
            model = None
    except Exception as e:
        print(f"Error clearing model: {e}")
    
    # Aggressive memory cleanup
    aggressive_memory_cleanup()
    
    print("Cleanup completed!")
    print("="*50)

def signal_handler(signum, frame):
    """Handle termination signals"""
    print(f"\nReceived signal {signum}. Cleaning up...")
    cleanup_resources()
    sys.exit(1)

def terminate_all_processes():
    """Terminate all child processes"""
    try:
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        
        print(f"Found {len(children)} child processes to terminate")
        
        for child in children:
            try:
                print(f"Terminating process {child.pid}")
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        gone, alive = psutil.wait_procs(children, timeout=15)
        
        for p in alive:
            try:
                print(f"Force killing process {p.pid}")
                p.kill()
            except psutil.NoSuchProcess:
                pass
                
    except Exception as e:
        print(f"Error terminating processes: {e}")

def exit_handler():
    """Handler called on normal exit"""
    print("\nProgram exiting normally...")
    cleanup_resources()
    terminate_all_processes()

# Register cleanup handlers
atexit.register(exit_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def print_gpu_memory():
    """Print memory usage for all GPUs"""
    if torch.cuda.is_available():
        print("GPU Memory Usage:")
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            reserved = torch.cuda.memory_reserved(i) / 1024**3
            print(f"  GPU {i}: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")
    else:
        print("CUDA not available")

def clear_cache():
    """Clear CUDA cache and run garbage collection"""
    aggressive_memory_cleanup()

def get_model_layer_count(model_name):
    """Get the actual number of layers in the model"""
    try:
        config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
        num_layers = config.num_hidden_layers
        print(f"Model has {num_layers} layers")
        return num_layers
    except Exception as e:
        print(f"Could not determine layer count, defaulting to 64: {e}")
        return 64

def create_device_map(model_name, num_gpus=6):
    """Create device map for model parallelism across GPUs with memory constraints"""
    print(f"Creating device map for {num_gpus} GPUs...")
    
    # Get actual layer count
    num_layers = get_model_layer_count(model_name)
    
    # Calculate layers per GPU
    layers_per_gpu = num_layers // num_gpus
    remainder = num_layers % num_gpus
    
    print(f"Distributing {num_layers} layers across {num_gpus} GPUs")
    print(f"Base layers per GPU: {layers_per_gpu}")
    if remainder > 0:
        print(f"First {remainder} GPUs will get 1 extra layer")
    
    device_map = {}
    
    # Embedding layer on first GPU
    device_map["model.embed_tokens"] = 0
    
    # Distribute transformer layers
    current_layer = 0
    for gpu in range(num_gpus):
        # Calculate how many layers this GPU should get
        layers_for_this_gpu = layers_per_gpu
        if gpu < remainder:  # First few GPUs get extra layers
            layers_for_this_gpu += 1
        
        # Assign layers to this GPU
        end_layer = current_layer + layers_for_this_gpu
        for layer in range(current_layer, end_layer):
            device_map[f"model.layers.{layer}"] = gpu
        
        print(f"GPU {gpu}: layers {current_layer} to {end_layer-1} ({layers_for_this_gpu} layers)")
        current_layer = end_layer
    
    # Final layers on last GPU
    last_gpu = num_gpus - 1
    device_map["model.norm"] = last_gpu
    device_map["lm_head"] = last_gpu
    
    return device_map

def get_lora_target_modules(model_family):
    """Get LoRA target modules based on model family"""
    target_modules_map = {
        "deepseek": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "qwen": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "llama": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "mistral": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "yi": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "baichuan": ["W_pack", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "chatglm": ["query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h"],
        "internlm": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    }
    
    return target_modules_map.get(model_family, ["q_proj", "k_proj", "v_proj", "o_proj"])

def main():
    """Main training function with model parallelism and comprehensive metrics"""
    global writer, trainer, model, metrics_tracker
    
    # Initialize metrics tracker
    metrics_tracker = MetricsTracker()
    
    # Parse command line arguments (only config path)
    args = parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Validate configuration
    validate_config(config)
    
    # Print configuration
    print_config(config)
    
    try:
        # Start overall timing
        metrics_tracker.start_step("total_training")
        
        # Extract configuration values
        model_name = config["model"]["model_path"]
        model_family = config["model"]["model_family"]
        train_csv = config["data"]["train_csv"]
        eval_csv = config["data"]["eval_csv"]
        use_lora = config["lora"]["use_lora"]
        save_total_limit = config["training"].get("save_total_limit", 3)
        
        # Generate output directory if not provided
        if config["output"]["output_dir"] is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            model_type = "LoRA" if use_lora else "FullFT"
            output_model_path = f"./output_models/job_{args.job_id}_{timestamp}_{model_name.split('/')[-1]}_{model_type}"
        else:
            output_model_path = config["output"]["output_dir"]

        num_gpus = torch.cuda.device_count()
        print(f"\n🖥️  Available GPUs: {num_gpus}")
        
        os.makedirs(output_model_path, exist_ok=True)
        print(f"📁 Output directory: {output_model_path}")
        
        # Initial resource snapshot and aggressive cleanup
        aggressive_memory_cleanup()
        metrics_tracker.snapshot_resources("initial")
        print("\n🔍 Initial GPU memory state:")
        print_gpu_memory()

        # ==== 2. Data Loading ====
        metrics_tracker.start_step("data_loading")
        
        class CustomDataset(Dataset):
            def __init__(self, csv_file, tokenizer, model_family, max_seq_length):
                self.data = pd.read_csv(csv_file)
                self.tokenizer = tokenizer
                self.max_seq_length = max_seq_length
                self.model_family = model_family
                
                print(f"📊 Loaded {len(self.data)} examples from {csv_file}")
                print(f"📋 Columns: {list(self.data.columns)}")
                
                # Get model family configuration
                self.family_config = MODEL_FAMILIES[model_family]
                
            def __len__(self):
                return len(self.data)
            
            def __getitem__(self, idx):
                row = self.data.iloc[idx]
        
                # Convert pandas Series to dictionary to ensure consistent format
                if pd.notna(row['Transactions']) and str(row['Transactions']).strip():
                    # Use this structure when Transactions data exists
                    item_dict = {
                        'Instruction': str(row['Instruction']),
                        'Input': f'Now, process the following documents.\n<FRAUD_ALERT_SOURCE>\n{row["Input"]}\n</FRAUD_ALERT_SOURCE>\n<TRANSACTION_RECORDS_CSV>\n{row["Transactions"]}\n</TRANSACTION_RECORDS_CSV>', 
                        'Output': str(row['Ground Truth'])
                    }
                else:
                    # Use this structure when Transactions is empty or missing
                    item_dict = {
                        'Instruction': str(row['Instruction']),
                        'Input': str(row['Input']), 
                        'Output': str(row['Ground Truth'])
                    }
                
                return item_dict  # Return dictionary instead of processed tokens

        # ==== 3. Tokenizer ====
        print("🔤 Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Handle different tokenizer configurations
        if tokenizer.pad_token is None:
            if tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token
            else:
                tokenizer.add_special_tokens({'pad_token': '[PAD]'})
        
        # Set padding side based on model family
        tokenizer.padding_side = MODEL_FAMILIES[model_family]["padding_side"]
        print(f"✓ Tokenizer padding side set to: {tokenizer.padding_side}")

        # ==== 4. Create Datasets ====
        print("📚 Creating datasets...")
        train_dataset = CustomDataset(train_csv, tokenizer, model_family, config["training"]["max_seq_length"])
        eval_dataset = CustomDataset(eval_csv, tokenizer, model_family, config["training"]["max_seq_length"])

        aggressive_memory_cleanup()
        metrics_tracker.end_step("data_loading")
        metrics_tracker.snapshot_resources("after_data_loading")
        print("\n🔍 After data loading:")
        print_gpu_memory()

        # ==== 5. Model Loading ====
        metrics_tracker.start_step("model_loading")
        
        # Create Device Map for Model Parallelism
        device_map = create_device_map(model_name, num_gpus)

        # Load Model with Model Parallelism and stricter memory limits
        print("🤖 Loading model with model parallelism...")
        
        model_config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
        if hasattr(model_config, "tensor_parallel_size"):
            model_config.tensor_parallel_size = 1

        # Load model with device_map for model parallelism and stricter memory limits
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            config=model_config,
            torch_dtype=torch.bfloat16,
            attn_implementation="flash_attention_2",
            trust_remote_code=True,
            device_map=device_map,
            low_cpu_mem_usage=True,
            max_memory={i: "72GB" for i in range(num_gpus)},  # Reduced from 12GB to 8GB
        )

        metrics_tracker.end_step("model_loading")
        aggressive_memory_cleanup()
        metrics_tracker.snapshot_resources("after_model_loading")
        print("✓ Model loaded with model parallelism")
        print_gpu_memory()

        # ==== 6. LoRA Setup ====
        metrics_tracker.start_step("lora_setup")
        
        if use_lora:
            print("🔧 Applying LoRA...")
            
            lora_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=config["lora"]["lora_r"],
                lora_alpha=config["lora"]["lora_alpha"],
                lora_dropout=config["lora"]["lora_dropout"],
                target_modules=get_lora_target_modules(model_family),
                bias="none",
            )
            
            model = get_peft_model(model, lora_config)
            print(f"✓ LoRA target modules for {model_family}: {get_lora_target_modules(model_family)}")
        else:
            print("🔧 Using full fine-tuning (no LoRA)")
            
        model.train()
        
        metrics_tracker.end_step("lora_setup")
        aggressive_memory_cleanup()
        metrics_tracker.snapshot_resources("after_lora_setup")
        print(f"\n🔍 After {'LoRA application' if use_lora else 'model setup'}:")
        print_gpu_memory()

        # Check trainable parameters
        if use_lora:
            lora_param_count = 0
            for name, param in model.named_parameters():
                if "lora" in name.lower():
                    param.requires_grad = True
                    lora_param_count += 1
                else:
                    param.requires_grad = False
            print(f"🎯 LoRA parameters found: {lora_param_count}")
        else:
            for name, param in model.named_parameters():
                param.requires_grad = True
            print("🎯 All model parameters are trainable (full fine-tuning)")

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"📊 Trainable parameters: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")

        # ==== 7. Training Setup ====
        metrics_tracker.start_step("training_setup")
        
        print(f"🔧 Transformers version: {transformers.__version__}")

        # Data collator with memory optimization
        class HKMADataCollator:
            """Universal data collator that auto-detects working tokens"""
            
            def __init__(self, tokenizer, max_length=512):
                self.tokenizer = tokenizer
                self.max_length = max_length
                
                # Debug tokenizer info
                print(f"🔤 Tokenizer Debug Info:")
                print(f"  Vocab size: {tokenizer.vocab_size}")
                print(f"  Model max length: {getattr(tokenizer, 'model_max_length', 'Unknown')}")
                
                # Check what special tokens are actually available
                special_tokens_info = {
                    'bos_token': tokenizer.bos_token,
                    'eos_token': tokenizer.eos_token,
                    'pad_token': tokenizer.pad_token,
                    'unk_token': tokenizer.unk_token,
                }
                
                print(f"  Available special tokens:")
                for name, token in special_tokens_info.items():
                    if token:
                        token_id = tokenizer.convert_tokens_to_ids(token)
                        valid = token_id < tokenizer.vocab_size and token_id >= 0
                        print(f"    {name}: '{token}' (ID: {token_id}) {'✅' if valid else '🚨 INVALID'}")
                    else:
                        print(f"    {name}: None")
                
                # Try to find working conversation tokens
                test_tokens = [
                    '<|begin_of_text|>', '<|start_header_id|>', '<|end_header_id|>', '<|eot_id|>',
                    '<|im_start|>', '<|im_end|>', 
                    '<s>', '</s>', '[INST]', '[/INST]',
                    '<|user|>', '<|assistant|>', '<|system|>',
                    'Human:', 'Assistant:', 'User:', 'AI:'
                ]
                
                self.working_tokens = {}
                print(f"  Testing conversation tokens:")
                for token in test_tokens:
                    try:
                        token_id = tokenizer.convert_tokens_to_ids(token)
                        # Check if it's a valid single token (not broken into pieces)
                        reconstructed = tokenizer.convert_ids_to_tokens([token_id])
                        if (token_id < tokenizer.vocab_size and 
                            token_id >= 0 and 
                            reconstructed and 
                            len(reconstructed) == 1):
                            self.working_tokens[token] = token_id
                            print(f"    '{token}': ID {token_id} ✅")
                        else:
                            print(f"    '{token}': ID {token_id} ❌ (broken/invalid)")
                    except:
                        print(f"    '{token}': ❌ NOT FOUND")
                
                # Determine the best prompt format to use
                self.prompt_format = self._determine_prompt_format()
                print(f"  Selected prompt format: {self.prompt_format}")
            
            def _determine_prompt_format(self):
                """Determine the best prompt format based on available tokens"""
                
                # Format 1: Try DeepSeek-style if tokens available
                if all(token in self.working_tokens for token in ['<|start_header_id|>', '<|end_header_id|>', '<|eot_id|>']):
                    return "deepseek_style"
                
                # Format 2: Try Qwen-style
                elif all(token in self.working_tokens for token in ['<|im_start|>', '<|im_end|>']):
                    return "qwen_style"
                
                # Format 3: Try Llama-style
                elif all(token in self.working_tokens for token in ['<s>', '</s>', '[INST]', '[/INST]']):
                    return "llama_style"
                
                # Format 4: Try simple user/assistant
                elif all(token in self.working_tokens for token in ['<|user|>', '<|assistant|>']):
                    return "simple_conversation"
                
                # Format 5: Fallback to plain text with identifiers
                else:
                    return "plain_text"
            
            def _create_prompt(self, instruction, input_text, output_text=None):
                """Create prompt based on determined format"""
                
                if self.prompt_format == "deepseek_style":
                    prompt = (
                        f"<|start_header_id|>user<|end_header_id|>\n\n"
                        f"Instruction: {instruction}\nInput: {input_text}<|eot_id|>\n"
                        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
                    )
                    if output_text:
                        return prompt + f"{output_text}<|eot_id|>"
                    
                elif self.prompt_format == "qwen_style":
                    prompt = (
                        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
                        f"<|im_start|>user\n{instruction}\n{input_text}<|im_end|>\n"
                        f"<|im_start|>assistant\n"
                    )
                    if output_text:
                        return prompt + f"{output_text}<|im_end|>"
                        
                elif self.prompt_format == "llama_style":
                    prompt = f"<s>[INST] {instruction}\n{input_text} [/INST] "
                    if output_text:
                        return prompt + f"{output_text}</s>"
                        
                elif self.prompt_format == "simple_conversation":
                    prompt = f"<|user|>\n{instruction}\n{input_text}\n<|assistant|>\n"
                    if output_text:
                        return prompt + output_text
                        
                else:  # plain_text fallback
                    prompt = f"Instruction: {instruction}\nInput: {input_text}\nOutput: "
                    if output_text:
                        return prompt + output_text
                
                return prompt
            
            def __call__(self, batch):
                """Process a batch with auto-detected format - FIXED VERSION"""
                
                input_ids_list = []
                attention_mask_list = []
                labels_list = []
                
                for item in batch:
                    try:
                        # Handle different data formats
                        if isinstance(item, dict):
                            # Dictionary format (expected)
                            instruction = item.get('Instruction', item.get('instruction', ''))
                            input_text = item.get('Input', item.get('input', ''))
                            output_text = item.get('Output', item.get('output', ''))
                        else:
                            # Pandas Series or other format
                            instruction = getattr(item, 'Instruction', getattr(item, 'instruction', ''))
                            input_text = getattr(item, 'Input', getattr(item, 'input', ''))
                            output_text = getattr(item, 'Output', getattr(item, 'output', ''))
                        
                        # Debug print for first few items
                        if len(input_ids_list) < 3:
                            print(f"🔍 Processing item {len(input_ids_list) + 1}:")
                            print(f"  Type: {type(item)}")
                            if isinstance(item, dict):
                                print(f"  Keys: {list(item.keys())}")
                            print(f"  Instruction: '{instruction[:50]}...'")
                            print(f"  Input: '{input_text[:50]}...'")
                            print(f"  Output: '{output_text[:50]}...'")
                        
                        # Create full conversation
                        full_text = self._create_prompt(instruction, input_text, output_text)
                        prompt_only = self._create_prompt(instruction, input_text)
                        
                        if len(input_ids_list) < 3:
                            print(f"  Full text: '{full_text[:100]}...'")
                            print(f"  Prompt only: '{prompt_only[:100]}...'")
                        
                        # Tokenize full text
                        encoding = self.tokenizer(
                            full_text,
                            max_length=self.max_length,
                            truncation=True,
                            padding=False,
                            return_tensors="pt",
                            add_special_tokens=False
                        )
                        
                        input_ids = encoding['input_ids'].squeeze()
                        attention_mask = encoding['attention_mask'].squeeze()
                        
                        # Handle single token case
                        if len(input_ids.shape) == 0:
                            input_ids = input_ids.unsqueeze(0)
                            attention_mask = attention_mask.unsqueeze(0)
                        
                        # Validate token IDs
                        invalid_mask = (input_ids >= self.tokenizer.vocab_size) | (input_ids < 0)
                        if invalid_mask.any():
                            print(f"🚨 Found {invalid_mask.sum()} invalid tokens in item {len(input_ids_list) + 1}")
                            unk_id = self.tokenizer.unk_token_id if self.tokenizer.unk_token_id is not None else 0
                            input_ids[invalid_mask] = unk_id
                        
                        # Create labels
                        labels = input_ids.clone()
                        
                        # Mask prompt tokens
                        try:
                            prompt_encoding = self.tokenizer(
                                prompt_only,
                                max_length=self.max_length,
                                truncation=True,
                                padding=False,
                                add_special_tokens=False
                            )
                            prompt_length = len(prompt_encoding['input_ids'])
                            
                            if len(labels) > prompt_length:
                                labels[:prompt_length] = -100
                                if len(input_ids_list) < 3:
                                    print(f"  Masked {prompt_length} prompt tokens")
                            else:
                                # Keep some labels if sequence is very short
                                if len(labels) > 5:
                                    labels[:-5] = -100
                                    if len(input_ids_list) < 3:
                                        print(f"  Kept last 5 tokens as labels")
                        except Exception as e:
                            print(f"⚠️ Prompt masking failed: {e}, using fallback")
                            # Fallback: mask first half
                            half_length = len(labels) // 2
                            labels[:half_length] = -100
                        
                        # Ensure we have some valid labels
                        valid_labels = (labels != -100).sum()
                        if valid_labels == 0 and len(labels) > 0:
                            labels[-1] = input_ids[-1]
                            if len(input_ids_list) < 3:
                                print(f"  Added fallback label for last token")
                        
                        if len(input_ids_list) < 3:
                            print(f"  Final sequence length: {len(input_ids)}")
                            print(f"  Valid labels: {valid_labels}")
                        
                        input_ids_list.append(input_ids)
                        attention_mask_list.append(attention_mask)
                        labels_list.append(labels)
                        
                    except Exception as e:
                        print(f"❌ Error processing item {len(input_ids_list) + 1}: {e}")
                        print(f"   Item type: {type(item)}")
                        if hasattr(item, '__dict__'):
                            print(f"   Item attributes: {list(item.__dict__.keys())}")
                        elif isinstance(item, dict):
                            print(f"   Item keys: {list(item.keys())}")
                        
                        # Create minimal fallback
                        try:
                            fallback_text = "Question: Answer:"
                            encoding = self.tokenizer(
                                fallback_text,
                                max_length=20,
                                truncation=True,
                                padding=False,
                                return_tensors="pt"
                            )
                            input_ids = encoding['input_ids'].squeeze()
                            if len(input_ids.shape) == 0:
                                input_ids = input_ids.unsqueeze(0)
                            
                            input_ids_list.append(input_ids)
                            attention_mask_list.append(torch.ones_like(input_ids))
                            labels_list.append(input_ids.clone())
                            print(f"   Used fallback sequence")
                        except Exception as e2:
                            print(f"   Fallback also failed: {e2}")
                            continue
                
                if not input_ids_list:
                    raise ValueError("No valid samples in batch - all processing failed")
                
                print(f"✅ Successfully processed {len(input_ids_list)} items in batch")
                
                # Pad sequences
                max_len = max(len(seq) for seq in input_ids_list)
                max_len = min(max_len, self.max_length)
                
                padded_input_ids = []
                padded_attention_mask = []
                padded_labels = []
                
                for i in range(len(input_ids_list)):
                    seq = input_ids_list[i]
                    mask = attention_mask_list[i]
                    labels = labels_list[i]
                    
                    # Truncate if needed
                    if len(seq) > max_len:
                        seq = seq[:max_len]
                        mask = mask[:max_len]
                        labels = labels[:max_len]
                    
                    seq_len = len(seq)
                    pad_len = max_len - seq_len
                    
                    # Pad sequences
                    pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0
                    
                    padded_ids = torch.cat([
                        seq,
                        torch.full((pad_len,), pad_token_id, dtype=seq.dtype)
                    ])
                    
                    padded_mask = torch.cat([
                        mask,
                        torch.zeros(pad_len, dtype=mask.dtype)
                    ])
                    
                    padded_label = torch.cat([
                        labels,
                        torch.full((pad_len,), -100, dtype=labels.dtype)
                    ])
                    
                    padded_input_ids.append(padded_ids)
                    padded_attention_mask.append(padded_mask)
                    padded_labels.append(padded_label)
                
                result = {
                    'input_ids': torch.stack(padded_input_ids),
                    'attention_mask': torch.stack(padded_attention_mask),
                    'labels': torch.stack(padded_labels)
                }
                
                # Final validation
                batch_size, seq_len = result['input_ids'].shape
                max_valid_id = self.tokenizer.vocab_size - 1
                
                # Fix any remaining invalid IDs
                invalid_mask = (result['input_ids'] < 0) | (result['input_ids'] > max_valid_id)
                if invalid_mask.any():
                    print(f"⚠️ Fixed {invalid_mask.sum()} invalid token IDs in final batch")
                    pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0
                    result['input_ids'] = torch.where(invalid_mask, pad_token_id, result['input_ids'])
                
                print(f"📊 Final batch shape: {result['input_ids'].shape}")
                print(f"📊 Token ID range: {result['input_ids'].min()} to {result['input_ids'].max()}")
                
                return result
            
        # Data collator with memory optimization - FIXED VERSION
        hkma_collator = HKMADataCollator(tokenizer, max_length=config["training"]["max_seq_length"])

        # Create data loader
        from torch.utils.data import DataLoader
        train_dataloader = DataLoader(
            train_dataset,
            batch_size=config["training"]["batch_size"],
            shuffle=True,
            collate_fn=hkma_collator,
            num_workers=0,
            pin_memory=False
        )

        # Get trainable parameters
        trainable_param_list = [p for p in model.parameters() if p.requires_grad]
        print(f"📊 Number of trainable parameter tensors: {len(trainable_param_list)}")
        
        # Optimizer
        optimizer = torch.optim.AdamW(trainable_param_list, lr=config["training"]["learning_rate"], weight_decay=0.01)
        
        # Calculate steps
        total_train_batch_size = config["training"]["batch_size"] * config["training"]["gradient_accumulation_steps"]
        num_update_steps_per_epoch = len(train_dataloader) // config["training"]["gradient_accumulation_steps"]
        num_training_steps = config["training"]["num_epochs"] * num_update_steps_per_epoch
        
        print(f"📈 Total training steps: {num_training_steps}")
        
        # Scheduler
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=config["training"]["warmup_steps"],
            num_training_steps=num_training_steps
        )
        
        metrics_tracker.end_step("training_setup")

	# ==== 8. Training Loop ====
        metrics_tracker.start_step("training_loop")
        
        writer = SummaryWriter(log_dir=os.path.join(output_model_path, "logs"))
        
        print("\n" + "="*60)
        print("🚀 STARTING TRAINING")
        print("="*60)
        print(f"  📊 Num examples = {len(train_dataset)}")
        print(f"  🔄 Num Epochs = {config['training']['num_epochs']}")
        print(f"  📦 Batch size per device = {config['training']['batch_size']}")
        print(f"  📦 Total train batch size = {total_train_batch_size}")
        print(f"  🔄 Gradient Accumulation steps = {config['training']['gradient_accumulation_steps']}")
        print(f"  📈 Total optimization steps = {num_training_steps}")
        print("="*60)
        
        # Training state
        global_step = 0
        model.train()
        
        # Key fix: We need to properly iterate through the training data
        for epoch in range(config["training"]["num_epochs"]):
            print(f"\n🔄 === Epoch {epoch + 1}/{config['training']['num_epochs']} ===")
            epoch_start_time = time.time()
            
            epoch_loss = 0.0
            num_batches = 0
            accumulated_loss = 0.0
            gradient_accumulation_count = 0
            
            # Create fresh dataloader for each epoch
            train_dataloader = DataLoader(
                train_dataset,
                batch_size=config["training"]["batch_size"],
                shuffle=True,
                collate_fn=hkma_collator,
                num_workers=0,
                pin_memory=False
            )
            
            print(f"📊 Epoch {epoch+1}: Processing {len(train_dataloader)} batches...")
            
            for batch_idx, batch in enumerate(train_dataloader):
                try:
                    # Move batch to the correct device - BETTER ERROR HANDLING
                    device = 'cuda:0'  # Use first GPU for input
                    
                    # Debug batch content
                    if batch_idx < 3:
                        print(f"🔍 Batch {batch_idx + 1} debug:")
                        print(f"  Batch keys: {list(batch.keys())}")
                        print(f"  input_ids shape: {batch['input_ids'].shape}")
                        print(f"  input_ids device: {batch['input_ids'].device}")
                        print(f"  Token ID range: {batch['input_ids'].min()} to {batch['input_ids'].max()}")
                    
                    batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
                    
                    # Forward pass
                    outputs = model(**batch)
                    loss = outputs.loss
                    
                    if batch_idx < 3:
                        print(f"  Loss: {loss.item():.6f}")
                    
                    # Validate loss
                    if torch.isnan(loss) or torch.isinf(loss):
                        print(f"⚠️ Skipping batch {batch_idx} due to invalid loss: {loss}")
                        continue
                    
                    # Scale loss for gradient accumulation
                    scaled_loss = loss / config["training"]["gradient_accumulation_steps"]
                    
                    # Backward pass
                    scaled_loss.backward()
                    
                    # Accumulate metrics
                    accumulated_loss += scaled_loss.item()
                    epoch_loss += scaled_loss.item()
                    num_batches += 1
                    gradient_accumulation_count += 1
                    
                    print(f"🔄 Batch {batch_idx+1}/{len(train_dataloader)}: loss={loss.item():.6f}, scaled={scaled_loss.item():.6f}, accumulated={accumulated_loss:.6f}")
                    
                    # Check if we should do an optimization step
                    should_step = (gradient_accumulation_count >= config["training"]["gradient_accumulation_steps"]) or (batch_idx == len(train_dataloader) - 1)
                    
                    if should_step:
                        step_start_time = time.time()
                        
                        # Gradient clipping
                        grad_norm = torch.nn.utils.clip_grad_norm_(trainable_param_list, 1.0)
                        
                        # Optimizer step
                        optimizer.step()
                        scheduler.step()
                        optimizer.zero_grad()
                        
                        global_step += 1
                        step_duration = time.time() - step_start_time
                        current_lr = scheduler.get_last_lr()[0]
                        
                        # Calculate average loss for this optimization step
                        avg_accumulated_loss = accumulated_loss * config["training"]["gradient_accumulation_steps"] / gradient_accumulation_count
                        
                        print(f"📊 ✅ OPTIMIZATION STEP {global_step}:")
                        print(f"    Loss: {avg_accumulated_loss:.6f}")
                        print(f"    LR: {current_lr:.2e}")
                        print(f"    Grad norm: {grad_norm:.6f}")
                        print(f"    Duration: {step_duration:.2f}s")
                        print(f"    Batches accumulated: {gradient_accumulation_count}")
                        
                        # Log to metrics tracker
                        metrics_tracker.log_training_step(global_step, avg_accumulated_loss, current_lr, step_duration)
                        
                        # TensorBoard logging
                        if writer:
                            writer.add_scalar('train/loss', avg_accumulated_loss, global_step)
                            writer.add_scalar('train/learning_rate', current_lr, global_step)
                            writer.add_scalar('train/step_duration', step_duration, global_step)
                            writer.add_scalar('train/grad_norm', grad_norm, global_step)
                        
                        # Reset accumulation
                        accumulated_loss = 0.0
                        gradient_accumulation_count = 0
                        
                        # Save checkpoint
                        if global_step % 5 == 0:  # Save more frequently for debugging
                            checkpoint_dir = os.path.join(output_model_path, f"checkpoint-{global_step}")
                            print(f"💾 Saving checkpoint at step {global_step}")
                            os.makedirs(checkpoint_dir, exist_ok=True)
                            model.save_pretrained(checkpoint_dir, safe_serialization=True)
                            tokenizer.save_pretrained(checkpoint_dir)
                            
                            # Cleanup old checkpoints
                            if save_total_limit > 0:
                                import glob
                                import shutil
                                checkpoints = glob.glob(os.path.join(output_model_path, "checkpoint-*"))
                                checkpoints = [d for d in checkpoints if os.path.isdir(d)]
                                if len(checkpoints) > save_total_limit:
                                    checkpoints.sort(key=lambda x: int(x.split("-")[-1]))
                                    for old_checkpoint in checkpoints[:-save_total_limit]:
                                        print(f"🗑️ Removing old checkpoint: {old_checkpoint}")
                                        shutil.rmtree(old_checkpoint)
                        
                        # Memory cleanup
                        if global_step % 2 == 0:
                            aggressive_memory_cleanup()
                    
                except Exception as e:
                    print(f"❌ Error in batch {batch_idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Epoch summary
            avg_epoch_loss = epoch_loss / num_batches if num_batches > 0 else 0
            epoch_duration = time.time() - epoch_start_time
            
            print(f"\n✅ Epoch {epoch + 1} completed:")
            print(f"    Average loss: {avg_epoch_loss:.6f}")
            print(f"    Duration: {epoch_duration:.1f}s")
            print(f"    Optimization steps this epoch: {global_step - (epoch * (len(train_dataloader) // config['training']['gradient_accumulation_steps']))}")
            print(f"    Total optimization steps so far: {global_step}")
            
            # Log epoch metrics
            metrics_tracker.log_epoch_metrics(epoch + 1, avg_epoch_loss, global_step)
            
            # Cleanup after epoch
            aggressive_memory_cleanup()
        
        print(f"\n🎉 Training completed! Total optimization steps: {global_step}")
        
        if global_step == 0:
            print("🚨 WARNING: No optimization steps were performed!")
            print("🚨 The model was not actually trained!")
            return False
        
        metrics_tracker.end_step("training_loop")

        # ==== 9. Model Saving ====
        metrics_tracker.start_step("model_saving")
        
        print("💾 Saving final model...")
        model.save_pretrained(
            output_model_path,
            safe_serialization=True,
            max_shard_size="2GB"
        )
        tokenizer.save_pretrained(output_model_path)
        
        # Save training configuration
        config_info = {
            "original_config": config,
            "model_family": model_family,
            "use_lora": use_lora,
            "output_model_path": output_model_path,
            "training_completed": True
        }
        
        with open(os.path.join(output_model_path, "training_config.json"), "w") as f:
            json.dump(config_info, f, indent=2)
        
        if writer:
            writer.close()
        
        metrics_tracker.end_step("model_saving")
        metrics_tracker.end_step("total_training")
        
        print(f"✅ Model saved to {output_model_path}")
        print("🎉 Training and saving completed successfully!")
        
        # Final resource snapshot
        metrics_tracker.snapshot_resources("final")
        print("\n🔍 Final GPU memory state:")
        print_gpu_memory()
        
        # Generate and display comprehensive metrics report
        metrics_summary = metrics_tracker.get_training_summary()
        print_metrics_report(metrics_summary, config)
        
        # Save detailed metrics
        save_metrics_report(metrics_summary, config, output_model_path)
        
        return True

    except KeyboardInterrupt:
        print("\n⚠️  Training interrupted by user (Ctrl+C)")
        return False
    except Exception as e:
        print(f"\n❌ Training failed with error: {e}")
        print("🔍 GPU memory state at failure:")
        print_detailed_memory_usage()
        print("\n📋 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n" + "="*50)
            print("🎉 MODEL PARALLEL TRAINING COMPLETED SUCCESSFULLY!")
            print("="*50)
            sys.exit(0)
        else:
            print("\n" + "="*50)
            print("❌ MODEL PARALLEL TRAINING FAILED!")
            print("="*50)
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Critical error in main: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        cleanup_resources()
        print("🧹 All cleanup completed. Exiting.")
