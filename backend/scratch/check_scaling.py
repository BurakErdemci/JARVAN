import mss
import pyautogui
import os

def check_scaling():
    print(f"OS: {os.uname().sysname}")
    
    # PyAutoGUI (Mantıksal - Logical)
    p_width, p_height = pyautogui.size()
    print(f"PyAutoGUI Size (Logical): {p_width}x{p_height}")
    
    # MSS (Fiziksel - Physical)
    with mss.mss() as sct:
        for i, mon in enumerate(sct.monitors):
            print(f"MSS Monitor {i} (Physical): {mon}")
            
    # Oran (Scaling Factor)
    with mss.mss() as sct:
        m1 = sct.monitors[1]
        scale_x = m1['width'] / p_width
        scale_y = m1['height'] / p_height
        print(f"Detected Scale Factor: X={scale_x}, Y={scale_y}")

if __name__ == "__main__":
    check_scaling()
