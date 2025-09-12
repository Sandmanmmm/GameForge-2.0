# GameForge GPU Server - Manual Deployment Instructions

## 🚀 DEPLOYMENT STEPS FOR VAST.AI

### Step 1: Access Your Vast Instance
1. Go to: https://vast.ai/console/instances/
2. Find Instance ID: **25599851**
3. Click **"Open"** to access Jupyter interface
4. Open a **Terminal** in Jupyter

### Step 2: Upload GPU Server Code
1. In Jupyter, create a new file: `gpu_server_port8080.py`
2. Copy the entire contents from your local `gpu_server_port8080.py` file
3. Save the file

### Step 3: Install Dependencies
Run these commands in the Jupyter terminal:

```bash
pip install fastapi uvicorn diffusers transformers accelerate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install xformers safety-checker pillow aiofiles
```

### Step 4: Verify GPU
```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

### Step 5: Start GPU Server
```bash
python gpu_server_port8080.py
```

You should see output like:
```
INFO: Starting GameForge GPU Server on port 8080...
INFO: Using device: cuda
INFO: GPU: NVIDIA GeForce RTX 4090
INFO: Loading SDXL pipeline...
INFO: GameForge GPU Server ready on port 8080!
INFO: External access via port 41392
```

### Step 6: Test Health Endpoint
Open a new terminal tab and test:
```bash
curl http://localhost:8080/health
```

Or from external:
```bash
curl http://172.97.240.138:41392/health
```

## 🔧 TROUBLESHOOTING

**If you get import errors:**
```bash
pip install --upgrade pip
pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**If CUDA is not available:**
- Check instance status in Vast console
- Verify GPU instance is running
- Restart instance if needed

**If port issues occur:**
- Ensure you're running on port 8080 (not 41392)
- Port 8080 maps to external port 41392

## 📋 QUICK DEPLOYMENT SCRIPT

Copy this entire block and paste in Jupyter terminal:

```bash
# Install dependencies
pip install fastapi uvicorn diffusers transformers accelerate torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 xformers safety-checker pillow aiofiles

# Check GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

# Start server (make sure gpu_server_port8080.py is uploaded first)
python gpu_server_port8080.py
```

## ✅ SUCCESS INDICATORS

When deployment is successful, you'll see:
- ✅ All packages installed without errors
- ✅ CUDA Available: True
- ✅ GPU: NVIDIA GeForce RTX 4090  
- ✅ SDXL pipeline loaded successfully
- ✅ Server running on port 8080
- ✅ Health endpoint responding

**External endpoint will be accessible at: http://172.97.240.138:41392/health**
