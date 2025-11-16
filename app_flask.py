from flask import Flask, render_template, request, jsonify, send_file, Response
import cv2
import numpy as np
import os
import base64
import io
from foot_size_detector import process_foot_image
from report_generator import generate_html_report, get_size_conversions
import tempfile
import json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_base64(image):
    """Convert OpenCV image to base64 string"""
    _, buffer = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{img_base64}"

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_image():
    """Process uploaded image"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Save uploaded file temporarily
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the image
            result = process_foot_image(filepath)
            
            if result['success']:
                # Convert annotated image to base64
                annotated_img_base64 = image_to_base64(result['image_with_annotations'])
                
                response_data = {
                    'success': True,
                    'foot_length_cm': result['foot_length_cm'],
                    'uk_shoe_size': str(result['uk_shoe_size']),
                    'pixel_distance': result['pixel_distance'],
                    'scale_factor_mm_per_pixel': result['scale_factor_mm_per_pixel'],
                    'annotated_image': annotated_img_base64
                }
                
                return jsonify(response_data)
            else:
                return jsonify({
                    'success': False,
                    'error': result['error_message']
                }), 400
                
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500

@app.route('/api/default-image', methods=['POST'])
def process_default_image():
    """Process default image"""
    try:
        default_path = r"E:\footsize\img.jpg"
        
        if not os.path.exists(default_path):
            return jsonify({
                'success': False,
                'error': f'Default image not found: {default_path}'
            }), 404
        
        # Process the image
        result = process_foot_image(default_path)
        
        if result['success']:
            # Convert annotated image to base64
            annotated_img_base64 = image_to_base64(result['image_with_annotations'])
            
            response_data = {
                'success': True,
                'foot_length_cm': result['foot_length_cm'],
                'uk_shoe_size': str(result['uk_shoe_size']),
                'pixel_distance': result['pixel_distance'],
                'scale_factor_mm_per_pixel': result['scale_factor_mm_per_pixel'],
                'annotated_image': annotated_img_base64
            }
            
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': result['error_message']
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500

@app.route('/api/download-report', methods=['POST'])
def download_report():
    """Generate and download report"""
    try:
        data = request.json
        
        if not data or 'foot_length_cm' not in data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        
        # Prepare result data for report
        result_data = {
            'foot_length_cm': data['foot_length_cm'],
            'uk_shoe_size': data.get('uk_shoe_size', 'N/A'),
            'pixel_distance': data.get('pixel_distance', 0),
            'scale_factor_mm_per_pixel': data.get('scale_factor_mm_per_pixel', 0),
            'image_with_annotations': None
        }
        
        # Convert base64 image back to OpenCV format if provided
        if 'annotated_image' in data and data['annotated_image']:
            try:
                # Extract base64 data
                img_data = data['annotated_image'].split(',')[1] if ',' in data['annotated_image'] else data['annotated_image']
                img_bytes = base64.b64decode(img_data)
                nparr = np.frombuffer(img_bytes, np.uint8)
                result_data['image_with_annotations'] = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                # If image conversion fails, continue without image
                pass
        
        # Generate HTML report
        html_report = generate_html_report(result_data)
        
        # Return as downloadable HTML file
        return Response(
            html_report,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'attachment; filename=foot_size_report_{data["foot_length_cm"]:.1f}cm.html'
            }
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Report generation error: {str(e)}'
        }), 500

@app.route('/api/size-conversions', methods=['POST'])
def get_size_conversions_api():
    """Get shoe size conversions for a given foot length"""
    try:
        data = request.json
        foot_length_cm = float(data.get('foot_length_cm', 0))
        
        if foot_length_cm <= 0:
            return jsonify({'success': False, 'error': 'Invalid foot length'}), 400
        
        conversions = get_size_conversions(foot_length_cm)
        
        return jsonify({
            'success': True,
            'conversions': conversions
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

