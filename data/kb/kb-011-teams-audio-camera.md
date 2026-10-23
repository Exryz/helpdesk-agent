---
id: KB-011
title: Teams Audio and Camera Problems
category: Email & Collaboration
tags: [teams, audio, camera, microphone, headset]
---

# Teams Audio and Camera Problems

## Symptoms
- Others cannot hear you, or you cannot hear them, in a Microsoft Teams meeting.
- Teams shows "We couldn't find a camera" or your video is black.
- Echo, robotic audio, or your headset is not listed.

## Cause
Usually Teams is using the wrong device, Windows privacy settings are blocking the camera or microphone, another app (such as Zoom or the Windows Camera app) is holding the camera, the laptop's physical camera shutter is closed, or the Teams cache is corrupted.

## Resolution steps
1. **Check physical switches**: Northwind's Dell Latitude laptops have a sliding **privacy shutter** above the screen and an **F9** key that disables the camera. Headsets may have a mute button on the cable.
2. **Select the right devices in Teams**: click **... (Settings and more) > Settings > Devices**. Choose your headset under **Speaker** and **Microphone**, and the correct **Camera**. Click **Make a test call** to verify.
3. **Check Windows privacy**: go to **Settings > Privacy & security > Camera** and **Settings > Privacy & security > Microphone**, and make sure **Let apps access your camera/microphone** and **Microsoft Teams** are turned **On**.
4. Close other apps that may be using the camera or microphone.
5. **Unplug and replug** USB headsets or docks; try a different USB port that is directly on the laptop.
6. **Reset Teams**: quit Teams (right-click its taskbar icon > **Quit**), then go to **Settings > Apps > Installed apps > Microsoft Teams > Advanced options > Reset**. Sign in again.
7. Restart the laptop.
8. During a meeting you can switch devices quickly via **More > Settings > Device settings**.

## Tips
- Only Northwind-approved headsets (Jabra Evolve2 series) are supported; they can be requested at no cost through the portal under **Hardware > Accessories**.
- Echo usually means someone is using laptop speakers with an open microphone; ask them to use a headset.
- Poor audio quality while remote is often bandwidth related; turn off incoming video via **More > Turn off incoming video**.

## When to contact IT
If the camera is not listed in **Device Manager > Cameras** at all, open a ticket at https://help.northwind.example under **Email & Collaboration > Teams**. If a client meeting is starting within minutes, call local **4357**.
