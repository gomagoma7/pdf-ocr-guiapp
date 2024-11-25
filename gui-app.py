import io
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import pytesseract
import TkEasyGUI as eg
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from tqdm import tqdm


class PdfOcrProcessor:
    def __init__(self, tesseract_path: Optional[str] = "/opt/homebrew/bin/tesseract"):
        """
        Initialize the PDF OCR Processor.
        
        Args:
            tesseract_path: Path to tesseract executable
        """
        # Setup logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Configure tesseract
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
        # Setup font
        self._setup_font()
        
        # OCR configuration
        self.conf_threshold = 60  # Minimum confidence threshold for OCR
        self.dpi = 300  # DPI for PDF to image conversion
        
    def _setup_font(self) -> None:
        """Setup the font for PDF text layer."""
        try:
            font_folder = Path(__file__).parent / "fonts"
            self.font_name = "0xProto-Regular"
            font_path = font_folder / f"{self.font_name}.ttf"
            
            if font_path.exists():
                pdfmetrics.registerFont(TTFont(self.font_name, str(font_path)))
                self.logger.info(f"Registered custom font: {self.font_name}")
            else:
                raise FileNotFoundError(f"Font file not found: {font_path}")
                
        except Exception as e:
            self.logger.warning(f"Font registration failed: {str(e)}. Using Helvetica.")
            self.font_name = 'Helvetica'

    def process_pdf(self, input_path: str, output_path: str) -> Tuple[bool, str]:
        """
        Process PDF file with OCR and create searchable PDF.
        
        Args:
            input_path: Path to input PDF file
            output_path: Path to save output PDF file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate input file
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert PDF to images
            self.logger.info("Converting PDF to images...")
            images = convert_from_path(input_path, dpi=self.dpi)
            
            # Initialize PDF reader and writer
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Process each page
            for i, image in tqdm(enumerate(images), total=len(images), 
                               desc="Processing pages"):
                # Perform OCR with detailed data
                ocr_data = pytesseract.image_to_data(
                    image, 
                    lang='eng',
                    output_type=pytesseract.Output.DICT,
                    config='--psm 1'  # Automatic page segmentation with OSD
                )
                
                # Create text layer
                text_layer = self._create_text_layer(ocr_data, image.size)
                
                # Merge layers
                original_page = reader.pages[i]
                text_page = PdfReader(io.BytesIO(text_layer)).pages[0]
                original_page.merge_page(text_page)
                writer.add_page(original_page)
                
                self.logger.info(f"Processed page {i+1}/{len(images)}")
            
            # Save output PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            self.logger.info(f"Successfully saved searchable PDF to: {output_path}")
            return True, "Processing completed successfully"
            
        except Exception as e:
            error_msg = f"Error processing PDF: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        
    def _create_text_layer(self, ocr_data: dict, size: Tuple[int, int]) -> bytes:
        """
        Create a PDF text layer from OCR data.
        
        Args:
            ocr_data: Dictionary containing OCR data from pytesseract
            size: Tuple of (width, height) for the page
            
        Returns:
            PDF content as bytes
        """
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=size)
        
        # Set font and color
        c.setFont(self.font_name, 8)
        c.setFillColor(Color(0, 0, 0, alpha=0))  # Transparent text
        
        last_block_num = -1
        text_block = []
        
        # Process OCR data
        for i in range(len(ocr_data['text'])):
            conf = float(ocr_data['conf'][i])
            if conf < self.conf_threshold:
                continue
                
            # Group text by blocks for better paragraph handling
            if ocr_data['block_num'][i] != last_block_num:
                if text_block:
                    self._write_text_block(c, text_block, size)
                text_block = []
                last_block_num = ocr_data['block_num'][i]
            
            text_block.append({
                'text': ocr_data['text'][i],
                'x': ocr_data['left'][i],
                'y': ocr_data['top'][i],
                'width': ocr_data['width'][i],
                'height': ocr_data['height'][i]
            })
        
        # Write final text block
        if text_block:
            self._write_text_block(c, text_block, size)
            
        c.save()
        return packet.getvalue()
    
    def _write_text_block(self, canvas_obj, text_block: list, size: Tuple[int, int]) -> None:
        """
        Write a block of text to the PDF canvas.
        
        Args:
            canvas_obj: ReportLab canvas object
            text_block: List of text elements in the block
            size: Page size tuple (width, height)
        """
        for item in text_block:
            text = item['text'].strip()
            if not text:
                continue
                
            try:
                # Convert coordinates (tesseract uses top-left origin, PDF uses bottom-left)
                x = item['x']
                y = size[1] - item['y'] - item['height']
                
                # Clean text and maintain positioning
                cleaned_text = text.encode('utf-8', 'ignore').decode('utf-8')
                canvas_obj.drawString(x, y, cleaned_text)
                
            except Exception as e:
                self.logger.warning(f"Failed to write text: {str(e)}")
                continue

def main():
    """Main function to run the GUI application."""
    processor = PdfOcrProcessor()
    
    layout = [
        [eg.Text("Select PDF File:"), eg.Button("Select File")],
        [eg.Text("Select Output Folder:"), eg.Button("Select Folder")],
        [eg.Text("Output Filename:"), eg.Input("output", key="-name-")],
        [eg.Button("Start OCR"), eg.Button("Cancel")]
    ]
    
    window = eg.Window("PDF OCR Processor", layout=layout)
    selected_file = ""
    output_folder = ""
    
    while window.is_alive():
        event, values = window.read()
        
        if event == "Select File":
            selected_file = eg.popup_get_file(
                "Select PDF File",
                file_types=[("PDF Files", "*.pdf")]
            )
            
        elif event == "Select Folder":
            output_folder = eg.popup_get_folder("Select Output Folder")
            
        elif event == "Start OCR":
            output_name = values["-name-"]
            
            if not all([selected_file, output_folder, output_name]):
                eg.popup("Please select input file, output folder, and filename.")
                continue
                
            output_path = os.path.join(output_folder, f"{output_name}.pdf")
            
            success, message = processor.process_pdf(selected_file, output_path)
            eg.popup("Success!" if success else f"Error: {message}")
            
            if success:
                break
                
        elif event in (None, "Cancel"):
            break
            
    window.close()

if __name__ == "__main__":
    main()