# pdf-ocr-guiapp

## Instalation

1. clone
  - `git clone https://github.com/gomagoma7/pdf-ocr-guiapp.git`
  - `cd pdf-ocr-guiapp`
2. sync packages
  - Using uv
    - For mac: `brew install uv`
  - Sync packages
    - `uv sync`
3. installing other dependencies
  - tesseract
  - OCR Soft
    - `brew install tesseract`
  - tkinter
    - `brew install python-tk`
4. check tesseract folder
  - If installing with brew... 
    - `/opt/homebrew/bin/tesseact`
  - Insert tesseract path
    - `PdfOcrProcessor` class => `__init__()` => `tesseract_path=YOUR_TESSERACT_PATH`