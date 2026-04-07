@echo off
echo ============================================================
echo Installing PyTorch with CUDA Support for RTX 3060
echo ============================================================
echo.
echo Your GPU: NVIDIA GeForce RTX 3060 Laptop GPU (6GB)
echo Driver Version: 555.99
echo.
echo This will:
echo 1. Uninstall CPU-only PyTorch
echo 2. Install CUDA-enabled PyTorch (CUDA 11.8)
echo.
pause

echo.
echo Step 1: Uninstalling CPU-only PyTorch...
pip uninstall -y torch torchvision torchaudio

echo.
echo Step 2: Installing CUDA-enabled PyTorch...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

echo.
echo Step 3: Verifying installation...
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not detected')"

echo.
echo ============================================================
echo Installation complete!
echo ============================================================
pause
