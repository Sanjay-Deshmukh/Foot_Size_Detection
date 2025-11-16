"""
Report Generator for Foot Size Detection System
Generates downloadable reports with results and shoe size charts
"""
import cv2
import numpy as np
from datetime import datetime
import base64
import io


# Shoe Size Conversion Chart: Centimetres | India | Euro
SHOE_SIZE_CHART = [
    {"CM": 20, "India": 5.5, "EU": "39"},
    {"CM": 22.1, "India": 6, "EU": "39"},
    {"CM": 24.4, "India": 6.5, "EU": "40"},
    {"CM": 24.8, "India": 7, "EU": "40-41"},
    {"CM": 25.4, "India": 7.5, "EU": "41"},
    {"CM": 25.7, "India": 8, "EU": "41-42"},
    {"CM": 26.0, "India": 8.5, "EU": "42"},
    {"CM": 26.7, "India": 9, "EU": "42-43"},
    {"CM": 27.0, "India": 9.5, "EU": "43"},
    {"CM": 27.3, "India": 10, "EU": "43-44"},
    {"CM": 27.9, "India": 10.5, "EU": "44"},
    {"CM": 28.3, "India": 11, "EU": "44-45"},
    {"CM": 29.3, "India": 12, "EU": "46-47"},
    {"CM": 30.0, "India": 13, "EU": "47-48"},
]


def get_size_conversions(foot_length_cm, india_size=None):
    """Get shoe size conversions for a given foot length in cm and India size"""
    # If India size is provided, use it to find the exact match in chart
    if india_size is not None:
        # Try to find exact India size match
        for size in SHOE_SIZE_CHART:
            if size["India"] == india_size:
                return {
                    "recommended": size,
                    "alternatives": [],
                    "foot_length_cm": foot_length_cm
                }
        # If exact match not found, try to find closest India size
        try:
            india_size_float = float(india_size)
            closest_india = min(SHOE_SIZE_CHART, key=lambda x: abs(x["India"] - india_size_float))
            return {
                "recommended": closest_india,
                "alternatives": [],
                "foot_length_cm": foot_length_cm
            }
        except (ValueError, TypeError):
            # If India size is not a number (e.g., "Too small"), fall back to CM-based lookup
            pass
    
    # Fallback: Find closest match in chart based on CM
    closest = min(SHOE_SIZE_CHART, key=lambda x: abs(x["CM"] - foot_length_cm))
    
    # Get sizes within ±0.5 cm range
    recommended_sizes = [
        size for size in SHOE_SIZE_CHART
        if abs(size["CM"] - foot_length_cm) <= 0.5
    ]
    
    if not recommended_sizes:
        recommended_sizes = [closest]
    
    return {
        "recommended": recommended_sizes[0] if recommended_sizes else closest,
        "alternatives": recommended_sizes[1:3] if len(recommended_sizes) > 1 else [],
        "foot_length_cm": foot_length_cm
    }


def image_to_base64(image):
    """Convert OpenCV image to base64 string"""
    _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{img_base64}"


