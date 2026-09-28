"""
CHRONOS Model Cacher.

Pre-downloads the HuggingFace foundation models to ensure they are 
cached locally for the air-gapped hackathon demo.
"""

def cache_models():
    print("Loading HuggingFace Transformers...")
    try:
        from transformers import AutoModel, AutoImageProcessor
    except ImportError:
        print("Transformers not installed yet. Run this after pip install.")
        return

    print("Downloading/Caching openai/clip-vit-base-patch32 (RemoteCLIP Tier 2 Fallback)...")
    model = AutoModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = AutoImageProcessor.from_pretrained("openai/clip-vit-base-patch32")
    
    print("Models successfully cached for offline use!")

if __name__ == "__main__":
    cache_models()
