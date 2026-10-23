---
id: KB-018
title: External Monitors and Docking Stations
category: Hardware
tags: [monitor, dock, display, usb-c]
---

# External Monitors and Docking Stations

## Standard equipment
Each Northwind desk has a **Dell WD19S USB-C docking station** and up to **two 24-inch Dell P2425H monitors**. The dock charges the laptop (up to 130 W), and provides Ethernet, USB and display connections through a single USB-C cable. A maximum of **two external monitors** is supported per laptop. Remote employees may request one monitor and one dock for home use through the portal under **Hardware > Accessories**, with manager approval.

## Symptoms
- External monitors stay black or show "No signal".
- Only one of two monitors works.
- Displays flicker, have the wrong resolution, or windows move to the wrong screen.
- The laptop does not charge on the dock.

## Resolution steps
1. Connect the dock's USB-C cable to the laptop port marked with the **Thunderbolt/DisplayPort** symbol (on the left side of the Latitude 5440).
2. Check that the monitors are powered on and set to the correct input (**DisplayPort** or **HDMI**) using the buttons on the monitor.
3. Press **Win + P** and choose **Extend**.
4. Go to **Settings > System > Display**, click **Detect** under **Multiple displays**, and drag the monitor icons to match their physical layout. Set resolution to **1920 x 1080** (recommended).
5. Reset the dock: unplug the dock's power cable and USB-C cable, wait **30 seconds**, plug power back in, then reconnect the laptop.
6. Update dock firmware and drivers: open **Dell Command | Update** and click **Check**, then **Apply**, with the laptop connected to the dock.
7. Try a different cable between dock and monitor to rule out a faulty cable.
8. If the laptop is not charging, make sure the dock is using its own **130 W** power adapter, not a laptop charger.

## Tips
- Connect the dock **after** Windows has started if you encounter BitLocker recovery prompts at startup (see KB-016).
- Hot desks on the 4th floor use the same dock model; just plug in and use Win + P.

## When to contact IT
If monitors still are not detected after resetting the dock and updating firmware, open a ticket at https://help.northwind.example under **Hardware > Monitor / Dock** and include the **desk number** and dock service tag.
