![Status: Work in Progress, Some fetures may not work.](https://img.shields.io/badge/status-work--in--progress-orange)

# Workbench

Workbench is a modular, open-source suite for designing and simulating electronics. It consists of two desktop tools for circuit simulation using modular .adev device files.

## Install

pip install PyQt5

## Tools

### 1. Workbench IDE — Circuit Designer
python IDE.py
- Import .adev device files -> devices appear in sidebar
- Click devices to place them on the canvas
- Click pins to draw orthogonal wires (routes dodge each other)
- Import .ino sketch files into the code editor
- Run simulation — LEDs light up, servos move, serial output appears

**Controls:**
- 1 Select tool, 2 Wire tool, 3 Delete tool
- Middle-click or drag background to pan
- Scroll to zoom
- Del to remove selected component
- Esc to cancel wire

### 2. Device Creator — Build .adev Files
python DeviceCreator.py

**5 tabs to build a device:**

1. Info — Device ID, name, category, description, canvas size, color
2. Visual — Upload a 2D image, then use tools:
   - Pin tool — Click to place pins, set type/direction/side in properties
   - LED tool — Place LED indicators that glow when a state variable matches
   - Display tool — Click-drag to define a screen region for OLEDs/LCDs
   - Select any pin/LED to edit its properties in the right panel
3. Emulation — JSON editor for rules (triggers, actions, state variables)
   - Reference sidebar shows all trigger/action types and your defined pins
4. Preview — See your device at 3x zoom, test emulation live (LEDs blink)
5. Export — Summary, JSON preview, download as .adev

You can also Import .adev to edit existing device files.

## .adev File Format

{
  "format_version": "1.0",
  "device": { "id": "...", "name": "...", "category": "..." },
  "visual": { "width": 100, "height": 100, "label": "...", "color": "#..." },
  "pins": [{ "id": "...", "label": "...", "x": 0, "y": 0, "type": "digital", "side": "left" }],
  "emulation": { "type": "active", "state_vars": {}, "rules": [], "properties": {} },
  "display": { "type": "oled_ssd1306", "region": { "x": 10, "y": 10, "w": 80, "h": 40 } }
}

**License**: GPLv3
