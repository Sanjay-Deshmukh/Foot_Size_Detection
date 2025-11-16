import cv2
import numpy as np
import sys
import os

# ============================================================
# CONFIGURATION
# ============================================================
REAL_COIN_DIAMETER_MM = 22.0  # UK 1p coin diameter
MAX_DISPLAY_SIZE = 900
MIN_COIN_SIZE = 20  # Minimum coin size in pixels
MIN_CONTOUR_POINTS = 20  # Minimum points for ellipse fitting

# ============================================================
# SHOE SIZE FUNCTION
# ============================================================
def predict_uk_size_v2(length_cm):
    """
    Predict shoe size based on standard shoe size chart.
    Finds the nearest CM in SHOE_SIZE_CHART.
    Returns India size as primary size.
    """
    # Size chart: Centimetres | India | Euro
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

    # If foot is too small
    if length_cm < SHOE_SIZE_CHART[0]["CM"]:
        return "Too small"

    # If foot is too large
    if length_cm > SHOE_SIZE_CHART[-1]["CM"]:
        return "Too large"

    # Find closest CM entry
    closest_entry = min(
        SHOE_SIZE_CHART,
        key=lambda x: abs(x["CM"] - length_cm)
    )

    return closest_entry["India"]


# ============================================================
# COIN DETECTION
# ============================================================
def detect_coin(img):
    """
    Detect coin in image using ellipse fitting.
    Returns: (center, radius, diameter_pixels, MA, ma) or None
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 1)
    edges = cv2.Canny(blur, 60, 150)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        if len(cnt) >= MIN_CONTOUR_POINTS:
            try:
                ellipse = cv2.fitEllipse(cnt)
                (cx, cy), (MA, ma), angle = ellipse
                
                if MA > MIN_COIN_SIZE and ma > MIN_COIN_SIZE:
                    # Tilt-corrected coin diameter (geometric mean)
                    coin_diameter_pixels = np.sqrt(MA * ma)
                    radius = coin_diameter_pixels / 2.0
                    center = (int(cx), int(cy))
                    
                    return {
                        'center': center,
                        'radius': int(radius),
                        'diameter_pixels': coin_diameter_pixels,
                        'MA': MA,
                        'ma': ma,
                        'angle': angle
                    }
            except:
                continue
    
    return None


# ============================================================
# SCALING CALCULATION
# ============================================================
def calculate_scale_factor(coin_diameter_pixels, real_coin_diameter_mm=REAL_COIN_DIAMETER_MM):
    """Calculate scale factor: mm per pixel."""
    return real_coin_diameter_mm / coin_diameter_pixels


# ============================================================
# DISTANCE CALCULATION
# ============================================================
def calculate_distance(point1, point2, scale_mm_per_pixel):
    """
    Calculate real-world distance between two points.
    Returns: (pixel_distance, distance_mm, distance_cm)
    """
    x1, y1 = point1
    x2, y2 = point2
    
    # FIXED: Use **2 (squared) instead of *2
    pixel_dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    real_mm = pixel_dist * scale_mm_per_pixel
    real_cm = real_mm / 10.0
    
    return pixel_dist, real_mm, real_cm


# ============================================================
# MANUAL MODE: CLICK HANDLER
# ============================================================
class ClickHandler:
    def __init__(self, img_display, scale_display):
        self.img_display = img_display.copy()
        self.scale_display = scale_display
        self.clicked_points_display = []
        self.clicked_points_original = []
        
    def click_event(self, event, x, y, flags, param):
        """Handle mouse click events."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicked_points_display.append((x, y))
            
            orig_x = int(x / self.scale_display)
            orig_y = int(y / self.scale_display)
            self.clicked_points_original.append((orig_x, orig_y))
            
            print(f"\n📍 Display Point {len(self.clicked_points_display)}: ({x}, {y})")
            print(f"📍 Original Point {len(self.clicked_points_original)}: ({orig_x}, {orig_y})")
            
            # Draw point
            cv2.circle(self.img_display, (x, y), 6, (0, 0, 255), -1)
            
            # Draw line if two points
            if len(self.clicked_points_display) == 2:
                cv2.line(self.img_display,
                        self.clicked_points_display[0],
                        self.clicked_points_display[1],
                        (255, 0, 0), 2)
            
            cv2.imshow("Select TWO Points (Press any key when done)", self.img_display)
    
    def get_points(self):
        """Get clicked points in original image coordinates."""
        if len(self.clicked_points_original) == 2:
            return self.clicked_points_original[0], self.clicked_points_original[1]
        return None, None