def generate_html_report(result_data):
    """Generate HTML report with results and shoe size chart"""
    foot_length = result_data['foot_length_cm']
    india_size = result_data['uk_shoe_size']  # Note: uk_shoe_size now contains India size
    # Use the India size from the result to find the correct conversion
    conversions = get_size_conversions(foot_length, india_size)
    
    # Convert annotated image to base64
    annotated_img_base64 = image_to_base64(result_data['image_with_annotations'])
    
    # Get current date
    current_date = datetime.now().strftime("%B %d, %Y")
    current_time = datetime.now().strftime("%I:%M %p")
    
    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Foot Size Detection Report</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px 20px;
                min-height: 100vh;
            }}
            
            .report-container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                overflow: hidden;
            }}
            
            .report-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            
            .report-header h1 {{
                font-size: 2.5rem;
                margin-bottom: 10px;
                font-weight: 700;
            }}
            
            .report-header p {{
                font-size: 1.1rem;
                opacity: 0.9;
            }}
            
            .report-body {{
                padding: 40px;
            }}
            
            .section {{
                margin-bottom: 40px;
            }}
            
            .section-title {{
                font-size: 1.8rem;
                color: #333;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #667eea;
                font-weight: 600;
            }}
            
            .result-image {{
                width: 100%;
                max-width: 800px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                margin: 20px 0;
            }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            
            .metric-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            }}
            
            .metric-card.orange {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }}
            
            .metric-label {{
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                opacity: 0.9;
                margin-bottom: 10px;
            }}
            
            .metric-value {{
                font-size: 2.5rem;
                font-weight: 700;
                margin: 10px 0;
            }}
            
            .size-chart {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                border-radius: 10px;
                overflow: hidden;
            }}
            
            .size-chart thead {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            
            .size-chart th {{
                padding: 15px;
                text-align: center;
                font-weight: 600;
                font-size: 1rem;
            }}
            
            .size-chart td {{
                padding: 12px;
                text-align: center;
                border-bottom: 1px solid #eee;
            }}
            
            .size-chart tbody tr:hover {{
                background: #f5f5f5;
            }}
            
            .size-chart tbody tr.recommended {{
                background: #e3f2fd;
                font-weight: 600;
                border-left: 4px solid #2196F3;
            }}
            
            .recommended-badge {{
                background: #4CAF50;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 0.8rem;
                font-weight: 600;
            }}
            
            .info-box {{
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            
            .info-box p {{
                margin: 5px 0;
                color: #666;
                line-height: 1.6;
            }}
            
            .report-footer {{
                background: #f8f9fa;
                padding: 30px;
                text-align: center;
                color: #666;
                border-top: 1px solid #eee;
            }}
            
            .technical-details {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            
            .technical-details p {{
                margin: 8px 0;
                color: #666;
                font-family: 'Courier New', monospace;
            }}
            
            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}
                
                .report-container {{
                    box-shadow: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="report-header">
                <h1>🦶 Foot Size Detection Report</h1>
                <p>Professional Computer Vision Analysis</p>
                <p style="margin-top: 10px; font-size: 0.9rem;">Generated on {current_date} at {current_time}</p>
            </div>
            
            <div class="report-body">
                <!-- Measurement Results -->
                <div class="section">
                    <h2 class="section-title">Measurement Results</h2>
                    
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">Foot Length</div>
                            <div class="metric-value">{foot_length:.2f}</div>
                            <div class="metric-label">Centimeters</div>
                        </div>
                        <div class="metric-card orange">
                            <div class="metric-label">India Shoe Size</div>
                            <div class="metric-value">{india_size}</div>
                            <div class="metric-label">Recommended</div>
                        </div>
                    </div>
                    
                    <img src="{annotated_img_base64}" alt="Foot Measurement" class="result-image">
                </div>
                
                <!-- Shoe Size Conversion Chart -->
                <div class="section">
                    <h2 class="section-title">Shoe Size Conversion Chart</h2>
                    
                    <div class="info-box">
                        <p><strong>Your Measurement:</strong> {foot_length:.2f} cm</p>
                        <p><strong>Recommended India Size:</strong> {india_size}</p>
                        <p><strong>Recommended EU Size:</strong> {conversions['recommended']['EU']}</p>
                    </div>
                    
                    <table class="size-chart">
                        <thead>
                            <tr>
                                <th>Centimetres</th>
                                <th>India</th>
                                <th>Euro</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    # Add chart rows
    for size in SHOE_SIZE_CHART:
        # Check if this row matches the calculated India size
        try:
            india_size_float = float(india_size)
            is_recommended = size["India"] == india_size_float
        except (ValueError, TypeError):
            # If India size is not a number, use the conversions recommended
            is_recommended = size == conversions['recommended']
        
        row_class = "recommended" if is_recommended else ""
        badge = '<span class="recommended-badge">Recommended</span>' if is_recommended else ""
        
        html += f"""
                            <tr class="{row_class}">
                                <td>{size['CM']:.1f}</td>
                                <td>{size['India']}</td>
                                <td>{size['EU']}</td>
                                <td>{badge}</td>
                            </tr>
        """
    
    html += """
                        </tbody>
                    </table>
                </div>
                
                <!-- Additional Information -->
                <div class="section">
                    <h2 class="section-title">Important Notes</h2>
                    <div class="info-box">
                        <p>• This measurement is based on foot length only. Actual shoe fit may vary based on foot width, arch height, and personal preference.</p>
                        <p>• It's recommended to try on shoes before purchasing, as different brands may have slight size variations.</p>
                        <p>• For best results, measure your foot in the afternoon when feet are at their largest.</p>
                        <p>• The measurement was calculated using a Indian 1 Rupee coin (22mm diameter) as a scale reference.</p>
                    </div>
                </div>
            </div>
            
            <div class="report-footer">
                <p><strong>Foot Size Detection System</strong></p>
                <p>Professional Computer Vision-Based Measurement</p>
                <p style="margin-top: 10px; font-size: 0.9rem;"></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def generate_pdf_report(result_data):
    """Generate PDF report - placeholder for future PDF generation"""
    # For now, return HTML that can be printed to PDF
    # In the future, you can use libraries like reportlab or weasyprint
    return generate_html_report(result_data)

