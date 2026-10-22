---
id: KB-029
title: Conference Room AV and Zoom Rooms Troubleshooting
category: Hardware
tags: [zoom-rooms, conference-room, av, neat-pad, display, meeting-room]
---

# Conference Room AV and Zoom Rooms Troubleshooting

## Symptoms
- The main conference room television display is black or displays the warning "No Signal on HDMI 1".
- The tabletop touch controller (Neat Pad or iPad) is frozen, unresponsive, or shows "Connecting to Zoom Room... / Controller Offline".
- Remote video call participants complain of an intense audio echo or high-pitched acoustic screeching.
- In-person attendees cannot wirelessly share their laptop screen to the meeting room display, or the direct HDMI table connection does not project.

## Cause
Northwind conference rooms and boardrooms are standardized on **Neat Bar Pro** and **Logitech Rally Plus** unified communications hardware paired with dedicated Zoom Rooms and Microsoft Teams Room software. Display issues commonly result from television inputs being accidentally switched away from the primary AV source (**HDMI 1**), Power over Ethernet (PoE) drops on the tabletop touch controller, or laptop display resolution mismatches. Acoustic feedback loops occur almost exclusively when meeting attendees inside the room leave their personal laptop microphones and speakers unmuted simultaneously with the room's soundbar.

## Resolution steps
1. **Verify display power and source input**:
   - Ensure the large wall monitor is turned on (check the lower bezel power LED).
   - Using the television physical remote located in the room wall holster, ensure the video input source is set to **HDMI 1 (Room AV)**.
   - Do not adjust television volume using the TV remote; all room audio volume must be controlled from the tabletop touch controller.
2. **Wake and inspect the touch controller**:
   - Tap the tabletop controller screen once to wake it from standby mode.
   - If the controller indicates "Controller Offline", check the network cable on the back or bottom of the stand to ensure the RJ-45 PoE clip is firmly clicked into place.
3. **Power cycle the room AV compute unit**:
   - If the room camera, microphone bar, or controller remains completely unresponsive:
   - Locate the Neat Bar or Logitech compute bar mounted directly below or above the display.
   - Press and hold the recessed power button for **10 seconds** until the status LED flashes amber, then release to restart the appliance.
   - Allow **3 minutes** for the hardware to boot, re-negotiate network DHCP, and re-establish cloud connection with Zoom Room servers.
4. **Eliminate acoustic echo and feedback**:
   - Every attendee physically present in the conference room must **Mute** their personal laptop microphone and turn their laptop speaker volume to zero.
   - Only the designated conference room ceiling/tabletop microphone array and room speakers should handle in-room audio.
5. **Wireless screen sharing**:
   - On the tabletop touch screen, tap **Share Screen**.
   - Note the **6-digit sharing key** displayed in the upper-right corner of the main television.
   - Open the Zoom client on your laptop, click **Share Screen**, and enter the 6-digit room code to project wirelessly.
6. **Wired HDMI / USB-C connection**:
   - If wireless sharing fails, plug the tethered table **USB-C / HDMI cable** directly into your laptop port.
   - On your laptop, press **Win + P** and ensure the projection mode is set to **Duplicate** or **Extend**.

## When to contact IT
If an executive meeting or client-facing conference is starting within 15 minutes and the room system is malfunctioning, immediately call the **VIP IT Hotline at local 4357** for immediate on-site technician dispatch.

For general room maintenance, frayed table cables, or missing adapter pucks, open a ticket at https://help.northwind.example under **Hardware > Conference Room AV**.