# ============================================================
# VISUALIZATION
# ============================================================
def draw_measurements(img, point1, point2, foot_length_cm, uk_shoe_size, 
                     coin_center=None, coin_radius=None):
    """
    Draw measurements and annotations on image.
    Returns annotated image.
    """
    img_annotated = img.copy()
    
    # Draw coin if provided
    if coin_center and coin_radius:
        cv2.circle(img_annotated, coin_center, coin_radius, (0, 255, 0), 3)
        cv2.putText(img_annotated, "Coin", 
                   (coin_center[0] + coin_radius + 5, coin_center[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Draw measurement line
    if point1 and point2:
        cv2.line(img_annotated, point1, point2, (255, 0, 0), 3)
        cv2.circle(img_annotated, point1, 8, (0, 0, 255), -1)
        cv2.circle(img_annotated, point2, 8, (0, 0, 255), -1)
        
        # Label heel and toe
        cv2.putText(img_annotated, "Heel", 
                   (point1[0] + 10, point1[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(img_annotated, "Toe", 
                   (point2[0] + 10, point2[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Calculate midpoint for text
        mid_x = (point1[0] + point2[0]) // 2
        mid_y = (point1[1] + point2[1]) // 2
        
        # Draw measurement text
        text = f"{foot_length_cm:.2f} cm (India {uk_shoe_size})"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # Get text size for background
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Draw background rectangle
        cv2.rectangle(img_annotated,
                     (mid_x - text_width // 2 - 5, mid_y - text_height - baseline - 5),
                     (mid_x + text_width // 2 + 5, mid_y + baseline + 5),
                     (255, 255, 255), -1)
        
        # Draw text
        cv2.putText(img_annotated, text,
                   (mid_x - text_width // 2, mid_y),
                   font, font_scale, (0, 0, 0), thickness)
    
    return img_annotated


# ============================================================
# MAIN PROCESSING FUNCTION
# ============================================================
def process_foot_image(image_path):
    """
    Main function to process foot image and return measurements.
    Uses manual mode - user must click two points (heel and toe).
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary with:
        - foot_length_cm: Foot length in centimeters
        - uk_shoe_size: India shoe size
        - image_with_annotations: Annotated output image
        - success: Boolean indicating if processing was successful
        - error_message: Error message if processing failed
    """
    # Load image
    if not os.path.exists(image_path):
        return {
            'success': False,
            'error_message': f"Image not found: {image_path}",
            'foot_length_cm': None,
            'uk_shoe_size': None,
            'image_with_annotations': None
        }
    
    img = cv2.imread(image_path)
    if img is None:
        return {
            'success': False,
            'error_message': f"Could not load image: {image_path}",
            'foot_length_cm': None,
            'uk_shoe_size': None,
            'image_with_annotations': None
        }
    
    orig_h, orig_w = img.shape[:2]
    img_copy = img.copy()
    
    # Resize for display
    scale_display = min(MAX_DISPLAY_SIZE / orig_w, MAX_DISPLAY_SIZE / orig_h)
    display_w = int(orig_w * scale_display)
    display_h = int(orig_h * scale_display)
    img_display = cv2.resize(img_copy, (display_w, display_h))
    
    # ============================================================
    # DETECT COIN
    # ============================================================
    print("\n" + "="*50)
    print("🔍 DETECTING COIN...")
    print("="*50)
    
    coin_data = detect_coin(img)
    if coin_data is None:
        return {
            'success': False,
            'error_message': "No coin detected in image. Please ensure a coin is visible.",
            'foot_length_cm': None,
            'uk_shoe_size': None,
            'image_with_annotations': None
        }
    
    coin_center = coin_data['center']
    coin_radius = coin_data['radius']
    coin_diameter_pixels = coin_data['diameter_pixels']
    MA = coin_data['MA']
    ma = coin_data['ma']
    
    # Log coin detection stats
    print(f"✅ Coin detected!")
    print(f"   Major Axis (MA): {MA:.2f} px")
    print(f"   Minor Axis (ma): {ma:.2f} px")
    print(f"   Tilt-Corrected Diameter: {coin_diameter_pixels:.2f} px")
    print(f"   Center: {coin_center}")
    print(f"   Radius: {coin_radius} px")
    
    # Calculate scale factor
    scale_mm_per_pixel = calculate_scale_factor(coin_diameter_pixels)
    print(f"\n📏 Scale Factor: {scale_mm_per_pixel:.4f} mm per pixel")
    
    # ============================================================
    # GET MANUAL POINTS (USER CLICKS)
    # ============================================================
    print("\n" + "="*50)
    print("👆 Please click TWO points on the image...")
    print("="*50)
    print("   Click on HEEL first, then TOE")
    print("   Press any key when done")
    
    # Draw coin on display
    disp_center = (int(coin_center[0] * scale_display), int(coin_center[1] * scale_display))
    disp_radius = int(coin_radius * scale_display)
    cv2.circle(img_display, disp_center, disp_radius, (0, 255, 0), 3)
    
    # Set up click handler
    click_handler = ClickHandler(img_display, scale_display)
    cv2.imshow("Select TWO Points (Press any key when done)", img_display)
    cv2.setMouseCallback("Select TWO Points (Press any key when done)", click_handler.click_event)
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    point1, point2 = click_handler.get_points()
    
    if point1 is None or point2 is None:
        return {
            'success': False,
            'error_message': "You must click exactly TWO points.",
            'foot_length_cm': None,
            'uk_shoe_size': None,
            'image_with_annotations': None
        }
    
    print(f"📍 Selected points:")
    print(f"   Point 1 (Heel): {point1}")
    print(f"   Point 2 (Toe): {point2}")
    
    # ============================================================
    # CALCULATE MEASUREMENTS
    # ============================================================
    print("\n" + "="*50)
    print("📐 CALCULATING MEASUREMENTS...")
    print("="*50)
    
    pixel_dist, real_mm, real_cm = calculate_distance(point1, point2, scale_mm_per_pixel)
    
    print(f"   Pixel Distance: {pixel_dist:.2f} px")
    print(f"   Real Distance: {real_mm:.2f} mm ({real_cm:.2f} cm)")
    
    # Get shoe size
    uk_shoe = predict_uk_size_v2(real_cm)
    
    print(f"\n👟 India Shoe Size: {uk_shoe}")
    print("="*50)
    
    # ============================================================
    # CREATE ANNOTATED IMAGE
    # ============================================================
    img_annotated = draw_measurements(
        img, point1, point2, real_cm, uk_shoe,
        coin_center, coin_radius
    )
    
    result = {
        'success': True,
        'error_message': None,
        'foot_length_cm': real_cm,
        'uk_shoe_size': uk_shoe,
        'image_with_annotations': img_annotated,
        'pixel_distance': pixel_dist,
        'scale_factor_mm_per_pixel': scale_mm_per_pixel
    }
    
    return result


# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    # Default image path (update this)
    default_image_path = r"E:\footsize\img.jpg"
    
    # Check if image path provided as command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = default_image_path
    
    # Process the image
    result = process_foot_image(image_path)
    
    if result['success']:
        # Display result
        print("\n" + "="*50)
        print("✅ PROCESSING COMPLETE!")
        print("="*50)
        print(f"Foot Length: {result['foot_length_cm']:.2f} cm")
        print(f"India Shoe Size: {result['uk_shoe_size']}")
        print("="*50)
        
        # Show annotated image
        if result['image_with_annotations'] is not None:
            # Resize for display
            h, w = result['image_with_annotations'].shape[:2]
            scale = min(MAX_DISPLAY_SIZE / w, MAX_DISPLAY_SIZE / h)
            display_img = cv2.resize(result['image_with_annotations'], 
                                    (int(w * scale), int(h * scale)))
            
            cv2.imshow("Foot Size Detection Result", display_img)
            print("\nPress any key to close the result window...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print(f"\n❌ ERROR: {result['error_message']}")
        sys.exit(1)
